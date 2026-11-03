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


def test_two_seeds_yields_two_result_sets_with_different_cohorts(tmp_path):
    """
    Verifies that a configuration specifying multiple seeds yields distinct result sets
    for each seed, each having its own cohort of synthetic learners.
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


def test_seed_42_in_multiseed_run_equals_single_seed_run(tmp_path):
    """
    Verifies that seed 42 in a multi-seed run equals the single-seed run on a small cohort.
    Every learner metric except runtime_ms must match.
    """
    cfg = load_integrated_config(DEFAULT_INTEGRATED_CONFIG)
    cfg["evaluation_scale"]["num_synthetic_learners"] = 3

    # 1. Single-seed run with [42]
    cfg["seeds"] = [42]
    cfg_single_path = tmp_path / "single_cfg.yaml"
    with open(cfg_single_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)
    res_single = run_integrated_evaluation(
        config_path=str(cfg_single_path),
        output_dir=str(tmp_path / "out_single"),
        override_learners=3,
        override_resamples=10,
    )
    df_single = pd.read_csv(res_single["csv_path"])

    # 2. Multi-seed run with [42, 101]
    cfg["seeds"] = [42, 101]
    cfg_multi_path = tmp_path / "multi_cfg.yaml"
    with open(cfg_multi_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)
    res_multi = run_integrated_evaluation(
        config_path=str(cfg_multi_path),
        output_dir=str(tmp_path / "out_multi"),
        override_learners=3,
        override_resamples=10,
    )
    df_multi_42 = pd.read_csv(res_multi["seed_results"][42]["csv_path"])

    # Compare every learner metric except runtime_ms
    metrics = [
        "learner_id",
        "seed",
        "arm",
        "theta_true",
        "theta_hat",
        "mastered_concepts",
        "prereq_violations",
        "budget_violations",
        "no_plan_days",
    ]
    pd.testing.assert_frame_equal(df_single[metrics], df_multi_42[metrics])


def test_single_seed_path_is_unchanged(tmp_path):
    """
    Verifies that the single-seed path is unchanged: writes artifacts directly
    to output_dir (without subdirectories) and returns expected keys.
    """
    cfg = load_integrated_config(DEFAULT_INTEGRATED_CONFIG)
    cfg["seeds"] = [42]
    cfg["evaluation_scale"]["num_synthetic_learners"] = 2
    cfg_path = tmp_path / "single_cfg.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    out_dir = str(tmp_path / "single_unchanged")
    res = run_integrated_evaluation(
        config_path=str(cfg_path),
        output_dir=out_dir,
        override_learners=2,
        override_resamples=10,
    )

    assert os.path.exists(os.path.join(out_dir, "per_learner.csv"))
    assert os.path.exists(os.path.join(out_dir, "summary.md"))
    assert os.path.exists(os.path.join(out_dir, "manifest.json"))
    assert not os.path.exists(os.path.join(out_dir, "seed_42"))

    assert res["csv_path"] == os.path.join(out_dir, "per_learner.csv")
    assert res["md_path"] == os.path.join(out_dir, "summary.md")
    assert res["manifest_path"] == os.path.join(out_dir, "manifest.json")
    assert "arm_results" in res
