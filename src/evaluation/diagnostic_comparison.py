"""
Week 8 (M2 evidence): pooled five-seed diagnostic comparison with paired differences.

Runs the Week 4 diagnostic arms of src/evaluation/compare.py (evaluate_diagnostic_arm,
same cohorts, held-out items and metrics) for every seed in the config instead of the
first one only, pools the per-learner rows across seeds, and reports paired per-learner
differences adaptive - fixed and adaptive - random with 95% percentile bootstrap CIs
(compute_paired_bootstrap_ci, B from the config, seed 42), as scripts/w7_pooled_s0.py
does for integrated runs.

Metrics (lower is better for all three):
  abs_theta_error  |theta_hat - theta*|
  brier            concept Brier score against latent mastery (theta* >= b_concept)
  log_loss         log loss on held-out 2PL items

Claim rule: "X improves on Y" only if the paired 95% CI of the difference excludes
zero; otherwise "no difference shown". For a lower-is-better metric, a - b < 0 means a
is better.

Usage:
  python -m src.evaluation.diagnostic_comparison [--config experiments/w4_comparison.yaml]
      [--out evaluation/results/w8/diagnostic_comparison]
"""

import argparse
import json
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.diagnostic.diagnostic import (
    DEFAULT_CURRICULUM_PATH,
    DEFAULT_ITEM_BANK_PATH,
    DEFAULT_QMATRIX_PATH,
    load_item_bank_and_qmatrix,
)
from src.evaluation.compare import (
    DEFAULT_COMPARISON_CONFIG,
    compute_file_sha256,
    compute_paired_bootstrap_ci,
    create_held_out_items,
    evaluate_diagnostic_arm,
    generate_synthetic_learners,
    load_comparison_config,
)
from src.provenance import get_git_info, get_package_versions, resolved_config_hash

REFERENCE_ARM = "adaptive"
COMPARED_ARMS = ("fixed", "random")
METRICS = ("abs_theta_error", "brier", "log_loss")
METRIC_LABELS = {  # markdown table cells: literal pipes escaped
    "abs_theta_error": "\\|θ̂ − θ*\\| error",
    "brier": "concept Brier score",
    "log_loss": "held-out log loss",
}
CI_SEED = 42


def paired_difference(
    a: Sequence[float],
    b: Sequence[float],
    b_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = CI_SEED,
) -> Tuple[float, float, float]:
    """Mean of the paired differences a_i - b_i with a percentile bootstrap CI.

    a and b must be aligned per learner. Returns (mean, ci_low, ci_high).
    """
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if a_arr.shape != b_arr.shape:
        raise ValueError(f"paired arrays differ in length: {a_arr.shape} vs {b_arr.shape}")
    return compute_paired_bootstrap_ci(a_arr - b_arr, b_resamples, confidence_level, seed)


def claim_lower_is_better(arm_a: str, arm_b: str, mean: float, lo: float, hi: float) -> str:
    """Claim for a - b on a metric where lower is better."""
    if hi < 0.0:
        return f"{arm_a} improves on {arm_b} [{abs(hi):.4f}, {abs(lo):.4f}]"
    if lo > 0.0:
        return f"{arm_b} improves on {arm_a} [{lo:.4f}, {hi:.4f}]"
    return "no difference shown"


def _run_seed(config: Dict[str, Any], seed: int, n_learners: int, resamples: int) -> List[Dict[str, Any]]:
    """One cohort, set up exactly as compare.run_diagnostic_comparison does for its seed."""
    item_cap = int(config["diagnostic"]["item_cap"])
    stopping_variance = float(config["diagnostic"]["stopping_variance"])
    concept_diffs = {str(k): float(v) for k, v in config["diagnostic"]["concept_difficulties"].items()}

    _, _, qmatrix_dict, curriculum_nodes = load_item_bank_and_qmatrix(
        DEFAULT_ITEM_BANK_PATH, DEFAULT_QMATRIX_PATH, DEFAULT_CURRICULUM_PATH
    )
    bank_df = pd.read_csv(DEFAULT_ITEM_BANK_PATH)
    held_out_items = create_held_out_items(
        concepts=[c for c in curriculum_nodes if c in qmatrix_dict.values()],
        items_per_concept=int(config["diagnostic"].get("held_out_items_per_concept", 5)),
        seed=seed,
    )
    learners = generate_synthetic_learners(
        n_learners=n_learners, seed=seed, item_bank=bank_df,
        concept_difficulties=concept_diffs, held_out_items=held_out_items,
    )
    seed_by_id = {l.learner_id: l.seed for l in learners}

    rows: List[Dict[str, Any]] = []
    for arm in config["baselines"]["diagnostic_arms"]:
        res = evaluate_diagnostic_arm(
            arm_name=arm, learners=learners, bank_df=bank_df, qmatrix_dict=qmatrix_dict,
            curriculum_nodes=curriculum_nodes, item_cap=item_cap, stopping_variance=stopping_variance,
            held_out_items=held_out_items, bootstrap_resamples=resamples, seed=seed,
        )
        for rec in res.learner_records:
            rows.append({
                "cohort_seed": seed,
                "learner_seed": seed_by_id[rec["learner_id"]],
                "learner_id": rec["learner_id"],
                "arm": arm,
                "theta_true": rec["theta_true"],
                "theta_hat": rec["theta_hat"],
                "abs_theta_error": rec["mae"],
                "brier": rec["brier"],
                "log_loss": rec["log_loss"],
                "items_used": rec["items_used"],
                "variance": rec["variance"],
            })
    return rows


def _aligned(df: pd.DataFrame, arm: str) -> pd.DataFrame:
    g = df[df.arm == arm].sort_values(["cohort_seed", "learner_seed"], kind="mergesort")
    return g.reset_index(drop=True)


def run_pooled_diagnostic_comparison(
    config_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    override_learners: Optional[int] = None,
    override_resamples: Optional[int] = None,
) -> Dict[str, Any]:
    """Runs every configured seed, pools, and writes per_learner.csv, summary.md, manifest.json."""
    cfg_file = config_path or DEFAULT_COMPARISON_CONFIG
    # Git state before any output is written, so the run's own files do not mark it dirty.
    git_sha, dirty = get_git_info()
    config = load_comparison_config(cfg_file)
    seeds = [int(s) for s in config["seeds"]]
    n_learners = override_learners or int(config["evaluation_scale"]["num_synthetic_learners"])
    resamples = override_resamples or int(config["statistics"]["bootstrap_resamples"])
    conf = float(config["statistics"].get("confidence_level", 0.95))

    rows: List[Dict[str, Any]] = []
    for s in seeds:
        rows.extend(_run_seed(config, s, n_learners, resamples))
    df = pd.DataFrame(rows)

    # Pooled per-arm means
    arm_rows = []
    for arm in config["baselines"]["diagnostic_arms"]:
        g = _aligned(df, arm)
        entry = {"arm": arm, "n": len(g), "items_used": float(g["items_used"].mean())}
        for m in METRICS:
            entry[m] = compute_paired_bootstrap_ci(g[m].values, resamples, conf, CI_SEED)
        arm_rows.append(entry)

    # Paired differences
    ref = _aligned(df, REFERENCE_ARM)
    comparisons = []
    for other in COMPARED_ARMS:
        o = _aligned(df, other)
        if not (ref[["cohort_seed", "learner_seed"]].values == o[["cohort_seed", "learner_seed"]].values).all():
            raise ValueError(f"learners of {REFERENCE_ARM} and {other} are not paired")
        for m in METRICS:
            mean, lo, hi = paired_difference(ref[m].values, o[m].values, resamples, conf, CI_SEED)
            d = ref[m].values - o[m].values
            comparisons.append({
                "arm_a": REFERENCE_ARM, "arm_b": other, "metric": m, "n_pairs": int(len(d)),
                "mean": mean, "ci_low": lo, "ci_high": hi,
                "a_lower": int((d < 0).sum()), "b_lower": int((d > 0).sum()), "ties": int((d == 0).sum()),
                "claim": claim_lower_is_better(REFERENCE_ARM, other, mean, lo, hi),
            })

    out_dir = output_dir or os.path.join(
        os.path.dirname(__file__), "..", "..", "evaluation", "results", "w8", "diagnostic_comparison")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "per_learner.csv")
    md_path = os.path.join(out_dir, "summary.md")
    manifest_path = os.path.join(out_dir, "manifest.json")

    df.to_csv(csv_path, index=False)

    lines = [
        "# Diagnostic Comparison, Pooled Paired Differences (Week 8)",
        "",
        "All results are simulator behaviour on synthetic learners (2PL responses, latent mastery "
        "`theta* >= b_concept`). No real learner data.",
        "",
        f"- Config: `{os.path.relpath(cfg_file, os.getcwd()) if os.path.isabs(cfg_file) else cfg_file}`; "
        f"seeds {seeds}; {n_learners} learners per seed; {len(ref)} paired learners per arm.",
        f"- Item cap {config['diagnostic']['item_cap']}; stopping variance {config['diagnostic']['stopping_variance']}.",
        f"- Bootstrap: B = {resamples}, {int(conf * 100)}% percentile CI, resampling seed {CI_SEED}; "
        "rows pooled in seed order and paired by (cohort seed, learner seed).",
        "- Lower is better for every metric. A difference adaptive − X below zero favours adaptive.",
        "- Claim rule: \"X improves on Y\" only if the paired 95% CI excludes zero; otherwise \"no difference shown\".",
        "- `adaptive` is maximum-information selection run to the item cap. The concept Brier score uses "
        "p = sigmoid(θ̂) for probed concepts (0.5 for unprobed D), so the Week 8 diagnostic-prior change "
        "(n, κ, history) does not enter these metrics.",
        "",
        "## Arms (pooled mean [95% CI])",
        "",
        f"| Arm | n | Items used | {METRIC_LABELS['abs_theta_error']} | Concept Brier | Held-out log loss |",
        "|---|---|---|---|---|---|",
    ]
    for e in arm_rows:
        cells = " | ".join(f"{e[m][0]:.4f} [{e[m][1]:.4f}, {e[m][2]:.4f}]" for m in METRICS)
        lines.append(f"| {e['arm']} | {e['n']} | {e['items_used']:.2f} | {cells} |")
    lines += [
        "",
        "## Paired differences (adaptive − X)",
        "",
        "| Comparison | Metric | Mean difference | 95% CI | Learners lower (adaptive / X / tie) | Claim |",
        "|---|---|---|---|---|---|",
    ]
    for c in comparisons:
        lines.append(
            f"| {c['arm_a']} − {c['arm_b']} | {METRIC_LABELS[c['metric']]} | {c['mean']:+.4f} | "
            f"[{c['ci_low']:+.4f}, {c['ci_high']:+.4f}] | {c['a_lower']} / {c['b_lower']} / {c['ties']} | {c['claim']} |"
        )
    lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    manifest = {
        "benchmark_name": "w8_diagnostic_comparison_pooled",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config_hash": resolved_config_hash(config),
        "git": {"commit_sha": git_sha, "dirty": dirty},
        "seeds": seeds,
        "package_versions": get_package_versions(),
        "parameters": {
            "num_learners_per_seed": n_learners,
            "bootstrap_resamples": resamples,
            "confidence_level": conf,
            "ci_resampling_seed": CI_SEED,
            "reference_arm": REFERENCE_ARM,
            "compared_arms": list(COMPARED_ARMS),
        },
        "input_files": {
            "config": {"path": cfg_file, "sha256": compute_file_sha256(cfg_file)},
            "curriculum": {"path": DEFAULT_CURRICULUM_PATH, "sha256": compute_file_sha256(DEFAULT_CURRICULUM_PATH)},
            "item_bank": {"path": DEFAULT_ITEM_BANK_PATH, "sha256": compute_file_sha256(DEFAULT_ITEM_BANK_PATH)},
            "q_matrix": {"path": DEFAULT_QMATRIX_PATH, "sha256": compute_file_sha256(DEFAULT_QMATRIX_PATH)},
        },
        "output_files": {
            "per_learner.csv": compute_file_sha256(csv_path),
            "summary.md": compute_file_sha256(md_path),
        },
        "results_summary": {
            f"{c['arm_a']}-{c['arm_b']}:{c['metric']}": {
                "mean": c["mean"], "ci": [c["ci_low"], c["ci_high"]], "claim": c["claim"]}
            for c in comparisons
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    return {
        "per_learner": df,
        "arms": arm_rows,
        "comparisons": comparisons,
        "csv_path": csv_path,
        "md_path": md_path,
        "manifest_path": manifest_path,
    }


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", default="experiments/w4_comparison.yaml")
    ap.add_argument("--out", default="evaluation/results/w8/diagnostic_comparison")
    ap.add_argument("--learners", type=int, default=None)
    ap.add_argument("--resamples", type=int, default=None)
    args = ap.parse_args(argv)
    res = run_pooled_diagnostic_comparison(args.config, args.out, args.learners, args.resamples)
    for c in res["comparisons"]:
        print(f"{c['arm_a']} - {c['arm_b']} {c['metric']}: {c['mean']:+.4f} "
              f"[{c['ci_low']:+.4f}, {c['ci_high']:+.4f}] -> {c['claim']}")
    print(f"wrote {res['csv_path']}, {res['md_path']}, {res['manifest_path']}")


if __name__ == "__main__":
    main()
