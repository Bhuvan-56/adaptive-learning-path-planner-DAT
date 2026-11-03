import pytest
import networkx as nx

from src.curriculum.graph import load_graph
from src.state.learner_state import ConceptState
from src.state.policy import default_policy
from src.planning.service import plan_request
from src.trace.checker import check_trace
from src.trace.schema import ReasonCode
from src.trace.universe import get_candidate_universe


def test_tc_8_1_different_mastery_profiles_produce_distinct_plans():
    """
    TC-8.1 (Module M8 / Group M8-a):
    Scenario: Two synthetic learners with distinctly different prior mastery profiles
              (Novice vs. Intermediate) request a plan for the same target ('D').
    Expected: The two generated plans are mathematically and structurally different.
    """
    g = load_graph("data/curricula/demo_curriculum.json")
    policy, _ = default_policy()
    target_node = "D"
    budget = 10
    deadline_days = 5

    # Profile 1: Novice - unprobed, cold-start mastery across all concepts
    states_novice = {nid: ConceptState.cold_start() for nid in g.nodes}

    # Profile 2: Intermediate - prerequisites A and B probed & evidence-Mastered, downstream unprobed
    states_intermediate = {
        "A": ConceptState(A=9.0, B=1.0, n=8, history=[1, 1, 1, 1]),
        "B": ConceptState(A=9.0, B=1.0, n=8, history=[1, 1, 1, 1]),
        "C": ConceptState.cold_start(),
        "D": ConceptState.cold_start(),
    }

    # Generate plans for both learners requesting the same target node
    res_novice = plan_request(
        graph=g,
        learner_states=states_novice,
        budget=budget,
        deadline_days=deadline_days,
        targets=target_node,
        policy=policy,
    )
    res_inter = plan_request(
        graph=g,
        learner_states=states_intermediate,
        budget=budget,
        deadline_days=deadline_days,
        targets=target_node,
        policy=policy,
    )

    assert res_novice.is_valid, f"Novice plan request failed: {res_novice.message}"
    assert res_inter.is_valid, f"Intermediate plan request failed: {res_inter.message}"

    plan_novice = res_novice.plan
    plan_inter = res_inter.plan

    # 1. Structural differentiation: Daily activity schedules differ
    novice_days = [(d["day"], d["activities"]) for d in plan_novice["days"] if d["activities"]]
    inter_days = [(d["day"], d["activities"]) for d in plan_inter["days"] if d["activities"]]

    assert novice_days != inter_days, "Plans must be structurally distinct across different profiles"

    novice_day1 = plan_novice["days"][0]["activities"]
    inter_day1 = plan_inter["days"][0]["activities"]

    assert novice_day1 == ["A", "B"], f"Novice Day 1 should schedule prerequisites A and B, got {novice_day1}"
    assert inter_day1 == ["C"], f"Intermediate Day 1 should schedule downstream C, got {inter_day1}"

    # Mastered prerequisites A and B are skipped for Intermediate learner
    assert "A" not in inter_day1 and "B" not in inter_day1

    # Active duration differs: Novice requires 3 days, Intermediate requires 2 days
    assert len(novice_days) == 3
    assert len(inter_days) == 2

    # 2. Mathematical differentiation: Trace and state differences
    trace_novice = plan_novice["trace"]
    trace_inter = plan_inter["trace"]

    # Decision and reason codes on Day 1 differ
    t1_day1 = {t["node_id"]: (t["decision"], t["reason_code"]) for t in trace_novice if t["day"] == 1}
    t2_day1 = {t["node_id"]: (t["decision"], t["reason_code"]) for t in trace_inter if t["day"] == 1}

    assert t1_day1["A"] == ("SELECTED", ReasonCode.SELECTED.value)
    assert t2_day1["A"] == ("FILTERED", ReasonCode.ALREADY_MASTERED.value)

    assert t1_day1["C"] == ("FILTERED", ReasonCode.BUDGET_EXCEEDED.value)
    assert t2_day1["C"] == ("SELECTED", ReasonCode.SELECTED.value)

    # Observable concept states in traces reflect distinct prior parameters
    cs_novice_a = next(t for t in trace_novice if t["node_id"] == "A")["concept_state"]
    cs_inter_a = next(t for t in trace_inter if t["node_id"] == "A")["concept_state"]

    assert cs_novice_a["p"] == pytest.approx(0.5)
    assert cs_novice_a["class"] == "Uncertain"

    assert cs_inter_a["p"] == pytest.approx(0.9)
    assert cs_inter_a["class"] == "Mastered"

    # 3. Validation: Both traces satisfy complete candidate universe coverage
    candidate_universe = get_candidate_universe(g, target_node)
    assert check_trace(candidate_universe, trace_novice, num_days=deadline_days, budget=budget)
    assert check_trace(candidate_universe, trace_inter, num_days=deadline_days, budget=budget)
