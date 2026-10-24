import json
import os
import networkx as nx

from src.cli import run_demo
from src.planning.replan import replan, assessment_result
from src.state.learner_state import ConceptState


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
