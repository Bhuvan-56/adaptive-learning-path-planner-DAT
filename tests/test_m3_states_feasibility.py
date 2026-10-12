import networkx as nx
import pytest

from src.state.learner_state import ConceptState
from src.planning.static_baseline import generate_static_plan
from src.planning.feasibility import check_feasibility, FeasibilityStatus, InfeasibilityReason


@pytest.mark.xfail(strict=True, reason="Defect 1: scheduled-only prerequisite traced as ALREADY_MASTERED on day 2 instead of ALREADY_SCHEDULED")
def test_defect_1_day_2_uncertain_node_never_traced_already_mastered():
    """Defect 1: on day 2, a merely scheduled node with Uncertain state must not be traced ALREADY_MASTERED."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    g.add_node("B", baseline_duration=5)
    g.add_edge("A", "B")

    states = {"A": ConceptState.cold_start(), "B": ConceptState.cold_start()}
    plan = generate_static_plan(g, states, budget=5, deadline_days=2, target_node="B")

    # On day 2, node A was only scheduled on day 1 (learner state is still Uncertain)
    trace_day2_a = [e for e in plan["trace"] if e["node_id"] == "A" and e["day"] == 2][0]

    # Must NOT be ALREADY_MASTERED
    assert trace_day2_a["reason_code"] != "ALREADY_MASTERED"
    assert trace_day2_a["reason_code"] == "ALREADY_SCHEDULED"
    assert trace_day2_a["concept_state"]["class"] == "Uncertain"


@pytest.mark.xfail(strict=True, reason="Defect 4: nested feasibility explanation contradicts HEURISTIC_NO_PLAN with FEASIBLE")
def test_defect_4_three_six_minute_tasks_heuristic_no_plan_consistent_nested_status():
    """Defect 4: three 6-minute tasks on budget 10 across 2 days must return HEURISTIC_NO_PLAN with consistent nested status."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=6)
    g.add_node("B", baseline_duration=6)
    g.add_node("C", baseline_duration=6)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    # 1. check_feasibility must return CAPACITY_CHECK_PASSED, not public FEASIBLE
    status, info = check_feasibility(g, {"A", "B", "C"}, budget=10, deadline_days=2)
    assert status == "CAPACITY_CHECK_PASSED"
    assert info["status"] == "CAPACITY_CHECK_PASSED"

    # 2. Planner returns HEURISTIC_NO_PLAN and nested explanation agrees
    states = {n: ConceptState.cold_start() for n in g.nodes}
    plan = generate_static_plan(g, states, budget=10, deadline_days=2, target_node="C")

    assert plan["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN
    assert plan["feasibility_explanation"]["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN
    assert plan["feasibility_explanation"]["reason_code"] == InfeasibilityReason.SCHEDULING_CONSTRAINTS_UNMET
