"""W7 B1: saved bad cases for the greedy scheduler reproduce their recorded scores."""
import json
import os
import random

import pytest

from src.planning.benchmark import generate_benchmark_instance, load_benchmark_config
from src.planning.greedy import run_greedy_scheduler
from src.planning.oracle import run_exhaustive_oracle

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "w7", "bad_cases.json")


def _load_cases():
    with open(FIXTURE, "r", encoding="utf-8") as f:
        return json.load(f)["cases"]


CASES = _load_cases()


def test_fixture_has_both_cases():
    ids = {c["id"] for c in CASES}
    assert ids == {"counterexample_12_18", "benchmark_seed47_instance215"}
    for c in CASES:
        for key in ("id", "budget", "items", "greedy_score", "oracle_score", "source"):
            assert key in c


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_bad_case_scores(case):
    assert run_greedy_scheduler(case["items"], case["budget"]) == case["greedy_score"]
    assert run_exhaustive_oracle(case["items"], case["budget"]) == case["oracle_score"]
    assert case["greedy_score"] < case["oracle_score"]


def test_instance_215_matches_benchmark_generator():
    case = next(c for c in CASES if c["id"] == "benchmark_seed47_instance215")
    cfg = load_benchmark_config()
    counter = 1
    regenerated = None
    for seed in cfg["seeds"]:
        rng = random.Random(seed)
        for _ in range(cfg["instances_per_seed"]):
            inst = generate_benchmark_instance(counter, rng, cfg["generator_params"])
            if counter == 215:
                assert seed == 47
                regenerated = inst
            counter += 1
    assert regenerated is not None
    assert regenerated["budget"] == case["budget"]
    assert regenerated["items"] == case["items"]
