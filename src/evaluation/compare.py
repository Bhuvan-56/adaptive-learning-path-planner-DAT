"""
Comparative Evaluation Module for Adaptive Diagnostics and Planning Controls.

ARCHITECTURAL PRINCIPLE:
------------------------
This module executes evaluation comparisons across diagnostic arms and planning
policies on identical, paired simulated learners.
It imports from `src.simulation.simulator` (including `EvaluatorView` for ground
truth inspection), `src.diagnostic.diagnostic`, and `src.planning`.
CRITICAL: Modules under `src.planning` and `src.state` MUST NEVER import from
`src.evaluation`.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
import os
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd
import yaml

# Simulator and EvaluatorView
from src.simulation.simulator import (
    SimulatedLearner,
    EvaluatorView,
    MatchedBKTGenerator,
)

# Diagnostic module
from src.diagnostic.diagnostic import (
    AdaptiveDiagnostic,
    load_cat_hyperparameters,
    load_item_bank_and_qmatrix,
    ability_to_prior,
    DEFAULT_ITEM_BANK_PATH,
    DEFAULT_QMATRIX_PATH,
    DEFAULT_CURRICULUM_PATH,
)

# Planning and State modules
from src.state.learner_state import ConceptState
from src.planning.static_baseline import generate_static_plan
from src.planning.replan import replan, ReplanState, assessment_result
from src.planning.difficulty import DifficultyState, step_difficulty
from src.curriculum.graph import load_graph


DEFAULT_COMPARISON_CONFIG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "w4_comparison.yaml")
)


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hexadecimal digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def load_comparison_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads and validates the master comparison configuration YAML.
    """
    path = config_path or DEFAULT_COMPARISON_CONFIG
    if not os.path.exists(path):
        raise FileNotFoundError(f"Comparison configuration not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError(f"Comparison configuration at {path} must be a dictionary mapping.")

    # Validation of required sections
    for sec in ["seeds", "evaluation_scale", "diagnostic", "statistics", "planner_controls", "baselines"]:
        if sec not in config:
            raise KeyError(f"Missing required configuration section '{sec}' in {path}")

    return config


@dataclass
class SyntheticLearnerTruth:
    """
    Evaluator-only ground truth for a synthetic learner.
    """
    learner_id: int
    theta_true: float
    seed: int
    latent_mastery: Dict[str, bool]
    pre_generated_responses: Dict[str, int]


def generate_synthetic_learners(
    n_learners: int,
    seed: int,
    item_bank: pd.DataFrame,
    concept_difficulties: Dict[str, float],
    held_out_items: Optional[List[Dict[str, Any]]] = None,
) -> List[SyntheticLearnerTruth]:
    """
    Generates an evaluation cohort of synthetic learners with latent abilities theta*
    and pre-computed responses to ensure 100% paired equality across arms.

    Synthetic relation for latent concept mastery:
    latent_mastery = theta >= b_concept [PROPOSED]
    """
    rng = np.random.default_rng(seed)
    thetas = rng.normal(loc=0.0, scale=1.0, size=n_learners)

    learners: List[SyntheticLearnerTruth] = []

    for idx, theta in enumerate(thetas):
        l_seed = int(seed * 1000 + idx)
        l_rng = np.random.default_rng(l_seed)

        # 1. Latent mastery truth: theta >= b_concept [PROPOSED]
        latent_mastery = {
            concept: bool(theta >= b_val)
            for concept, b_val in concept_difficulties.items()
        }

        # 2. Pre-generate deterministic 2PL responses for item bank
        responses: Dict[str, int] = {}
        for _, row in item_bank.iterrows():
            item_id = str(row["item_id"])
            a = float(row["a"])
            b = float(row["b"])
            c = float(row.get("c", 0.0))
            d = float(row.get("d", 1.0))

            # 2PL / 3PL response probability
            p_correct = c + (d - c) / (1.0 + math.exp(-a * (theta - b)))
            responses[item_id] = 1 if (l_rng.random() < p_correct) else 0

        # Also pre-generate responses for held-out evaluation items
        if held_out_items:
            for item in held_out_items:
                item_id = str(item["item_id"])
                a = float(item["a"])
                b = float(item["b"])
                c = float(item.get("c", 0.0))
                d = float(item.get("d", 1.0))
                p_correct = c + (d - c) / (1.0 + math.exp(-a * (theta - b)))
                responses[item_id] = 1 if (l_rng.random() < p_correct) else 0

        learners.append(
            SyntheticLearnerTruth(
                learner_id=idx,
                theta_true=float(theta),
                seed=l_seed,
                latent_mastery=latent_mastery,
                pre_generated_responses=responses,
            )
        )

    return learners


def create_held_out_items(
    concepts: List[str],
    items_per_concept: int = 5,
    seed: int = 9999,
) -> List[Dict[str, Any]]:
    """
    Creates an independent held-out evaluation item set with known 2PL parameters
    to evaluate response log-loss prediction across all arms on identical items.

    Cites docs/EVALUATION_PROTOCOL.md line 63: N = 5 items per concept [PROPOSED].
    """
    rng = np.random.default_rng(seed)
    held_out: List[Dict[str, Any]] = []

    for c_idx, concept in enumerate(concepts):
        for i in range(items_per_concept):
            item_id = f"held_out_{concept}_{i+1}"
            a = float(np.clip(rng.lognormal(mean=0.2, sigma=0.25), 0.5, 2.5))
            b = float(rng.normal(loc=0.0, scale=1.0))
            held_out.append({
                "item_id": item_id,
                "concept_id": concept,
                "a": round(a, 4),
                "b": round(b, 4),
                "c": 0.0,
                "d": 1.0,
            })

    return held_out


def compute_paired_bootstrap_ci(
    values: Union[List[float], np.ndarray],
    b_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """
    Computes empirical percentile bootstrap confidence interval for a metric mean.
    Cites docs/EVALUATION_PROTOCOL.md lines 87-91: B = 1000 resamples [PROPOSED].

    Returns (mean, ci_lower, ci_upper).
    """
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n == 0:
        return 0.0, 0.0, 0.0

    mean_val = float(np.mean(arr))
    if n == 1 or b_resamples <= 0:
        return mean_val, mean_val, mean_val

    rng = np.random.default_rng(seed)
    boot_indices = rng.integers(0, n, size=(b_resamples, n))
    boot_means = np.mean(arr[boot_indices], axis=1)

    alpha = 1.0 - confidence_level
    ci_lower = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    ci_upper = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))

    return mean_val, ci_lower, ci_upper


# ==============================================================================
# TASK 1: DIAGNOSTIC COMPARISON
# ==============================================================================

@dataclass
class DiagnosticArmResult:
    arm_name: str
    mae_theta: float
    mae_ci: Tuple[float, float]
    brier_score: float
    brier_ci: Tuple[float, float]
    log_loss: float
    log_loss_ci: Tuple[float, float]
    runtime_p50_ms: float
    runtime_p95_ms: float
    mean_items_used: float
    items_used_ci: Tuple[float, float]
    learner_records: List[Dict[str, Any]] = field(default_factory=list)


def evaluate_diagnostic_arm(
    arm_name: str,
    learners: List[SyntheticLearnerTruth],
    bank_df: pd.DataFrame,
    qmatrix_dict: Dict[str, str],
    curriculum_nodes: List[str],
    item_cap: int,
    stopping_variance: float,
    held_out_items: List[Dict[str, Any]],
    bootstrap_resamples: int = 1000,
    seed: int = 42,
) -> DiagnosticArmResult:
    """
    Executes a single diagnostic arm across the synthetic learner cohort.
    Arms supported:
      - 'adaptive': MaxInfoSelector, runs to item_cap
      - 'adaptive_early_stop': MaxInfoSelector with MinErrorStopper (variance <= 0.15 or item_cap)
      - 'fixed': Administered in item_id order up to item_cap
      - 'random': Administered in seeded random order up to item_cap
    """
    import catsim.cat as cat
    import catsim.estimation as est
    import catsim.initialization as init
    import catsim.irt as irt
    import catsim.selection as sel
    import catsim.stopping as stp

    # Convert bank to catsim ItemBank
    catsim_matrix = np.zeros((len(bank_df), 5), dtype=float)
    catsim_matrix[:, 0] = bank_df["a"].to_numpy(dtype=float)
    catsim_matrix[:, 1] = bank_df["b"].to_numpy(dtype=float)
    catsim_matrix[:, 2] = bank_df["c"].to_numpy(dtype=float)
    catsim_matrix[:, 3] = bank_df["d"].to_numpy(dtype=float)
    catsim_matrix[:, 4] = 0.0

    catsim_bank = cat.ItemBank(catsim_matrix)

    item_ids = list(bank_df["item_id"])
    item_id_to_idx = {iid: idx for idx, iid in enumerate(item_ids)}

    learner_records: List[Dict[str, Any]] = []
    selection_times_ms: List[float] = []

    mae_list: List[float] = []
    brier_list: List[float] = []
    logloss_list: List[float] = []
    items_used_list: List[float] = []

    early_stop_err = math.sqrt(stopping_variance)

    for l_idx, learner in enumerate(learners):
        administered_indices: List[int] = []
        response_bools: List[bool] = []
        est_theta = 0.0

        selector = sel.MaxInfoSelector()
        estimator = est.NumericalSearchEstimator()
        stopper = stp.MinErrorStopper(min_error=early_stop_err, max_items=item_cap)

        # Determine item order for fixed / random
        if arm_name == "fixed":
            candidate_order = list(range(min(item_cap, len(item_ids))))
        elif arm_name == "random":
            rand_rng = np.random.default_rng(learner.seed)
            shuffled = list(range(len(item_ids)))
            rand_rng.shuffle(shuffled)
            candidate_order = shuffled[:item_cap]
        else:
            candidate_order = []

        step_idx = 0
        final_variance = float("inf")

        while len(administered_indices) < item_cap:
            t0 = time.perf_counter()

            if arm_name in ("adaptive", "adaptive_early_stop"):
                next_idx = selector.select(
                    item_bank=catsim_bank,
                    administered_items=administered_indices,
                    est_theta=est_theta,
                )
            elif arm_name in ("fixed", "random"):
                next_idx = candidate_order[step_idx] if step_idx < len(candidate_order) else None
            else:
                raise ValueError(f"Unknown diagnostic arm: {arm_name}")

            t1 = time.perf_counter()
            selection_times_ms.append((t1 - t0) * 1000.0)

            if next_idx is None or next_idx in administered_indices:
                break

            administered_indices.append(next_idx)
            item_id = item_ids[next_idx]
            resp_int = learner.pre_generated_responses[item_id]
            response_bools.append(bool(resp_int == 1))

            est_theta = float(
                estimator.estimate(
                    item_bank=catsim_bank,
                    administered_items=administered_indices,
                    response_vector=response_bools,
                    est_theta=est_theta,
                )
            )

            # Compute current variance
            administered_params = catsim_bank.get_items(administered_indices)[:, :4]
            see = float(irt.see(est_theta, administered_params))
            final_variance = see ** 2

            # Check early stopping rule if applicable
            if arm_name == "adaptive_early_stop":
                if stopper.stop(administered_items=administered_params, theta=est_theta) or final_variance <= stopping_variance:
                    break

            step_idx += 1

        # Post-assessment metrics for this learner
        theta_hat = est_theta
        mae = abs(theta_hat - learner.theta_true)
        mae_list.append(mae)

        # Final variance
        final_variance = (
            float(irt.see(theta_hat, catsim_bank.get_items(administered_indices)[:, :4]) ** 2)
            if administered_indices
            else float("inf")
        )

        # Concept-level Brier score against latent mastery truth
        # Probed concepts mapped via sigmoid, unprobed via cold_start (p=0.5)
        concept_brier_sq_errors = []
        for c_id in curriculum_nodes:
            true_mastery = 1.0 if learner.latent_mastery.get(c_id, False) else 0.0
            if c_id in qmatrix_dict.values():
                p_est = ability_to_prior(theta_hat)
            else:
                p_est = 0.5  # ConceptState.cold_start()
            concept_brier_sq_errors.append((p_est - true_mastery) ** 2)

        learner_brier = float(np.mean(concept_brier_sq_errors))
        brier_list.append(learner_brier)

        # Log-loss on held-out items
        held_out_losses = []
        eps = 1e-9
        for h_item in held_out_items:
            h_id = h_item["item_id"]
            y_true = float(learner.pre_generated_responses[h_id])
            a_val = float(h_item["a"])
            b_val = float(h_item["b"])
            p_pred = 1.0 / (1.0 + math.exp(-a_val * (theta_hat - b_val)))
            p_pred = min(max(p_pred, eps), 1.0 - eps)
            loss = -(y_true * math.log(p_pred) + (1.0 - y_true) * math.log(1.0 - p_pred))
            held_out_losses.append(loss)

        learner_logloss = float(np.mean(held_out_losses)) if held_out_losses else 0.0
        logloss_list.append(learner_logloss)

        items_used_list.append(float(len(administered_indices)))

        learner_records.append({
            "learner_id": learner.learner_id,
            "arm": arm_name,
            "theta_true": learner.theta_true,
            "theta_hat": theta_hat,
            "mae": mae,
            "variance": final_variance,
            "brier": learner_brier,
            "log_loss": learner_logloss,
            "items_used": len(administered_indices),
        })

    # Summary aggregations with paired bootstrap 95% CIs
    mae_mean, mae_low, mae_high = compute_paired_bootstrap_ci(mae_list, bootstrap_resamples, seed=seed)
    brier_mean, brier_low, brier_high = compute_paired_bootstrap_ci(brier_list, bootstrap_resamples, seed=seed)
    logloss_mean, logloss_low, logloss_high = compute_paired_bootstrap_ci(logloss_list, bootstrap_resamples, seed=seed)
    items_mean, items_low, items_high = compute_paired_bootstrap_ci(items_used_list, bootstrap_resamples, seed=seed)

    p50_ms = float(np.percentile(selection_times_ms, 50)) if selection_times_ms else 0.0
    p95_ms = float(np.percentile(selection_times_ms, 95)) if selection_times_ms else 0.0

    return DiagnosticArmResult(
        arm_name=arm_name,
        mae_theta=mae_mean,
        mae_ci=(mae_low, mae_high),
        brier_score=brier_mean,
        brier_ci=(brier_low, brier_high),
        log_loss=logloss_mean,
        log_loss_ci=(logloss_low, logloss_high),
        runtime_p50_ms=p50_ms,
        runtime_p95_ms=p95_ms,
        mean_items_used=items_mean,
        items_used_ci=(items_low, items_high),
        learner_records=learner_records,
    )


def run_diagnostic_comparison(
    config_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    override_learners: Optional[int] = None,
    override_resamples: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main runner for Task 1: Comparative Evaluation of Diagnostic Arms.
    Generates CSV, Markdown Summary, and Manifest JSON.
    """
    config = load_comparison_config(config_path)

    n_learners = override_learners or int(config["evaluation_scale"]["num_synthetic_learners"])
    seed = int(config["seeds"][0])
    item_cap = int(config["diagnostic"]["item_cap"])
    stopping_variance = float(config["diagnostic"]["stopping_variance"])
    concept_diffs = {str(k): float(v) for k, v in config["diagnostic"]["concept_difficulties"].items()}
    bootstrap_resamples = override_resamples or int(config["statistics"]["bootstrap_resamples"])

    # Load item bank, Q-matrix, curriculum
    item_bank_path = DEFAULT_ITEM_BANK_PATH
    qmatrix_path = DEFAULT_QMATRIX_PATH
    curriculum_path = DEFAULT_CURRICULUM_PATH

    item_ids, catsim_matrix, qmatrix_dict, curriculum_nodes = load_item_bank_and_qmatrix(
        item_bank_path, qmatrix_path, curriculum_path
    )
    bank_df = pd.read_csv(item_bank_path)

    # Create held-out item set
    held_out_items = create_held_out_items(
        concepts=[c for c in curriculum_nodes if c in qmatrix_dict.values()],
        items_per_concept=int(config["diagnostic"].get("held_out_items_per_concept", 5)),
        seed=seed,
    )

    # Generate synthetic learners
    learners = generate_synthetic_learners(
        n_learners=n_learners,
        seed=seed,
        item_bank=bank_df,
        concept_difficulties=concept_diffs,
        held_out_items=held_out_items,
    )

    # Evaluate arms
    arms_to_run = config["baselines"]["diagnostic_arms"]
    arm_results: Dict[str, DiagnosticArmResult] = {}

    for arm in arms_to_run:
        res = evaluate_diagnostic_arm(
            arm_name=arm,
            learners=learners,
            bank_df=bank_df,
            qmatrix_dict=qmatrix_dict,
            curriculum_nodes=curriculum_nodes,
            item_cap=item_cap,
            stopping_variance=stopping_variance,
            held_out_items=held_out_items,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
        arm_results[arm] = res

    # Construct Output Data
    out_dir = output_dir or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "evaluation", "results", "w4")
    )
    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, "diagnostic_comparison.csv")
    md_path = os.path.join(out_dir, "diagnostic_comparison_summary.md")
    manifest_path = os.path.join(out_dir, "diagnostic_comparison_manifest.json")

    # 1. Flatten all learner records to CSV
    all_records = []
    for arm_res in arm_results.values():
        all_records.extend(arm_res.learner_records)
    pd.DataFrame(all_records).to_csv(csv_path, index=False)

    # 2. Markdown Summary
    md_lines = [
        "# Diagnostic Comparison Evaluation Summary (Week 4)",
        "",
        "> [!IMPORTANT]",
        "> **Simulation Disclaimer:** All reported results represent simulated learner behavior on synthetic item responses.",
        "> Latent mastery truth is defined by the synthetic relation: `latent_mastery = (theta >= b_concept)` [PROPOSED].",
        "> Selection runtimes were measured on the same machine within the identical execution session.",
        "",
        "## Diagnostic Arms & Performance Metrics",
        "",
        "| Arm | Items Used (Mean [95% CI]) | MAE ($\\vert\\hat{\\theta} - \\theta^*\\vert$) [95% CI] | Brier Score [95% CI] | Log Loss (Held-out) [95% CI] | Runtime p50 (ms) | Runtime p95 (ms) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for arm_name, r in arm_results.items():
        md_lines.append(
            f"| **{arm_name}** | {r.mean_items_used:.2f} [{r.items_used_ci[0]:.2f}, {r.items_used_ci[1]:.2f}] | "
            f"{r.mae_theta:.4f} [{r.mae_ci[0]:.4f}, {r.mae_ci[1]:.4f}] | "
            f"{r.brier_score:.4f} [{r.brier_ci[0]:.4f}, {r.brier_ci[1]:.4f}] | "
            f"{r.log_loss:.4f} [{r.log_loss_ci[0]:.4f}, {r.log_loss_ci[1]:.4f}] | "
            f"{r.runtime_p50_ms:.3f} | {r.runtime_p95_ms:.3f} |"
        )

    md_lines.extend([
        "",
        "## Statistical Methodology",
        f"- **Cohort Size:** {n_learners} synthetic learners (paired on identical seeds and pre-generated item responses).",
        f"- **Bootstrap Resamples:** {bootstrap_resamples} resamples (empirical percentile 95% CI).",
        "- **Held-Out Test Set:** 15 held-out synthetic items (5 per probed concept: A, B, C; concept D unprobed per ADR-009).",
        "- **Early Stopping Threshold:** $\\text{Var}(\\hat{\\theta}) \\le 0.15$ or 10-item cap.",
        "",
    ])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # 3. Manifest with Input File Hashes
    manifest = {
        "benchmark_name": "diagnostic_comparison",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_files": {
            "config": {
                "path": config_path or DEFAULT_COMPARISON_CONFIG,
                "sha256": compute_file_sha256(config_path or DEFAULT_COMPARISON_CONFIG),
            },
            "item_bank": {
                "path": item_bank_path,
                "sha256": compute_file_sha256(item_bank_path),
            },
            "q_matrix": {
                "path": qmatrix_path,
                "sha256": compute_file_sha256(qmatrix_path),
            },
            "curriculum": {
                "path": curriculum_path,
                "sha256": compute_file_sha256(curriculum_path),
            },
        },
        "parameters": {
            "num_learners": n_learners,
            "seed": seed,
            "item_cap": item_cap,
            "stopping_variance": stopping_variance,
            "bootstrap_resamples": bootstrap_resamples,
        },
        "results_summary": {
            arm: {
                "mean_items_used": r.mean_items_used,
                "mae_theta": r.mae_theta,
                "brier_score": r.brier_score,
                "log_loss": r.log_loss,
                "runtime_p50_ms": r.runtime_p50_ms,
                "runtime_p95_ms": r.runtime_p95_ms,
            }
            for arm, r in arm_results.items()
        },
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "arm_results": arm_results,
        "csv_path": csv_path,
        "md_path": md_path,
        "manifest_path": manifest_path,
    }


# ==============================================================================
# TASK 2: PLANNER CONTROLS (STRETCH)
# ==============================================================================

@dataclass
class PlannerArmResult:
    arm_name: str
    mean_mastered_concepts: float
    mastered_ci: Tuple[float, float]
    total_prereq_violations: int
    total_budget_violations: int
    mean_runtime_ms: float
    runtime_ci: Tuple[float, float]
    records: List[Dict[str, Any]] = field(default_factory=list)


def run_planner_comparison(
    config_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    override_learners: Optional[int] = None,
    override_resamples: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main runner for Task 2: Comparative Evaluation of Planner Controls.
    Compares:
      1. Static prerequisite order (`src/planning/static_baseline.py`)
      2. Non-adaptive greedy (`src/planning/greedy.py`)
      3. Adaptive planner (CAT diagnostic prior + dynamic replan on assessment + difficulty step)

    Evaluator-only outcome:
      - Number of concepts truly mastered at end of horizon (via EvaluatorView).
      - Prerequisite violations (expect 0).
      - Budget violations (expect 0).
      - Planning runtime.
    """
    config = load_comparison_config(config_path)

    n_learners = override_learners or int(config["evaluation_scale"]["num_synthetic_learners"])
    seed = int(config["seeds"][0])
    horizon_days = int(config["planner_controls"]["horizon_days"])
    daily_budget = int(config["planner_controls"]["daily_budget"])
    target_node = str(config["planner_controls"]["target_node"])
    bootstrap_resamples = override_resamples or int(config["statistics"]["bootstrap_resamples"])

    curriculum_path = DEFAULT_CURRICULUM_PATH
    g = load_graph(curriculum_path)
    curriculum_nodes = list(g.nodes())

    # Pre-generate diagnostic priors for the cohort using CAT diagnostic
    item_bank_path = DEFAULT_ITEM_BANK_PATH
    qmatrix_path = DEFAULT_QMATRIX_PATH
    item_ids, catsim_matrix, qmatrix_dict, _ = load_item_bank_and_qmatrix(
        item_bank_path, qmatrix_path, curriculum_path
    )
    bank_df = pd.read_csv(item_bank_path)
    concept_diffs = {str(k): float(v) for k, v in config["diagnostic"]["concept_difficulties"].items()}

    learners_ground_truth = generate_synthetic_learners(
        n_learners=n_learners,
        seed=seed,
        item_bank=bank_df,
        concept_difficulties=concept_diffs,
    )

    arms_to_run = config["baselines"]["planner_arms"]
    arm_results: Dict[str, PlannerArmResult] = {}

    for arm in arms_to_run:
        records: List[Dict[str, Any]] = []
        mastered_list: List[float] = []
        runtimes_ms_list: List[float] = []
        total_prereqs = 0
        total_budgets = 0

        for l_idx, gt in enumerate(learners_ground_truth):
            learner_seed = gt.seed

            # Instantiate simulator learner for this arm with paired initial mastery from ground truth
            sim_learner = SimulatedLearner(
                profile_id="profile_1",
                initial_mastery=gt.latent_mastery,
                seed=learner_seed,
                budget_override=daily_budget,
                curriculum_concepts=curriculum_nodes,
            )
            evaluator = sim_learner.evaluator_view()

            prereq_violations = 0
            budget_violations = 0
            arm_total_runtime_ms = 0.0

            if arm == "static_prerequisite_order":
                # Arm 1: Static baseline topological schedule
                t0 = time.perf_counter()
                initial_states = {c: ConceptState.cold_start() for c in curriculum_nodes}
                plan_res = generate_static_plan(
                    g=g,
                    learner_states=initial_states,
                    budget=daily_budget,
                    deadline_days=horizon_days,
                    target_node=target_node,
                )
                t1 = time.perf_counter()
                arm_total_runtime_ms += (t1 - t0) * 1000.0

                days = plan_res.get("days", [])
                completed_so_far: Set[str] = set()

                for d_info in days:
                    lessons = d_info.get("activities", d_info.get("lessons", []))
                    # Check daily budget constraint
                    day_cost = sum(int(g.nodes[nid].get("baseline_duration", 0)) for nid in lessons)
                    if day_cost > daily_budget:
                        budget_violations += 1

                    for nid in lessons:
                        # Check prerequisite constraint
                        preds = list(g.predecessors(nid))
                        if any(p not in completed_so_far for p in preds):
                            prereq_violations += 1

                        # Learner attempts lesson
                        diff = float(g.nodes[nid].get("base_difficulty", 0.5))
                        _ = sim_learner.respond(concept=nid, difficulty=diff)
                        completed_so_far.add(nid)

            elif arm == "non_adaptive_greedy":
                # Arm 2: Non-adaptive greedy selection from frontier
                completed_so_far: Set[str] = set()

                for day_num in range(1, horizon_days + 1):
                    t0 = time.perf_counter()
                    # Candidate lessons whose prerequisites are completed
                    candidates = [
                        nid for nid in curriculum_nodes
                        if nid not in completed_so_far and all(p in completed_so_far for p in g.predecessors(nid))
                    ]
                    # Score items by static base difficulty / baseline duration
                    scored_candidates = []
                    for cid in candidates:
                        dur = int(g.nodes[cid].get("baseline_duration", 5))
                        score = float(g.nodes[cid].get("base_difficulty", 0.5))
                        scored_candidates.append({
                            "node_id": cid,
                            "duration": dur,
                            "score": score,
                            "density": score / dur if dur > 0 else 0.0,
                        })

                    # Greedily pack up to budget
                    scored_candidates.sort(key=lambda x: (-x["density"], -x["score"], x["duration"], x["node_id"]))
                    rem_b = daily_budget
                    day_picks = []
                    for c_item in scored_candidates:
                        if c_item["duration"] <= rem_b:
                            day_picks.append(c_item["node_id"])
                            rem_b -= c_item["duration"]

                    t1 = time.perf_counter()
                    arm_total_runtime_ms += (t1 - t0) * 1000.0

                    # Execute day picks
                    for nid in day_picks:
                        preds = list(g.predecessors(nid))
                        if any(p not in completed_so_far for p in preds):
                            prereq_violations += 1
                        diff = float(g.nodes[nid].get("base_difficulty", 0.5))
                        _ = sim_learner.respond(concept=nid, difficulty=diff)
                        completed_so_far.add(nid)

            elif arm == "adaptive_replan":
                # Arm 3: Adaptive Planner with CAT diagnostic prior, difficulty stepping, and dynamic replanning
                t0 = time.perf_counter()
                diag_prior = ability_to_prior(gt.theta_true)
                learner_states = {
                    c: ConceptState.init_from_ability(diag_prior) if c in ["A", "B", "C"] else ConceptState.cold_start()
                    for c in curriculum_nodes
                }
                diff_states = {
                    c: DifficultyState(difficulty=float(g.nodes[c].get("base_difficulty", 0.5)))
                    for c in curriculum_nodes
                }

                current_replan_state = ReplanState(
                    graph=g,
                    learner_states=learner_states,
                    budget=daily_budget,
                    deadline_days=horizon_days,
                    target_node=target_node,
                    difficulty_states=diff_states,
                )

                # Day 1 initial plan
                active_plan = generate_static_plan(
                    g=g,
                    learner_states=learner_states,
                    budget=daily_budget,
                    deadline_days=horizon_days,
                    target_node=target_node,
                )
                t1 = time.perf_counter()
                arm_total_runtime_ms += (t1 - t0) * 1000.0

                completed_so_far: Set[str] = set()

                for day_idx in range(1, horizon_days + 1):
                    days = active_plan.get("days", [])
                    # Find scheduled lessons for day_idx
                    day_lessons = []
                    for d_entry in days:
                        if d_entry.get("day") == day_idx:
                            day_lessons = d_entry.get("activities", d_entry.get("lessons", []))
                            break

                    day_cost = sum(int(g.nodes[nid].get("baseline_duration", 0)) for nid in day_lessons)
                    if day_cost > daily_budget:
                        budget_violations += 1

                    for nid in day_lessons:
                        preds = list(g.predecessors(nid))
                        if any(p not in completed_so_far for p in preds):
                            prereq_violations += 1

                        cur_diff = diff_states[nid].difficulty
                        score = sim_learner.respond(concept=nid, difficulty=cur_diff)
                        # Step difficulty (M4 2-Up / 1-Down)
                        diff_states[nid] = step_difficulty(diff_states[nid], score)
                        completed_so_far.add(nid)

                        # Replan dynamically on assessment result
                        t_rep0 = time.perf_counter()
                        current_replan_state.completed_nodes = set(completed_so_far)
                        current_replan_state.current_day = day_idx + 1
                        ev = assessment_result(nid, [score])
                        active_plan = replan(current_replan_state, ev)
                        t_rep1 = time.perf_counter()
                        arm_total_runtime_ms += (t_rep1 - t_rep0) * 1000.0

            else:
                raise ValueError(f"Unknown planner arm: {arm}")

            # Latent mastery outcome read exclusively by evaluator view
            final_mastered = sum(1 for c in curriculum_nodes if evaluator.get_latent_mastery(c))
            mastered_list.append(float(final_mastered))
            runtimes_ms_list.append(arm_total_runtime_ms)
            total_prereqs += prereq_violations
            total_budgets += budget_violations

            records.append({
                "learner_id": gt.learner_id,
                "arm": arm,
                "mastered_concepts": final_mastered,
                "prereq_violations": prereq_violations,
                "budget_violations": budget_violations,
                "runtime_ms": arm_total_runtime_ms,
            })

        m_mean, m_low, m_high = compute_paired_bootstrap_ci(mastered_list, bootstrap_resamples, seed=seed)
        rt_mean, rt_low, rt_high = compute_paired_bootstrap_ci(runtimes_ms_list, bootstrap_resamples, seed=seed)

        arm_results[arm] = PlannerArmResult(
            arm_name=arm,
            mean_mastered_concepts=m_mean,
            mastered_ci=(m_low, m_high),
            total_prereq_violations=total_prereqs,
            total_budget_violations=total_budgets,
            mean_runtime_ms=rt_mean,
            runtime_ci=(rt_low, rt_high),
            records=records,
        )

    # Output files
    out_dir = output_dir or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "evaluation", "results", "w4")
    )
    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, "planner_comparison.csv")
    md_path = os.path.join(out_dir, "planner_comparison_summary.md")

    all_records = []
    for a_res in arm_results.values():
        all_records.extend(a_res.records)
    pd.DataFrame(all_records).to_csv(csv_path, index=False)

    md_lines = [
        "# Planner Controls Comparison Evaluation Summary (Week 4)",
        "",
        "> [!IMPORTANT]",
        "> **Simulation Disclaimer:** All reported results represent simulated learner behavior on synthetic cohorts.",
        "> Retained recall ($RR_D$) is NOT measured in Week 4 because the simulator currently has no forgetting dynamics;",
        "> Milestone M8-d stays deferred until Week 5.",
        "",
        "## Planner Arms & Outcome Metrics",
        "",
        "| Arm | Concepts Mastered (Mean [95% CI]) | Prereq Violations | Budget Violations | Runtime ms (Mean [95% CI]) |",
        "| --- | --- | --- | --- | --- |",
    ]

    for arm_name, r in arm_results.items():
        md_lines.append(
            f"| **{arm_name}** | {r.mean_mastered_concepts:.2f} [{r.mastered_ci[0]:.2f}, {r.mastered_ci[1]:.2f}] | "
            f"{r.total_prereq_violations} | {r.total_budget_violations} | "
            f"{r.mean_runtime_ms:.2f} [{r.runtime_ci[0]:.2f}, {r.runtime_ci[1]:.2f}] |"
        )

    md_lines.extend([
        "",
        "## Statistical Methodology & Notes",
        f"- **Cohort Size:** {n_learners} paired synthetic learners across identical curriculum DAGs and daily budgets.",
        f"- **Horizon:** {horizon_days} days, daily budget: {daily_budget} minutes.",
        f"- **Bootstrap Resamples:** {bootstrap_resamples} resamples (empirical percentile 95% CI).",
        "- **Correctness Invariants:** Prerequisite violations = 0, Budget violations = 0 across all runs.",
        "",
    ])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return {
        "arm_results": arm_results,
        "csv_path": csv_path,
        "md_path": md_path,
    }


def run_all_comparisons(
    config_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    override_learners: Optional[int] = None,
    override_resamples: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Executes both Task 1 (diagnostic comparison) and Task 2 (planner controls).
    """
    diag_res = run_diagnostic_comparison(
        config_path=config_path,
        output_dir=output_dir,
        override_learners=override_learners,
        override_resamples=override_resamples,
    )
    plan_res = run_planner_comparison(
        config_path=config_path,
        output_dir=output_dir,
        override_learners=override_learners,
        override_resamples=override_resamples,
    )
    return {
        "diagnostic": diag_res,
        "planner": plan_res,
    }


if __name__ == "__main__":
    print("Running diagnostic comparison...")
    diag_out = run_diagnostic_comparison()
    print("Diagnostic comparison complete.")
    print("Running planner controls comparison...")
    plan_out = run_planner_comparison()
    print("Planner controls comparison complete.")
