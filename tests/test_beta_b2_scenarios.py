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
import pytest

from src.evaluation.integrated import run_integrated_evaluation
from src.simulation.simulator import SimulatedLearner, MatchedBKTGenerator


@pytest.mark.xfail(strict=True, reason="Scenario selector not yet integrated into run_integrated_evaluation")
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
