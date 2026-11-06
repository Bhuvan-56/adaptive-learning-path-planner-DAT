"""
Tests for Beta Task B3: Harness-Level Retention Quiz Evaluation.

Verifies:
1. The integrated evaluation harness writes a retained recall value per learner across all arms.
2. Retained recall values are within valid operational range [0.0, 1.0].
3. Existing learner metrics remain value-identical apart from the new retained_recall column and runtime_ms.
"""

import os
import pandas as pd
import pytest

from src.evaluation.integrated import run_integrated_evaluation


def test_integrated_run_writes_retained_recall_per_learner(tmp_path):
    """
    Verifies that running integrated evaluation writes a retained_recall column
    for every learner record in per_learner.csv.
    """
    out_dir = str(tmp_path / "eval_retention_check")
    res = run_integrated_evaluation(
        config_path="experiments/w5_final.yaml",
        output_dir=out_dir,
        override_learners=4,
        override_resamples=10,
    )

    csv_path = res["csv_path"]
    assert os.path.exists(csv_path), f"Output CSV not found at {csv_path}"

    df = pd.read_csv(csv_path)
    assert "retained_recall" in df.columns, f"'retained_recall' not found in columns: {df.columns.tolist()}"
    assert not df["retained_recall"].isna().any(), "Found NaN values in 'retained_recall'"
    assert len(df["retained_recall"]) == len(df)
    assert len(df) > 0


def test_retained_recall_range(tmp_path):
    """Verifies that all computed retained_recall values lie strictly in [0.0, 1.0]."""
    out_dir = str(tmp_path / "eval_range_check")
    res = run_integrated_evaluation(
        config_path="experiments/w5_final.yaml",
        output_dir=out_dir,
        override_learners=4,
        override_resamples=10,
    )

    df = pd.read_csv(res["csv_path"])
    recalls = df["retained_recall"].tolist()
    assert len(recalls) > 0
    for r in recalls:
        assert 0.0 <= r <= 1.0, f"Retained recall {r} out of bounds [0.0, 1.0]"


def test_existing_outputs_unchanged_apart_from_new_value(tmp_path):
    """
    Verifies that existing learner metrics (learner_id, seed, arm, theta_true, theta_hat,
    mastered_concepts, prereq_violations, budget_violations, no_plan_days) remain identical
    to baseline expectations.

    The W7 deadlock fix (docs/w7/preregistration_deadlock_fix.md) deliberately changes the
    replan arms' schedules, so for those arms only the learner and diagnostic columns are
    compared with the golden file, and the hard constraints (0 prerequisite and 0 budget
    violations) are checked directly. Every other arm must still match exactly.
    """
    replan_arms = {"adaptive_full", "ablation_no_diagnostic", "ablation_no_difficulty_step",
                   "ablation_no_review", "ablation_no_remediation"}
    out_dir = str(tmp_path / "eval_unchanged_check")
    res = run_integrated_evaluation(
        config_path="experiments/w5_final.yaml",
        output_dir=out_dir,
        override_learners=4,
        override_resamples=10,
    )

    df_new = pd.read_csv(res["csv_path"])
    golden_csv = "evaluation/results/w5/final/per_learner.csv"
    assert os.path.exists(golden_csv), f"Golden CSV missing: {golden_csv}"
    df_golden = pd.read_csv(golden_csv)

    # Filter golden to first 4 learners per arm for seed 42
    arms = df_new["arm"].unique()
    cols_to_check = [
        "learner_id",
        "arm",
        "theta_true",
        "theta_hat",
        "mastered_concepts",
        "prereq_violations",
        "budget_violations",
        "no_plan_days",
    ]

    for arm in arms:
        df_new_arm = df_new[(df_new["seed"] == 42000) | (df_new["arm"] == arm)]
        df_new_arm = df_new_arm[df_new_arm["arm"] == arm].head(4).reset_index(drop=True)
        df_gold_arm = df_golden[df_golden["arm"] == arm].head(4).reset_index(drop=True)

        if arm in replan_arms:
            assert (df_new_arm["prereq_violations"] == 0).all(), arm
            assert (df_new_arm["budget_violations"] == 0).all(), arm
        for col in (cols_to_check if arm not in replan_arms else ["learner_id", "arm", "theta_true", "theta_hat"]):
            val_new = list(df_new_arm[col])
            val_gold = list(df_gold_arm[col])
            assert val_new == val_gold, f"Mismatch in arm {arm}, column {col}: {val_new} != {val_gold}"
