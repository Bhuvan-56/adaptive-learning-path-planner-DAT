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


def test_tc_3_2_benchmark_runs_and_reports(tmp_path):
    """TC-3.2: Optimality benchmark runner executes 250 instances and writes CSV/MD reports."""
    summary_info = run_benchmark(output_dir=str(tmp_path))

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


def test_defect_7_nan_duration():
    """Defect 7 sub-case 1: validate_graph must reject NaN duration."""
    import networkx as nx
    from src.curriculum.graph import validate_graph
    from src.curriculum.errors import GraphErrorCode
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=float("nan"), base_difficulty=0.5)
    g.graph["raw_edges"] = []
    errors = validate_graph(g)
    assert GraphErrorCode.NON_FINITE_VALUE in errors


def test_defect_7_nan_difficulty():
    """Defect 7 sub-case 2: validate_graph must reject NaN difficulty."""
    import networkx as nx
    from src.curriculum.graph import validate_graph
    from src.curriculum.errors import GraphErrorCode
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=10, base_difficulty=float("nan"))
    g.graph["raw_edges"] = []
    errors = validate_graph(g)
    assert GraphErrorCode.NON_FINITE_VALUE in errors


def test_defect_7_cycle_produces_no_plan():
    """Defect 7 sub-case 3: cyclic graph must be rejected as InvalidInput and never produce fallback plan."""
    import networkx as nx
    from src.planning.service import plan_request
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=10, base_difficulty=0.5)
    g.add_node("B", baseline_duration=10, base_difficulty=0.5)
    g.add_edge("A", "B", importance=1.0)
    g.add_edge("B", "A", importance=1.0)
    g.graph["raw_edges"] = [("A", "B", 1.0), ("B", "A", 1.0)]
    result = plan_request(g, {}, budget=20, deadline_days=5, targets="B")
    assert not result.is_valid
    assert "CYCLE_DETECTED" in result.error_codes


def test_defect_7_deadline_zero_no_zero_division():
    """Defect 7 sub-case 4: deadline_days = 0 must return InvalidInput without raising ZeroDivisionError."""
    import networkx as nx
    from src.planning.service import plan_request
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=10, base_difficulty=0.5)
    g.graph["raw_edges"] = []
    result = plan_request(g, {}, budget=10, deadline_days=0, targets="A")
    assert not result.is_valid
    assert "INVALID_DEADLINE" in result.error_codes


def test_static_baseline_sequential_budget_12_then_6():
    """Defect 8: sequential selections under budget 12 must record 12 then 6 in trace."""
    import networkx as nx
    from src.state.learner_state import ConceptState
    from src.planning.static_baseline import generate_static_plan

    g = nx.DiGraph()
    g.add_node("A", baseline_duration=6)
    g.add_node("B", baseline_duration=6)
    g.add_edge("A", "B")
    learner_states = {"A": ConceptState.cold_start(), "B": ConceptState.cold_start()}

    plan = generate_static_plan(g, learner_states, budget=12, deadline_days=1, target_node="B")
    selected_entries = [e for e in plan["trace"] if e["decision"] == "SELECTED"]
    assert len(selected_entries) == 2
    assert selected_entries[0]["node_id"] == "A"
    assert selected_entries[0]["constraints"]["remaining_budget"] == 12
    assert selected_entries[1]["node_id"] == "B"
    assert selected_entries[1]["constraints"]["remaining_budget"] == 6



