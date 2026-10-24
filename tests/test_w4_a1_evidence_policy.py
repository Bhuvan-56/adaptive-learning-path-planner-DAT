import json
import os
import networkx as nx

from src.cli import run_demo
from src.planning.replan import replan, assessment_result
from src.planning.service import plan_request
from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig


def test_w4_d1_assessment_applied_once_in_cli_and_artifacts(tmp_path):
    """
    D1: For both pass and fail scenarios, n after minus n before must equal the number of responses.
    n, p, and state must be identical in response_updates.json, the saved plan's learner_states for A,
    and the trace entry for A.
    """
    out_dir = str(tmp_path / "cli_demo_d1")
    ret = run_demo(out_dir=out_dir, seed=20261012, budget=10, curriculum_path="data/curricula/demo_curriculum.json")
    assert ret == 0

    ru_path = os.path.join(out_dir, "response_updates.json")
    with open(ru_path, "r", encoding="utf-8") as f:
        ru_data = json.load(f)

    scenarios = [
        ("scenario_assessment_passed", "plan_assessment_passed.json", "trace_assessment_passed.json"),
        ("scenario_assessment_failed", "plan_assessment_failed.json", "trace_assessment_failed.json"),
    ]

    for sc_key, plan_filename, trace_filename in scenarios:
        sc = ru_data[sc_key]
        concept = sc["concept"]
        assert concept == "A"
        responses = sc["responses"]
        n_responses = len(responses)
        before = sc["before"]
        after = sc["after"]

        assert after["n"] - before["n"] == n_responses

        plan_path = os.path.join(out_dir, plan_filename)
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
        plan_a = plan_data["learner_states"]["A"]

        trace_path = os.path.join(out_dir, trace_filename)
        with open(trace_path, "r", encoding="utf-8") as f:
            trace_data = json.load(f)
        trace_a_entries = [e for e in trace_data if e.get("node_id") == "A"]
        assert len(trace_a_entries) > 0
        trace_a = trace_a_entries[0]["concept_state"]

        ru_n = after["n"]
        ru_p = round(after["p"], 8)
        ru_state = after["state"]

        plan_n = plan_a["n"]
        plan_p = round(plan_a["p"], 8)
        plan_cs = ConceptState(
            A=plan_a["A"],
            B=plan_a["B"],
            n=plan_a["n"],
            history=plan_a["history"]
        )
        plan_state = plan_cs.classify()

        trace_n = trace_a["n"]
        trace_p = round(trace_a["p"], 8)
        trace_state = trace_a["class"]

        assert ru_n == plan_n == trace_n, (
            f"Mismatch in n for {sc_key}: response_updates={ru_n}, plan={plan_n}, trace={trace_n}"
        )
        assert ru_p == plan_p == trace_p, (
            f"Mismatch in p for {sc_key}: response_updates={ru_p}, plan={plan_p}, trace={trace_p}"
        )
        assert ru_state == plan_state == trace_state, (
            f"Mismatch in state for {sc_key}: response_updates={ru_state}, plan={plan_state}, trace={trace_state}"
        )


def test_w4_d1_replay_rule_event_applied_once_per_call_and_twice_if_passed_twice():
    """
    Replay rule: an event is applied once per call, and passing the same event twice applies it twice.
    No event-ID de-duplication is performed.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    states = {"A": ConceptState.cold_start()}
    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 1,
        "target_node": "A",
        "current_day": 1
    }
    evt = assessment_result("A", [1, 1])

    res1 = replan(state, evt)
    assert res1["learner_states"]["A"].n == 2

    # Passing the exact same event again applies it a second time (n becomes 4)
    res2 = replan(state, evt)
    assert res2["learner_states"]["A"].n == 4


def test_w4_d2_a_mastered_p_different_decisions_in_plan_request():
    """
    (a) mastered_p 0.99 against default 0.85 gives different decisions for the same learner through plan_request.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5, base_difficulty=0.2)
    g.add_node("B", baseline_duration=5, base_difficulty=0.2)
    g.add_edge("A", "B")

    # Concept A: p=0.90, n=5. Classifies as Mastered under default (0.85), but Developing under 0.99.
    states_def = {"A": ConceptState(A=9.0, B=1.0, n=5, history=[1, 1, 1, 1]), "B": ConceptState.cold_start()}
    states_99 = {"A": ConceptState(A=9.0, B=1.0, n=5, history=[1, 1, 1, 1]), "B": ConceptState.cold_start()}

    pol_def = PolicyConfig(mastered_p=0.85)
    pol_99 = PolicyConfig(mastered_p=0.99)

    res_def = plan_request(g, states_def, budget=10, deadline_days=1, targets="B", policy=pol_def)
    res_99 = plan_request(g, states_99, budget=10, deadline_days=1, targets="B", policy=pol_99)

    assert res_def.is_valid and res_99.is_valid
    # Under default policy, A is already mastered, so Day 1 schedules ['B'].
    # Under 0.99 policy, A is not mastered (Developing), so Day 1 cannot just skip A and schedule B.
    def_acts = res_def.plan["days"][0]["activities"]
    acts_99 = res_99.plan["days"][0]["activities"]
    assert def_acts != acts_99, (
        f"Expected different decisions under mastered_p=0.99 vs default 0.85, got {def_acts} for both"
    )


def test_w4_d2_b_window_size_changes_quorum_and_classification():
    """
    (b) window_size 6 against 4 changes the quorum and the classification after the same response sequence.
    """
    pol4 = PolicyConfig(window_size=4)
    pol6 = PolicyConfig(window_size=6)
    assert pol4.quorum == 3
    assert pol6.quorum == 5

    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5, base_difficulty=0.2)
    states4 = {"A": ConceptState.cold_start()}
    states6 = {"A": ConceptState.cold_start()}
    evt = assessment_result("A", [1, 1, 1, 1])

    res4 = replan({"graph": g, "learner_states": states4, "budget": 10, "deadline_days": 1, "target_node": "A", "policy": pol4}, evt)
    res6 = replan({"graph": g, "learner_states": states6, "budget": 10, "deadline_days": 1, "target_node": "A", "policy": pol6}, evt)

    # After 4 responses, window is full for size 4 (quorum 3 met -> Mastered),
    # but not full for size 6 (len 4 < 6 -> Developing).
    class4 = res4["learner_states"]["A"].classify(pol4)
    class6 = res6["learner_states"]["A"].classify(pol6)
    assert class4 == "Mastered"
    assert class6 == "Developing"

    # Replan trace concept_state must also reflect the different classifications
    trace4_class = next(e for e in res4["trace"] if e["node_id"] == "A")["concept_state"]["class"]
    trace6_class = next(e for e in res6["trace"] if e["node_id"] == "A")["concept_state"]["class"]
    assert trace4_class == "Mastered"
    assert trace6_class == "Developing"


def test_w4_d2_c_bkt_params_different_p_inside_replan():
    """
    (c) different p_T, p_S or p_G give different p after the same responses inside replan.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5, base_difficulty=0.2)
    states1 = {"A": ConceptState.cold_start()}
    states2 = {"A": ConceptState.cold_start()}
    pol1 = PolicyConfig(p_T=0.10, p_S=0.10, p_G=0.25)
    pol2 = PolicyConfig(p_T=0.30, p_S=0.05, p_G=0.10)
    evt = assessment_result("A", [1, 1])

    res1 = replan({"graph": g, "learner_states": states1, "budget": 10, "deadline_days": 1, "target_node": "A", "policy": pol1}, evt)
    res2 = replan({"graph": g, "learner_states": states2, "budget": 10, "deadline_days": 1, "target_node": "A", "policy": pol2}, evt)

    p1 = res1["learner_states"]["A"].p
    p2 = res2["learner_states"]["A"].p
    assert p1 != p2, f"Expected different p under different BKT params, but both got {p1}"


def test_w4_d2_d_replan_trace_class_equals_state_classify_for_every_node():
    """
    (d) after a replan event the trace's concept_state class equals state.classify(policy) for every node.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5, base_difficulty=0.2)
    g.add_node("B", baseline_duration=5, base_difficulty=0.2)
    g.add_edge("A", "B")

    # A has p=0.90, n=5 -> Developing under mastered_p=0.99
    pol = PolicyConfig(mastered_p=0.99)
    states = {
        "A": ConceptState(A=9.0, B=1.0, n=5, history=[1, 1, 1, 1]),
        "B": ConceptState.cold_start()
    }
    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 1,
        "target_node": "B",
        "policy": pol
    }
    evt = assessment_result("A", [1])
    res = replan(state, evt)

    for entry in res["trace"]:
        nid = entry["node_id"]
        expected_class = res["learner_states"][nid].classify(pol)
        actual_class = entry["concept_state"]["class"]
        assert actual_class == expected_class, (
            f"Node '{nid}' trace class '{actual_class}' != expected '{expected_class}' under policy {pol}"
        )
