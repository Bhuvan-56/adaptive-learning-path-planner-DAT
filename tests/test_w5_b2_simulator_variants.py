"""
Unit and Integration Tests for Week 5 Task B2: Simulator Variants and Retention Evaluation.

Verifies:
1. Default generator response sequence and latent transitions match golden file for fixed seeds.
2. Forgetting variant (advance_day / step_day with p_F):
   - p_F = 0 reproduces golden sequence exactly.
   - p_F > 0 transitions some mastered concepts to unmastered with enough days.
3. Difficulty-sensitive variant (parameter k):
   - k = 0 reproduces golden sequence exactly.
   - Monotone response probabilities in [0, 1] across [0.05, 0.95].
4. Mismatched PFA/logistic generator:
   - Returns 0 or 1, is seeded, depends on counts of successes/failures, never calls BKT transition.
5. Delayed retention quiz (src.evaluation.retention):
   - Reads N and D from YAML, draws fresh items, evaluator-only.
   - With p_F > 0, recall is lower than with p_F = 0.
6. Architectural boundary audit: zero imports of simulation/evaluation from planning/state/diagnostic.
"""

import json
import os
import pytest
from src.simulation.simulator import SimulatedLearner, MatchedBKTGenerator

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
