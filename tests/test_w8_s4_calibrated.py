"""W8 S4 (public-data extension): ASSISTments-calibrated learner generator (src/simulation/calibrated.py)."""
import numpy as np
import pytest

from src.simulation.calibrated import CalibratedBKTGenerator, load_parameter_pool


def test_pool_keeps_only_identifiable_fits():
    pool = load_parameter_pool()
    assert len(pool) > 10
    assert all(p["p_G"] < 0.5 and p["p_S"] < 0.5 for p in pool)


def test_draw_depends_only_on_learner_and_concept():
    a = CalibratedBKTGenerator(learner_seed=42)
    b = CalibratedBKTGenerator(learner_seed=42)
    # Different first-seen order must give the same parameters (arms see concepts in different orders).
    for c in ["A", "B", "C", "D"]:
        a.params_for(c)
    for c in ["D", "C", "B", "A"]:
        b.params_for(c)
    assert a.concept_params == b.concept_params


def test_different_learners_differ():
    draws = {tuple(sorted(CalibratedBKTGenerator(learner_seed=s).params_for("A").items())) for s in range(50)}
    assert len(draws) > 5


def test_response_rule_uses_concept_parameters():
    g = CalibratedBKTGenerator(learner_seed=7)
    p = g.params_for("A")
    rng = np.random.default_rng(0)
    n = 20000
    known = np.mean([g.generate_response("A", 0.5, True, rng)[0] for _ in range(n)])
    guess = np.mean([g.generate_response("A", 0.5, False, rng)[0] for _ in range(n)])
    assert known == pytest.approx(1 - p["p_S"], abs=0.015)
    assert guess == pytest.approx(p["p_G"], abs=0.015)
    # Mastered stays mastered (no forgetting in S4).
    assert all(g.generate_response("A", 0.5, True, rng)[1] for _ in range(100))
