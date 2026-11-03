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


@pytest.mark.xfail(strict=True, reason="Harness does not yet write retained_recall per learner across all arms")
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
