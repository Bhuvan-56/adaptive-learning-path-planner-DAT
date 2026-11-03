"""
Tests for Beta Task B2: Simulator Scenario Selection and Retention Evaluation.

Verifies:
1. Scenario S1 produces learners with forgetting enabled (p_F = 0.05).
2. Scenario selector selects correct generator parameters across S0, S1, S2.
3. Unknown scenario names raise a ValueError.
4. S0 equality: S0 produces identical outputs on a small cohort to default unconfigured scenario.
"""

import os
from unittest.mock import patch
import pandas as pd
import pytest
import yaml

from src.evaluation.integrated import (
    run_integrated_evaluation,
    make_learner_generator,
)
from src.simulation.simulator import SimulatedLearner, MatchedBKTGenerator


def test_scenario_s1_produces_learners_with_forgetting_enabled(tmp_path):
    """
    Verifies that running evaluation under scenario S1 passes a generator_family
    with forgetting p_F == 0.05 to all SimulatedLearner instances.
    """
    captured_learners = []
    orig_init = SimulatedLearner.__init__

    def spy_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        captured_learners.append(self)

    with patch.object(SimulatedLearner, "__init__", spy_init):
        res = run_integrated_evaluation(
            config_path="experiments/beta_s1.yaml",
            output_dir=str(tmp_path / "out_s1"),
            override_learners=2,
            override_resamples=10,
        )

    assert len(captured_learners) > 0, "No SimulatedLearner instances were created"
    for l in captured_learners:
        gen = getattr(l, "generator_family", None)
        assert gen is not None, "SimulatedLearner was not initialized with a generator_family"
        p_f = getattr(gen, "p_F", 0.0)
        assert p_f == 0.05, f"Expected forgetting p_F == 0.05, got {p_f}"


def test_scenario_selector_generator_parameters():
    """
    Verifies that make_learner_generator constructs appropriate MatchedBKTGenerator
    instances and retention evaluation flags for S0, S1, and S2.
    """
    gen_s0, ret_s0 = make_learner_generator("S0")
    assert isinstance(gen_s0, MatchedBKTGenerator)
    assert gen_s0.p_F == 0.0
    assert gen_s0.k == 0.0
    assert not ret_s0

    gen_s1, ret_s1 = make_learner_generator("S1")
    assert isinstance(gen_s1, MatchedBKTGenerator)
    assert gen_s1.p_F == 0.05
    assert gen_s1.k == 0.0
    assert ret_s1

    gen_s2, ret_s2 = make_learner_generator("S2")
    assert isinstance(gen_s2, MatchedBKTGenerator)
    assert gen_s2.p_F == 0.0
    assert gen_s2.k == 0.50
    assert not ret_s2


def test_unknown_scenario_name_raises_error(tmp_path):
    """Verifies that an unknown scenario name raises a ValueError immediately."""
    with pytest.raises(ValueError, match="Unknown scenario 'UNKNOWN'"):
        make_learner_generator("UNKNOWN")

    # Also test via run_integrated_evaluation with custom config
    cfg_path = str(tmp_path / "invalid_scenario.yaml")
    with open("experiments/w5_final.yaml", "r", encoding="utf-8") as f:
        raw_text = f.read()
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write('scenario: "UNKNOWN"\n' + raw_text)

    with pytest.raises(ValueError, match="Unknown scenario 'UNKNOWN'"):
        run_integrated_evaluation(
            config_path=cfg_path,
            output_dir=str(tmp_path / "out_invalid"),
            override_learners=2,
            override_resamples=10,
        )


def test_s0_equality_on_small_cohort(tmp_path):
    """
    Verifies that explicit scenario 'S0' produces outputs identical to the default
    unconfigured run on a small cohort across all learner metrics (excluding runtime_ms).
    """
    out_default = str(tmp_path / "out_default")
    out_s0 = str(tmp_path / "out_s0")

    # 1. Run with default config (experiments/w5_final.yaml without explicit scenario key)
    res_default = run_integrated_evaluation(
        config_path="experiments/w5_final.yaml",
        output_dir=out_default,
        override_learners=4,
        override_resamples=20,
    )

    # 2. Run with explicit scenario 'S0' config
    cfg_s0_path = str(tmp_path / "cfg_s0.yaml")
    with open("experiments/w5_final.yaml", "r", encoding="utf-8") as f:
        raw_text = f.read()
    with open(cfg_s0_path, "w", encoding="utf-8") as f:
        f.write('scenario: "S0"\n' + raw_text)

    res_s0 = run_integrated_evaluation(
        config_path=cfg_s0_path,
        output_dir=out_s0,
        override_learners=4,
        override_resamples=20,
    )

    df_default = pd.read_csv(res_default["csv_path"])
    df_s0 = pd.read_csv(res_s0["csv_path"])

    assert len(df_default) == len(df_s0)
    cols = [c for c in df_default.columns if c != "runtime_ms"]
    for c in cols:
        assert list(df_default[c]) == list(df_s0[c]), f"Column {c} differs between default and S0"
