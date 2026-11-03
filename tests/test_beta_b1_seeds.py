"""
Unit and Integration Tests for Beta Milestone Task B1: Multi-Seed Integrated Evaluation.

Tests required:
1. Former xfail: A config with two seeds yields two result sets with different cohorts.
2. Seed 42 in a multi-seed run equals the single-seed run on a small cohort.
3. The single-seed path is unchanged.
"""

import os
import yaml
import pytest
import pandas as pd

from src.evaluation.integrated import (
    run_integrated_evaluation,
    DEFAULT_INTEGRATED_CONFIG,
    load_integrated_config,
)


@pytest.mark.xfail(strict=True, reason="Harness uses only first seed; config with two seeds yields only one result set")
def test_two_seeds_yields_two_result_sets_with_different_cohorts(tmp_path):
    """
    Verifies that a configuration specifying multiple seeds yields distinct result sets
    for each seed, each having its own cohort of synthetic learners.
    In the unfixed code, line 172 selects config['seeds'][0], ignoring subsequent seeds.
    """
    cfg = load_integrated_config(DEFAULT_INTEGRATED_CONFIG)
    cfg["seeds"] = [42, 101]
    cfg["evaluation_scale"]["num_synthetic_learners"] = 3
    cfg["evaluation_scale"]["num_seed_runs"] = 2

    cfg_path = tmp_path / "two_seeds.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    out_dir = str(tmp_path / "multi_seed_out")
    res = run_integrated_evaluation(
        config_path=str(cfg_path),
        output_dir=out_dir,
        override_learners=3,
        override_resamples=10,
    )

    assert "seed_results" in res, "Multi-seed run did not return seed_results"
    seed_results = res["seed_results"]
    assert len(seed_results) == 2, f"Expected 2 result sets for 2 seeds, got {len(seed_results)}"
    assert 42 in seed_results and 101 in seed_results, "Missing seed 42 or 101 in seed_results"

    # Cohorts must be different between seed 42 and seed 101
    cohort_42 = seed_results[42]["cohort"]
    cohort_101 = seed_results[101]["cohort"]
    thetas_42 = [round(l.theta_true, 4) for l in cohort_42]
    thetas_101 = [round(l.theta_true, 4) for l in cohort_101]
    assert thetas_42 != thetas_101, "Cohorts across seed 42 and seed 101 must differ"
