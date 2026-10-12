"""
Tests for transparent learner simulator (Task 1: w3/b4-simulator-cat).

Verifies:
1. Deterministic repeatability (same seed yields identical response sequences).
2. Strict architectural boundary (zero imports of EvaluatorView in src/planning or src/state).
3. Slip and guess rates match configured values within statistical tolerance over 10,000 draws.
4. Profile loading (profile_1 budget 5, profile_2 budget 10) and budget_override behavior.
5. EvaluatorView isolation and transition dynamics.
6. Mismatched generator family documented interface.
"""

import glob
import os
import pytest

from src.simulation.simulator import (
    EvaluatorView,
    MatchedBKTGenerator,
    MismatchedPFAOrLogisticGenerator,
    SimulatedLearner,
)


def test_simulator_same_seed_gives_identical_response_sequences():
    """Verifies that identical seeds produce identical response sequences across concepts."""
    learner1 = SimulatedLearner(profile_id="profile_1", seed=42)
    learner2 = SimulatedLearner(profile_id="profile_1", seed=42)

    responses_1 = [learner1.respond("concept_x", 0.4) for _ in range(100)]
    responses_2 = [learner2.respond("concept_x", 0.4) for _ in range(100)]

    assert responses_1 == responses_2

    # Different seed should yield a different sequence
    learner3 = SimulatedLearner(profile_id="profile_1", seed=999)
    responses_3 = [learner3.respond("concept_x", 0.4) for _ in range(100)]
    assert responses_1 != responses_3


def test_planner_and_state_modules_contain_no_import_of_evaluator_view():
    """
    Grep-style test enforcing architectural isolation:
    Modules under src/planning and src/state must NEVER import or reference EvaluatorView.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    checked_dirs = [
        os.path.join(repo_root, "src", "planning"),
        os.path.join(repo_root, "src", "state"),
    ]

    forbidden_patterns = [
        "EvaluatorView",
        "evaluator_view",
        "from src.simulation",
        "import EvaluatorView",
    ]

    violations = []
    for cdir in checked_dirs:
        for py_file in glob.glob(os.path.join(cdir, "**", "*.py"), recursive=True):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                for pattern in forbidden_patterns:
                    if pattern in content:
                        rel_path = os.path.relpath(py_file, repo_root)
                        violations.append(f"{rel_path} references '{pattern}'")

    assert len(violations) == 0, f"Architectural boundary violated: {violations}"


def test_simulator_slip_and_guess_rates_within_statistical_tolerance_10000_draws():
    """
    Verifies that simulated responses follow stated slip and guess rates
    within statistical tolerance over 10,000 draws.

    Parameters:
      p_S = 0.10 (slip rate) -> SE = sqrt(0.1 * 0.9 / 10000) = 0.003
      p_G = 0.25 (guess rate)-> SE = sqrt(0.25 * 0.75 / 10000) ≈ 0.00433

    Tolerance:
      Slip: +/- 0.015 (5 standard errors)
      Guess: +/- 0.018 (4.15 standard errors)
    """
    n_draws = 10000

    # 1. Slip Rate Test on Mastered State (p_T = 0.0 preserves mastery)
    generator_slip = MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.0)
    learner_mastered = SimulatedLearner(
        profile_id="profile_1",
        generator_family=generator_slip,
        seed=101,
        initial_mastery={"concept_mastered": True},
    )

    slip_responses = [learner_mastered.respond("concept_mastered") for _ in range(n_draws)]
    slips = sum(1 for r in slip_responses if r == 0)
    empirical_slip_rate = slips / n_draws

    assert abs(empirical_slip_rate - 0.10) <= 0.015, (
        f"Empirical slip rate {empirical_slip_rate:.4f} outside tolerance of target 0.10"
    )

    # 2. Guess Rate Test on Unmastered State (p_T = 0.0 preserves unmastered state)
    generator_guess = MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.0)
    learner_unmastered = SimulatedLearner(
        profile_id="profile_1",
        generator_family=generator_guess,
        seed=202,
        initial_mastery={"concept_unmastered": False},
    )

    guess_responses = [learner_unmastered.respond("concept_unmastered") for _ in range(n_draws)]
    guesses = sum(1 for r in guess_responses if r == 1)
    empirical_guess_rate = guesses / n_draws

    assert abs(empirical_guess_rate - 0.25) <= 0.018, (
        f"Empirical guess rate {empirical_guess_rate:.4f} outside tolerance of target 0.25"
    )


def test_simulator_profiles_and_budget_override():
    """
    Verifies that:
    - profile_1 daily budget is 5 minutes.
    - profile_2 daily budget is 10 minutes.
    - budget_override sets the same budget across profiles for demo requirements.
    """
    p1 = SimulatedLearner(profile_id="profile_1")
    p2 = SimulatedLearner(profile_id="profile_2")

    assert p1.get_budget() == 5
    assert p2.get_budget() == 10

    # Demo requires running two profiles at the SAME budget via budget_override
    p1_override = SimulatedLearner(profile_id="profile_1", budget_override=15)
    p2_override = SimulatedLearner(profile_id="profile_2", budget_override=15)

    assert p1_override.get_budget() == 15
    assert p2_override.get_budget() == 15


def test_evaluator_view_and_transition_dynamics():
    """Verifies that EvaluatorView inspects latent state and transition probability p_T works."""
    # When p_T = 1.0, an unmastered concept MUST transition to mastered upon 1 attempt
    gen = MatchedBKTGenerator(p_S=0.0, p_G=0.0, p_T=1.0)
    learner = SimulatedLearner(
        profile_id="profile_1",
        generator_family=gen,
        initial_mastery={"topic_1": False},
    )

    eval_view = learner.evaluator_view()
    assert eval_view.is_mastered("topic_1") is False

    # Attempt topic_1
    learner.respond("topic_1")

    # Latent state must now be mastered
    assert eval_view.is_mastered("topic_1") is True
    assert eval_view.latent_masteries["topic_1"] is True

    summary = eval_view.get_latent_state_summary()
    assert summary["masteries"]["topic_1"] is True
    assert summary["generator_family"] == "MatchedBKTGenerator"


def test_mismatched_generator_interface_raises_not_implemented():
    """Verifies the documented empty interface for the mismatched family (scheduled W5)."""
    mismatched = MismatchedPFAOrLogisticGenerator()
    params = mismatched.get_parameters()
    assert params["status"] == "NOT_IMPLEMENTED_SCHEDULED_W5"

    learner = SimulatedLearner(generator_family=mismatched)
    with pytest.raises(NotImplementedError, match="scheduled for Week 5"):
        learner.respond("any_concept")
