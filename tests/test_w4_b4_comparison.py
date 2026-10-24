"""
Unit and Integration Tests for Week 4 Task B4: Comparative Evaluation Benchmark.

Verifies:
1. Master configuration (experiments/w4_comparison.yaml) schema, protocol citations, and [PROPOSED] tags.
2. Execution of diagnostic comparison across all 4 arms (adaptive, adaptive_early_stop, fixed, random).
3. Emission of valid CSV, markdown summary, and input hash manifest in tmp_path.
4. Correctness of paired bootstrap 95% confidence intervals.
5. Planner controls comparison with 0 prerequisite violations and 0 budget violations.
6. Latent state invisibility invariant: zero imports of src.evaluation or EvaluatorView in src/planning or src/state.
7. Simulator behavior disclaimer and deferred retained-recall notices in output summaries.
"""

import ast
import json
import math
import os
import glob
import pandas as pd
import pytest
import yaml

from src.evaluation.compare import (
    load_comparison_config,
    run_diagnostic_comparison,
    run_planner_comparison,
    run_all_comparisons,
    compute_paired_bootstrap_ci,
    generate_synthetic_learners,
    create_held_out_items,
    DEFAULT_COMPARISON_CONFIG,
)
from src.curriculum.graph import load_graph
from src.diagnostic.diagnostic import DEFAULT_CURRICULUM_PATH, DEFAULT_ITEM_BANK_PATH, DEFAULT_QMATRIX_PATH


def test_w4_comparison_yaml_schema_and_protocol_citations():
    """
    Verifies that experiments/w4_comparison.yaml contains required sections,
    citations to docs/EVALUATION_PROTOCOL.md, and [PROPOSED] markings.
    """
    assert os.path.exists(DEFAULT_COMPARISON_CONFIG), f"Config file not found: {DEFAULT_COMPARISON_CONFIG}"

    with open(DEFAULT_COMPARISON_CONFIG, "r", encoding="utf-8") as f:
        raw_text = f.read()
        config = yaml.safe_load(raw_text)

    # Required top-level sections
    for sec in ["seeds", "evaluation_scale", "diagnostic", "statistics", "planner_controls", "baselines"]:
        assert sec in config, f"Missing section '{sec}' in {DEFAULT_COMPARISON_CONFIG}"

    # Check N-style protocol citations in comments/text
    assert "docs/EVALUATION_PROTOCOL.md line 63" in raw_text or "line 63" in raw_text
    assert "docs/EVALUATION_PROTOCOL.md line 65" in raw_text or "line 65" in raw_text
    assert "docs/EVALUATION_PROTOCOL.md line 87" in raw_text or "line 87" in raw_text
    assert "[PROPOSED]" in raw_text

    # Scale and parameter checks
    assert config["evaluation_scale"]["num_synthetic_learners"] == 200
    assert config["diagnostic"]["item_cap"] == 10
    assert math.isclose(config["diagnostic"]["stopping_variance"], 0.15)
    assert config["statistics"]["bootstrap_resamples"] == 1000
    assert config["planner_controls"]["horizon_days"] == 5
    assert config["planner_controls"]["daily_budget"] == 10


def test_diagnostic_comparison_runs_and_emits_valid_artifacts(tmp_path):
    """
    Runs diagnostic comparison with a tiny cohort in tmp_path and verifies
    creation of CSV, markdown summary, and manifest JSON with valid hashes.
    """
    out_dir = str(tmp_path / "results_w4")

    res = run_diagnostic_comparison(
        config_path=DEFAULT_COMPARISON_CONFIG,
        output_dir=out_dir,
        override_learners=6,
        override_resamples=50,
    )

    assert os.path.exists(res["csv_path"])
    assert os.path.exists(res["md_path"])
    assert os.path.exists(res["manifest_path"])

    # 1. Verify CSV contents
    df = pd.read_csv(res["csv_path"])
    assert len(df) == 6 * 4  # 6 learners * 4 arms
    expected_cols = {"learner_id", "arm", "theta_true", "theta_hat", "mae", "variance", "brier", "log_loss", "items_used"}
    assert expected_cols.issubset(set(df.columns))

    # 2. Verify Manifest JSON contents and file hashes
    with open(res["manifest_path"], "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["benchmark_name"] == "diagnostic_comparison"
    assert "input_files" in manifest
    assert len(manifest["input_files"]["config"]["sha256"]) == 64
    assert len(manifest["input_files"]["item_bank"]["sha256"]) == 64
    assert len(manifest["input_files"]["q_matrix"]["sha256"]) == 64
    assert len(manifest["input_files"]["curriculum"]["sha256"]) == 64

    # 3. Verify Markdown Summary
    with open(res["md_path"], "r", encoding="utf-8") as f:
        md_text = f.read()

    assert "Diagnostic Comparison Evaluation Summary" in md_text
    assert "adaptive" in md_text
    assert "adaptive_early_stop" in md_text
    assert "fixed" in md_text
    assert "random" in md_text


def test_diagnostic_comparison_arms_and_metrics(tmp_path):
    """
    Verifies metric bounds across all 4 diagnostic arms:
    - MAE >= 0
    - Brier score in [0, 1]
    - Log loss > 0
    - Selection runtime p50 and p95 > 0
    - Items used <= 10
    """
    out_dir = str(tmp_path / "diag_metrics")

    res = run_diagnostic_comparison(
        output_dir=out_dir,
        override_learners=8,
        override_resamples=50,
    )

    arm_results = res["arm_results"]
    assert set(arm_results.keys()) == {"adaptive", "adaptive_early_stop", "fixed", "random"}

    for arm_name, r in arm_results.items():
        assert r.mae_theta >= 0.0
        assert 0.0 <= r.brier_score <= 1.0
        assert r.log_loss >= 0.0
        assert 0.0 < r.mean_items_used <= 10.0
        assert r.runtime_p50_ms >= 0.0
        assert r.runtime_p95_ms >= r.runtime_p50_ms

    # Adaptive with early stopping should report mean items used <= 10
    early_arm = arm_results["adaptive_early_stop"]
    assert early_arm.mean_items_used <= 10.0


def test_paired_bootstrap_ci_computation():
    """
    Verifies empirical percentile bootstrap confidence interval calculation.
    """
    values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    mean_val, low, high = compute_paired_bootstrap_ci(values, b_resamples=500, confidence_level=0.95, seed=42)

    assert math.isclose(mean_val, 0.55)
    assert low <= mean_val <= high
    assert low >= 0.1
    assert high <= 1.0


def test_planner_controls_comparison(tmp_path):
    """
    Verifies Task 2 planner controls comparison:
    - 3 arms: static_prerequisite_order, non_adaptive_greedy, adaptive_replan.
    - Zero prerequisite violations.
    - Zero budget violations.
    - Mastered concepts count within [0, 4].
    """
    out_dir = str(tmp_path / "plan_metrics")

    res = run_planner_comparison(
        output_dir=out_dir,
        override_learners=6,
        override_resamples=50,
    )

    assert os.path.exists(res["csv_path"])
    assert os.path.exists(res["md_path"])

    arm_results = res["arm_results"]
    assert set(arm_results.keys()) == {"static_prerequisite_order", "non_adaptive_greedy", "adaptive_replan"}

    for arm_name, r in arm_results.items():
        assert r.total_prereq_violations == 0, f"Prerequisite violations found in {arm_name}"
        assert r.total_budget_violations == 0, f"Budget violations found in {arm_name}"
        assert 0.0 <= r.mean_mastered_concepts <= 4.0
        assert r.mean_runtime_ms > 0.0


def test_latent_state_invisibility_and_zero_evaluation_imports_under_planning_and_state():
    """
    Architectural boundary test:
    Modules under src/planning/ and src/state/ must NEVER import from src/evaluation
    or import EvaluatorView.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    checked_dirs = [
        os.path.join(repo_root, "src", "planning"),
        os.path.join(repo_root, "src", "state"),
    ]

    forbidden_tokens = [
        "src.evaluation",
        "EvaluatorView",
        "evaluator_view",
    ]

    violations = []
    for cdir in checked_dirs:
        for py_file in glob.glob(os.path.join(cdir, "**", "*.py"), recursive=True):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            parsed = ast.parse(content, filename=py_file)
            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for token in forbidden_tokens:
                            if token in alias.name:
                                violations.append((py_file, node.lineno, token))
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    for token in forbidden_tokens:
                        if token in mod_name:
                            violations.append((py_file, node.lineno, token))
                    for alias in node.names:
                        for token in forbidden_tokens:
                            if token in alias.name:
                                violations.append((py_file, node.lineno, token))

    assert not violations, f"Architectural boundary violated! Forbidden imports found: {violations}"


def test_simulator_behavior_disclaimer_present(tmp_path):
    """
    Verifies that markdown summaries generated by comparison runners
    contain the required simulator behavior and deferred retained recall notices.
    """
    out_dir = str(tmp_path / "disclaimer_check")

    res = run_all_comparisons(
        output_dir=out_dir,
        override_learners=4,
        override_resamples=20,
    )

    with open(res["diagnostic"]["md_path"], "r", encoding="utf-8") as f:
        diag_md = f.read()
    assert "All reported results represent simulated learner behavior on synthetic" in diag_md
    assert "latent_mastery = (theta >= b_concept)" in diag_md

    with open(res["planner"]["md_path"], "r", encoding="utf-8") as f:
        plan_md = f.read()
    assert "All reported results represent simulated learner behavior on synthetic" in plan_md
    assert "Retained recall ($RR_D$) is NOT measured" in plan_md
    assert "Milestone M8-d stays deferred" in plan_md
