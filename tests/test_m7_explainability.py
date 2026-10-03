import json
import os
import pytest
from src.curriculum.graph import load_graph
from src.state.learner_state import ConceptState
from src.planning.static_baseline import generate_static_plan
from src.trace.universe import get_candidate_universe
from src.trace.checker import check_trace

FIXTURE_GRAPH = os.path.join(os.path.dirname(__file__), "fixtures", "graphs", "valid_branching.json")


def test_trace_has_one_entry_per_candidate():
    """TC-7.1: Daily plan includes structured JSON audit trace with 1 entry per candidate per day."""
    g = load_graph(FIXTURE_GRAPH)
    learner_states = {n: ConceptState.cold_start() for n in g.nodes}

    plan = generate_static_plan(g, learner_states, budget=15, deadline_days=2, target_node="D")
    universe = get_candidate_universe(g, "D")

    trace = plan["trace"]
    assert len(trace) > 0

    # Validate using automated checker
    assert check_trace(universe, trace, num_days=2)


def test_blocked_and_skipped_nodes_visible():
    """TC-7.2: Blocked and skipped (mastered) material are documented in JSON trace with reason codes."""
    g = load_graph(FIXTURE_GRAPH)
    learner_states = {n: ConceptState.cold_start() for n in g.nodes}
    # Mark node A as Mastered
    learner_states["A"] = ConceptState(A=8.5, B=1.5, n=4, history=[1, 1, 1, 1])  # p=0.85, Mastered with full window

    plan = generate_static_plan(g, learner_states, budget=15, deadline_days=2, target_node="D")
    trace = plan["trace"]

    a_entries = [e for e in trace if e["node_id"] == "A"]
    assert len(a_entries) > 0
    assert a_entries[0]["reason_code"] == "ALREADY_MASTERED"

    # Save sample trace outputs
    os.makedirs("evaluation/results", exist_ok=True)
    with open("evaluation/results/sample_trace_normal.json", "w", encoding="utf-8") as f:
        json.dump(plan["trace"], f, indent=2)


def test_checker_fails_on_missing_candidate():
    """TC-7.3: Checker hard-fails if a candidate node is missing from trace."""
    universe = {"A", "B", "C", "D"}
    incomplete_trace = [
        {"node_id": "A", "day": 1, "decision": "SELECTED", "reason_code": "SELECTED"},
        {"node_id": "B", "day": 1, "decision": "SELECTED", "reason_code": "SELECTED"},
        {"node_id": "C", "day": 1, "decision": "SELECTED", "reason_code": "SELECTED"},
        # "D" missing
    ]

    with pytest.raises(ValueError, match="missing candidate nodes"):
        check_trace(universe, incomplete_trace, num_days=1)


def test_checker_fails_on_duplicate():
    """TC-7.3: Checker hard-fails if a candidate node is duplicated on a day."""
    universe = {"A", "B"}
    duplicate_trace = [
        {"node_id": "A", "day": 1, "decision": "SELECTED", "reason_code": "SELECTED"},
        {"node_id": "A", "day": 1, "decision": "SELECTED", "reason_code": "SELECTED"},
        {"node_id": "B", "day": 1, "decision": "SELECTED", "reason_code": "SELECTED"},
    ]

    with pytest.raises(ValueError, match="Duplicate trace entry"):
        check_trace(universe, duplicate_trace, num_days=1)


def test_checker_fails_on_invalid_reason_code():
    """TC-7.3: Checker hard-fails if a filtered node has an invalid reason code."""
    universe = {"A"}
    invalid_code_trace = [
        {"node_id": "A", "day": 1, "decision": "FILTERED", "reason_code": "SOME_FAKE_REASON"}
    ]

    with pytest.raises(ValueError, match="invalid reason code"):
        check_trace(universe, invalid_code_trace, num_days=1)


def test_infeasible_sample_trace_exported():
    """Exports sample infeasible trace for evaluation artifacts."""
    g = load_graph(FIXTURE_GRAPH)
    learner_states = {n: ConceptState.cold_start() for n in g.nodes}

    plan = generate_static_plan(g, learner_states, budget=5, deadline_days=2, target_node="D")
    assert plan["status"] == "INFEASIBLE_PROVED"

    with open("evaluation/results/sample_trace_infeasible.json", "w", encoding="utf-8") as f:
        json.dump(plan["trace"], f, indent=2)
