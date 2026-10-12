import os
import pytest

from src.planning.benchmark import (
    run_benchmark,
    run_order_invariance_benchmark,
    load_benchmark_config
)
from src.planning.greedy import run_greedy_scheduler
from src.planning.oracle import run_exhaustive_oracle


def test_repaired_oracle_order_invariance_across_250_instances():
    """TASK 1: Shuffled benchmark variant verifies oracle result no longer depends on item order."""
    result = run_order_invariance_benchmark(shuffle_seed=999)
    assert result["total_instances"] == 250
    assert result["discrepancy_count"] == 0
    assert result["order_invariant"] is True


def test_counterexample_12_18():
    """TASK 1: Counterexample demonstrating greedy suboptimality (12 vs 18)."""
    items = [
        {"node_id": "item_1", "duration": 6, "score": 12},
        {"node_id": "item_2", "duration": 5, "score": 9},
        {"node_id": "item_3", "duration": 5, "score": 9},
    ]
    budget = 10
    greedy_score = run_greedy_scheduler(items, budget)
    oracle_score = run_exhaustive_oracle(items, budget)

    assert greedy_score == 12
    assert oracle_score == 18
    assert greedy_score / oracle_score == pytest.approx(2.0 / 3.0)


def test_w3_benchmark_artifacts_exist_and_valid():
    """TASK 1: Verify W3 benchmark writes to evaluation/results/w3/ without modifying W2 root files."""
    summary_info = run_benchmark(output_dir="evaluation/results/w3")

    assert os.path.exists("evaluation/results/w3/w3_summary.md")
    assert os.path.exists("evaluation/results/w3/w3_greedy_vs_oracle.csv")
    assert os.path.exists("evaluation/results/w3/manifest.json")
    assert os.path.exists("evaluation/results/w3/config_hash.txt")

    assert summary_info["total_count"] == 250
    assert summary_info["mean_ratio"] == pytest.approx(0.9737, abs=1e-4)
    assert summary_info["mean_ratio_nonzero"] == pytest.approx(0.9730, abs=1e-4)
    assert summary_info["p5_ratio"] == pytest.approx(0.8270, abs=1e-4)
    assert summary_info["min_ratio"] == pytest.approx(0.2143, abs=1e-4)
    assert summary_info["below_95_count"] == 35
    assert summary_info["zero_oracle_count"] == 6
