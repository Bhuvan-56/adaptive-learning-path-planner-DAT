import networkx as nx
import pytest

from src.state.learner_state import ConceptState
from src.planning.static_baseline import generate_static_plan, generate_static_baseline
from src.planning.feasibility import check_feasibility, FeasibilityStatus, InfeasibilityReason
from src.planning.admissibility import is_admissible
from src.trace.schema import ReasonCode


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

    # Must NOT be ALREADY_MASTERED; must be ALREADY_SCHEDULED with actual Uncertain state
    assert trace_day2_a["reason_code"] != "ALREADY_MASTERED"
    assert trace_day2_a["reason_code"] == ReasonCode.ALREADY_SCHEDULED.value
    assert trace_day2_a["concept_state"]["class"] == "Uncertain"


def test_defect_4_three_six_minute_tasks_heuristic_no_plan_consistent_nested_status():
    """Defect 4 & Defect 9: three 6-minute tasks on budget 10 across 2 days return HEURISTIC_NO_PLAN with consistent nested status and SCHEDULING_CONSTRAINTS_UNMET."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=6)
    g.add_node("B", baseline_duration=6)
    g.add_node("C", baseline_duration=6)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    # 1. check_feasibility must return CAPACITY_CHECK_PASSED, not public FEASIBLE
    status, info = check_feasibility(g, {"A", "B", "C"}, budget=10, deadline_days=2)
    assert status == FeasibilityStatus.CAPACITY_CHECK_PASSED
    assert info["status"] == FeasibilityStatus.CAPACITY_CHECK_PASSED

    # 2. Planner returns HEURISTIC_NO_PLAN and nested explanation agrees with SCHEDULING_CONSTRAINTS_UNMET
    states = {n: ConceptState.cold_start() for n in g.nodes}
    plan = generate_static_plan(g, states, budget=10, deadline_days=2, target_node="C")

    assert plan["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN
    assert plan["feasibility_explanation"]["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN
    assert plan["feasibility_explanation"]["reason_code"] == InfeasibilityReason.SCHEDULING_CONSTRAINTS_UNMET

    # Also verify BUDGET_EXCEEDED is emitted in trace
    budget_exceeded_entries = [e for e in plan["trace"] if e["reason_code"] == ReasonCode.BUDGET_EXCEEDED.value]
    assert len(budget_exceeded_entries) > 0


def test_scheduled_only_prerequisite_does_not_unlock_dependent_unconditionally():
    """Step 5: scheduled-only prerequisite does not unlock a dependent unconditionally."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    g.add_node("B", baseline_duration=5)
    g.add_edge("A", "B")

    act_b = {"node_id": "B", "duration": 5, "prerequisites": ["A"]}

    # In is_admissible: planned_set only unlocks if allow_conditional=True
    assert not is_admissible(act_b, selected_set=set(), mastered_set=set(), remaining_budget=5, g=g, planned_set={"A"}, allow_conditional=False)
    assert is_admissible(act_b, selected_set=set(), mastered_set=set(), remaining_budget=5, g=g, planned_set={"A"}, allow_conditional=True)

    # In contrast, evidence-mastered unlocks unconditionally
    assert is_admissible(act_b, selected_set=set(), mastered_set={"A"}, remaining_budget=5, g=g, allow_conditional=False)

    # In plan: B placed on day 2 is marked conditional
    states = {"A": ConceptState.cold_start(), "B": ConceptState.cold_start()}
    plan = generate_static_plan(g, states, budget=5, deadline_days=2, target_node="B")
    trace_day2_b = [e for e in plan["trace"] if e["node_id"] == "B" and e["day"] == 2][0]
    assert trace_day2_b["decision"] == "SELECTED"
    assert trace_day2_b["constraints"]["conditional"] is True
    assert trace_day2_b["constraints"]["revalidate_before_execution"] is True
    assert "B" in plan["days"][1]["conditional_activities"]


def test_failed_prerequisite_keeps_dependents_blocked():
    """Step 5: failed prerequisite keeps dependents blocked."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    g.add_node("B", baseline_duration=5)
    g.add_edge("A", "B")

    # A has failed learner state (Weak)
    weak_state = ConceptState(A=1.0, B=9.0, n=4, history=[0, 0, 0, 0])
    assert weak_state.classify() == "Weak"
    states = {"A": weak_state, "B": ConceptState.cold_start()}

    # is_admissible blocks dependent when prerequisite is Weak
    act_b = {"node_id": "B", "duration": 5, "prerequisites": ["A"]}
    assert not is_admissible(act_b, selected_set=set(), mastered_set=set(), remaining_budget=5, g=g, learner_states=states)

    # In plan: if A was completed and Weak, B stays blocked with PREREQUISITE_UNMET
    plan = generate_static_plan(g, states, budget=10, deadline_days=2, target_node="B", completed_nodes={"A"})
    b_entries = [e for e in plan["trace"] if e["node_id"] == "B"]
    assert all(e["decision"] == "FILTERED" for e in b_entries)
    assert any(e["reason_code"] == ReasonCode.PREREQUISITE_UNMET.value for e in b_entries)
    assert plan["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN


def test_uncertain_prerequisite_routes_to_uncertain_needs_assessment():
    """Step 5 & Defect 9: Uncertain prerequisite routes to UNCERTAIN_NEEDS_ASSESSMENT and an assessment candidate."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=6)
    g.add_node("B", baseline_duration=6)
    g.add_node("C", baseline_duration=6)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    states = {n: ConceptState.cold_start() for n in g.nodes}
    # Budget 10, deadline 2:
    # On day 1: A is scheduled (6 min). B cannot fit remaining budget (6 > 4), so B is not scheduled.
    # When C is evaluated on day 1: its prerequisite B was not scheduled and has Uncertain state.
    # Therefore, C routes to UNCERTAIN_NEEDS_ASSESSMENT, and B is yielded as assessment candidate.
    plan = generate_static_plan(g, states, budget=10, deadline_days=2, target_node="C")

    day1_c = [e for e in plan["trace"] if e["node_id"] == "C" and e["day"] == 1][0]
    assert day1_c["decision"] == "FILTERED"
    assert day1_c["reason_code"] == ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT.value

    # Assessment candidate is yielded for B
    assert "B" in plan["assessment_candidates"]


def test_completed_input_node_traced_as_completed():
    """Step 3: completed input node is traced with reason code COMPLETED."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    g.add_node("B", baseline_duration=5)
    g.add_edge("A", "B")

    # A completed by learner with Developing state (not evidence-Mastered)
    states = {"A": ConceptState(A=5.0, B=5.0, n=2, history=[1, 0]), "B": ConceptState.cold_start()}
    assert states["A"].classify() != "Mastered"

    plan = generate_static_baseline(g, states, budget=10, deadline_days=1, target_node="B", completed_nodes={"A"})
    a_entry = [e for e in plan["trace"] if e["node_id"] == "A" and e["day"] == 1][0]
    assert a_entry["decision"] == "FILTERED"
    assert a_entry["reason_code"] == ReasonCode.COMPLETED.value


def test_every_reason_code_in_enum_is_covered():
    """Step 5: verify all members of ReasonCode enum are defined and valid."""
    expected_codes = {
        "SELECTED",
        "PREREQUISITE_UNMET",
        "ALREADY_MASTERED",
        "ALREADY_SCHEDULED",
        "COMPLETED",
        "BLOCK_EXCEEDS_DAILY_BUDGET",
        "BUDGET_EXCEEDED",
        "UNCERTAIN_NEEDS_ASSESSMENT"
    }
    actual_codes = {c.value for c in ReasonCode}
    assert actual_codes == expected_codes
