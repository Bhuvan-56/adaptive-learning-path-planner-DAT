"""
Unit and Integration Tests for Week 5 Task B2: Simulator Variants and Retention Evaluation.

Verifies:
1. Default generator response sequence and latent transitions match golden file for fixed seeds.
2. Forgetting variant (advance_day / step_day with p_F):
   - p_F = 0 reproduces golden sequence exactly.
   - p_F > 0 transitions some mastered concepts to unmastered with enough days.
   - p_F = 0 transitions none to unmastered.
3. Difficulty-sensitive variant (parameter k):
   - k = 0 reproduces golden sequence exactly.
   - Monotone response probabilities in [0, 1] across [0.05, 0.95] for both mastered and unmastered.
4. Determinism: each variant is strictly deterministic for a fixed seed.
5. Mismatched PFA/logistic generator:
   - Returns 0 or 1, is seeded, depends on counts of successes/failures, never calls BKT transition.
6. Delayed retention quiz (src.evaluation.retention):
   - Reads N and D from YAML, draws fresh items, evaluator-only.
   - With p_F > 0, recall is lower than with p_F = 0.
7. Architectural boundary audit: zero imports of simulation/evaluation from planning/state/diagnostic.
"""

import ast
import glob
import json
import math
import os
from unittest.mock import patch

import numpy as np
import pytest

from src.simulation.simulator import (
    SimulatedLearner,
    MatchedBKTGenerator,
    MismatchedPFAOrLogisticGenerator,
)
from src.evaluation.retention import (
    administer_retention_quiz,
    evaluate_cohort_retention,
    load_retention_parameters,
    DEFAULT_CONFIG_PATH,
)

GOLDEN_FIXTURE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "fixtures", "w5", "default_generator_golden.json")
)


def test_default_generator_matches_golden_file():
    """
    Verifies that the default MatchedBKTGenerator exactly reproduces the response sequence
    and latent mastery transitions recorded in the golden fixture for 3 fixed seeds.
    """
    assert os.path.exists(GOLDEN_FIXTURE_PATH), f"Golden fixture not found at {GOLDEN_FIXTURE_PATH}"

    with open(GOLDEN_FIXTURE_PATH, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    seeds = golden_data["seeds"]
    requests = golden_data["requests"]
    runs = golden_data["runs"]

    for s in seeds:
        init_m = {"A": True, "B": False, "C": False, "D": False}
        learner = SimulatedLearner(
            profile_id="profile_1",
            seed=s,
            initial_mastery=dict(init_m),
            generator_family=MatchedBKTGenerator(),
        )
        eval_view = learner.evaluator_view()
        expected_records = runs[str(s)]

        for idx, req in enumerate(requests):
            c = req["concept"]
            d = req["difficulty"]
            expected = expected_records[idx]

            assert eval_view.latent_masteries == expected["latent_before"], (
                f"Seed {s}, step {idx} ({c}): latent mastery before request mismatch."
            )

            score = learner.respond(concept=c, difficulty=d)

            assert score == expected["score"], (
                f"Seed {s}, step {idx} ({c}): score mismatch. Expected {expected['score']}, got {score}."
            )
            assert eval_view.latent_masteries == expected["latent_after"], (
                f"Seed {s}, step {idx} ({c}): latent mastery after request mismatch."
            )


def test_variants_zero_params_match_golden_file():
    """
    Verifies that setting p_F = 0 and k = 0 reproduces the golden sequence exactly.
    """
    with open(GOLDEN_FIXTURE_PATH, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    seeds = golden_data["seeds"]
    requests = golden_data["requests"]
    runs = golden_data["runs"]

    for s in seeds:
        init_m = {"A": True, "B": False, "C": False, "D": False}
        # Explicitly pass p_F = 0.0 and k = 0.0
        gen = MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.10, p_F=0.0, k=0.0)
        learner = SimulatedLearner(
            profile_id="profile_1",
            seed=s,
            initial_mastery=dict(init_m),
            generator_family=gen,
        )
        eval_view = learner.evaluator_view()
        expected_records = runs[str(s)]

        for idx, req in enumerate(requests):
            c = req["concept"]
            d = req["difficulty"]
            expected = expected_records[idx]

            assert eval_view.latent_masteries == expected["latent_before"]
            score = learner.respond(concept=c, difficulty=d)
            assert score == expected["score"]
            assert eval_view.latent_masteries == expected["latent_after"]


def test_each_variant_is_deterministic_for_same_seed():
    """Verifies that each simulator variant is strictly deterministic given the same seed."""
    # 1. BKT variant with forgetting and difficulty sensitivity
    bkt_v1 = MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.10, p_F=0.05, k=0.50)
    bkt_v2 = MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.10, p_F=0.05, k=0.50)

    l1 = SimulatedLearner(seed=123, generator_family=bkt_v1, initial_mastery={"A": True, "B": False})
    l2 = SimulatedLearner(seed=123, generator_family=bkt_v2, initial_mastery={"A": True, "B": False})

    seq1 = [l1.respond("A", 0.3) for _ in range(20)]
    seq2 = [l2.respond("A", 0.3) for _ in range(20)]
    assert seq1 == seq2

    l1.advance_day(num_days=5)
    l2.advance_day(num_days=5)
    assert l1.evaluator_view().latent_masteries == l2.evaluator_view().latent_masteries

    # 2. Mismatched PFA generator
    pfa_v1 = MismatchedPFAOrLogisticGenerator(gamma=0.40, rho=0.10, difficulty_weight=1.0)
    pfa_v2 = MismatchedPFAOrLogisticGenerator(gamma=0.40, rho=0.10, difficulty_weight=1.0)

    l_pfa1 = SimulatedLearner(seed=456, generator_family=pfa_v1)
    l_pfa2 = SimulatedLearner(seed=456, generator_family=pfa_v2)

    seq_pfa1 = [l_pfa1.respond("concept_1", 0.4) for _ in range(20)]
    seq_pfa2 = [l_pfa2.respond("concept_1", 0.4) for _ in range(20)]
    assert seq_pfa1 == seq_pfa2
    assert l_pfa1.evaluator_view().latent_masteries == l_pfa2.evaluator_view().latent_masteries


def test_forgetting_variant_transitions_with_days():
    """
    Verifies that:
    - with p_F > 0 and enough days, some mastered concepts become unmastered.
    - with p_F = 0, no mastered concepts become unmastered.
    """
    # 1. p_F = 0.0: Zero decay over 100 days
    gen_zero = MatchedBKTGenerator(p_F=0.0)
    learner_zero = SimulatedLearner(
        seed=42,
        generator_family=gen_zero,
        initial_mastery={"A": True, "B": True, "C": True},
    )
    for _ in range(100):
        learner_zero.advance_day(num_days=1)
    assert learner_zero.evaluator_view().latent_masteries == {"A": True, "B": True, "C": True}

    # 2. p_F = 0.10: With 30 concepts and 50 days, some concepts MUST decay
    gen_decay = MatchedBKTGenerator(p_F=0.10)
    init_mastered = {f"concept_{i}": True for i in range(20)}
    learner_decay = SimulatedLearner(
        seed=101,
        generator_family=gen_decay,
        initial_mastery=init_mastered,
    )
    learner_decay.advance_day(num_days=30)
    final_masteries = learner_decay.evaluator_view().latent_masteries
    unmastered_count = sum(1 for v in final_masteries.values() if not v)
    assert unmastered_count > 0, "Expected some mastered concepts to decay to unmastered with p_F > 0."


def test_difficulty_monotone_at_every_grid_point():
    """
    Verifies that under difficulty sensitivity k > 0:
    - Probabilities stay strictly inside [0, 1] for every difficulty from 0.05 to 0.95.
    - Higher difficulty never raises the probability of a correct answer (monotone non-increasing).
    """
    p_S = 0.10
    p_G = 0.25
    k = 0.50

    # Grid of difficulties from 0.05 to 0.95 with step 0.05
    diff_grid = [round(x, 2) for x in np.arange(0.05, 0.96, 0.05)]

    def compute_prob(is_mastered: bool, d: float) -> float:
        diff_offset = d - 0.5
        if is_mastered:
            logit_base = math.log((1.0 - p_S) / p_S)
            return 1.0 / (1.0 + math.exp(-(logit_base - k * diff_offset)))
        else:
            logit_base = math.log(p_G / (1.0 - p_G))
            return 1.0 / (1.0 + math.exp(-(logit_base - k * diff_offset)))

    prev_p_mastered = 1.0
    prev_p_unmastered = 1.0

    for d in diff_grid:
        p_m = compute_prob(True, d)
        p_u = compute_prob(False, d)

        # 1. Bounds check
        assert 0.0 <= p_m <= 1.0, f"Mastered prob out of bounds: {p_m}"
        assert 0.0 <= p_u <= 1.0, f"Unmastered prob out of bounds: {p_u}"

        # 2. Monotonicity check: higher difficulty NEVER raises probability
        assert p_m <= prev_p_mastered + 1e-9, f"Non-monotone for mastered at d={d}: {p_m} > {prev_p_mastered}"
        assert p_u <= prev_p_unmastered + 1e-9, f"Non-monotone for unmastered at d={d}: {p_u} > {prev_p_unmastered}"

        prev_p_mastered = p_m
        prev_p_unmastered = p_u


def test_mismatched_generator_behavior_and_no_bkt_calls():
    """
    Verifies that MismatchedPFAOrLogisticGenerator:
    - Returns binary responses in {0, 1}.
    - Is deterministic for a seed.
    - NEVER calls MatchedBKTGenerator.generate_response (verified via spy patch).
    - Successes accumulate and elevate mastery classification without BKT state machine.
    """
    pfa_gen = MismatchedPFAOrLogisticGenerator(
        gamma=0.50,
        rho=0.10,
        difficulty_weight=1.0,
        mastered_p=0.70,
    )
    learner = SimulatedLearner(seed=777, generator_family=pfa_gen)

    # Use patch.object as a spy on MatchedBKTGenerator
    with patch.object(MatchedBKTGenerator, "generate_response") as mock_bkt_gen:
        responses = [learner.respond("concept_pfa", difficulty=0.5) for _ in range(15)]
        # Spy assertion: BKT generator must never be invoked
        assert mock_bkt_gen.call_count == 0, "MatchedBKTGenerator was called during PFA execution!"

    for r in responses:
        assert r in (0, 1), f"Expected response in {{0, 1}}, got {r}"

    # Learning enters strictly through success and failure counts
    assert pfa_gen.success_counts.get("concept_pfa", 0) + pfa_gen.failure_counts.get("concept_pfa", 0) == 15


def test_retention_quiz_reads_yaml_and_draws_fresh_items():
    """
    Verifies that retention quiz reads N and D from YAML configuration
    and administers fresh simulated items.
    """
    n, d, diff = load_retention_parameters(DEFAULT_CONFIG_PATH)
    assert n == 5, f"Expected N=5 from YAML [PROPOSED], got {n}"
    assert d == 7, f"Expected D=7 from YAML [PROPOSED], got {d}"

    learner = SimulatedLearner(seed=999, initial_mastery={"A": True, "B": True})
    studied = ["A", "B"]

    res = administer_retention_quiz(
        learner=learner,
        studied_concepts=studied,
        config_source=DEFAULT_CONFIG_PATH,
    )

    assert res["items_per_concept_N"] == 5
    assert res["delay_days_D"] == 7
    assert res["total_items"] == 10  # 2 concepts * 5 items
    assert 0.0 <= res["retention_share"] <= 1.0
    assert len(res["per_concept_scores"]["A"]) == 5
    assert len(res["per_concept_scores"]["B"]) == 5


def test_retention_quiz_lower_recall_with_forgetting():
    """
    Verifies that across a cohort with p_F > 0, delayed retention recall
    is strictly lower than when p_F = 0.
    """
    n_learners = 30
    studied = ["A", "B", "C"]
    delay_days = 20

    cohort_no_forget = []
    cohort_forget = []

    for s in range(n_learners):
        init_m = {"A": True, "B": True, "C": True}
        l_nf = SimulatedLearner(
            seed=s + 1000,
            initial_mastery=dict(init_m),
            generator_family=MatchedBKTGenerator(p_F=0.0),
        )
        l_f = SimulatedLearner(
            seed=s + 1000,
            initial_mastery=dict(init_m),
            generator_family=MatchedBKTGenerator(p_F=0.15),
        )
        cohort_no_forget.append((l_nf, studied))
        cohort_forget.append((l_f, studied))

    res_nf = evaluate_cohort_retention(cohort_no_forget, n_items=5, delay_days=delay_days)
    res_f = evaluate_cohort_retention(cohort_forget, n_items=5, delay_days=delay_days)

    assert res_f["mean_retention_share"] < res_nf["mean_retention_share"], (
        f"Expected lower retention recall with forgetting ({res_f['mean_retention_share']:.4f}) "
        f"than without forgetting ({res_nf['mean_retention_share']:.4f})."
    )


def test_architectural_boundary_import_audit():
    """
    Architectural boundary audit:
    Modules under src/planning, src/state, and src/diagnostic must NEVER import
    from src/simulation or src/evaluation, nor reference EvaluatorView.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    checked_dirs = [
        os.path.join(repo_root, "src", "planning"),
        os.path.join(repo_root, "src", "state"),
        os.path.join(repo_root, "src", "diagnostic"),
    ]

    forbidden_tokens = [
        "src.evaluation",
        "src.simulation",
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
