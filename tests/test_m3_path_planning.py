import os
import pytest
from src.curriculum.graph import load_graph
from src.state.learner_state import ConceptState
from src.planning.static_baseline import generate_static_plan
from src.planning.feasibility import FeasibilityStatus, InfeasibilityReason
from src.planning.greedy import run_greedy_scheduler
from src.planning.oracle import run_exhaustive_oracle, run_exact_dp_oracle
from src.planning.benchmark import run_benchmark

FIXTURE_GRAPH = os.path.join(os.path.dirname(__file__), "fixtures", "graphs", "valid_branching.json")


@pytest.mark.parametrize("budget", [5, 10, 15, 30])
def test_tc_3_1_budget_never_exceeds_configured_budget(budget):
    """TC-3.1: Daily time-budget constraint enforcement."""
    g = load_graph(FIXTURE_GRAPH)
    learner_states = {n: ConceptState.cold_start() for n in g.nodes}

    plan = generate_static_plan(
        g=g,
        learner_states=learner_states,
        budget=budget,
        deadline_days=10,
        target_node="D"
    )

    if budget == 5:
        # 10-minute blocks (C, D) exceed budget 5
        assert plan["status"] == FeasibilityStatus.INFEASIBLE_PROVED
        explanation = plan["feasibility_explanation"]
        assert explanation["reason_code"] == InfeasibilityReason.BLOCK_EXCEEDS_DAILY_BUDGET
    else:
        assert plan["status"] in [FeasibilityStatus.FEASIBLE, FeasibilityStatus.HEURISTIC_NO_PLAN]
        for day in plan["days"]:
            assert day["minutes_used"] <= budget
            assert day["minutes_remaining"] >= 0


def test_infeasible_block_10min_under_5min_cap():
    """Infeasibility check for block duration > daily budget."""
    g = load_graph(FIXTURE_GRAPH)
    learner_states = {n: ConceptState.cold_start() for n in g.nodes}

    plan = generate_static_plan(
        g=g,
        learner_states=learner_states,
        budget=5,
        deadline_days=100,  # Even with 100 days, 10-minute block cannot fit on 5-minute daily budget
        target_node="D"
    )

    assert plan["status"] == FeasibilityStatus.INFEASIBLE_PROVED
    explanation = plan["feasibility_explanation"]
    assert explanation["reason_code"] == InfeasibilityReason.BLOCK_EXCEEDS_DAILY_BUDGET
    assert "offending_nodes" in explanation
    assert "raise daily budget to at least 10 minutes" in explanation["minimum_fix"]


def test_tc_3_2_counterexample():
    """TC-3.2: Counterexample demonstrating greedy scheduler score-per-minute suboptimality."""
    budget = 10
    items = [
        {"node_id": "item_1", "duration": 6, "score": 12},
        {"node_id": "item_2", "duration": 5, "score": 9},
        {"node_id": "item_3", "duration": 5, "score": 9},
    ]

    greedy_score = run_greedy_scheduler(items, budget)
    oracle_score = run_exhaustive_oracle(items, budget)

    assert greedy_score == 12
    assert oracle_score == 18
    assert run_exact_dp_oracle(items, budget) == 18

    ratio = greedy_score / oracle_score
    assert ratio == pytest.approx(2.0 / 3.0)


def test_tc_3_2_benchmark_runs_and_reports():
    """TC-3.2: Optimality benchmark runner executes 250 instances and writes CSV/MD reports."""
    summary_info = run_benchmark(output_dir="evaluation/results")

    assert os.path.exists(summary_info["csv_path"])
    assert os.path.exists(summary_info["summary_path"])
    assert summary_info["total_count"] == 250
    assert 0.0 < summary_info["mean_ratio"] <= 1.0


def test_greedy_and_oracle_share_constraints():
    """Verifies greedy and exact oracle enforce identical prerequisite constraints."""
    budget = 10
    items = [
        {"node_id": "A", "duration": 4, "score": 5, "prerequisites": []},
        {"node_id": "B", "duration": 5, "score": 20, "prerequisites": ["A"]},
    ]

    greedy_score = run_greedy_scheduler(items, budget)
    oracle_score = run_exhaustive_oracle(items, budget)

    assert greedy_score == 25
    assert oracle_score == 25


def test_oracle_hard_cap_exceeded():
    """Verifies that the exhaustive oracle raises ValueError when items > 20 hard cap."""
    budget = 10
    items = [{"node_id": f"item_{i}", "duration": 1, "score": 1} for i in range(21)]

    with pytest.raises(ValueError, match="Oracle hard cap exceeded"):
        run_exhaustive_oracle(items, budget)

    with pytest.raises(ValueError, match="Oracle hard cap exceeded"):
        run_exact_dp_oracle(items, budget)

