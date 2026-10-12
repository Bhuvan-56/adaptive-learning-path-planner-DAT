import networkx as nx
import pytest

from src.state.learner_state import ConceptState
from src.planning.feasibility import FeasibilityStatus, InfeasibilityReason
from src.planning.replan import (
    replan,
    ReplanState,
    assessment_result,
    missed_day,
    changed_budget,
    changed_deadline
)
from src.trace.checker import check_trace, check_no_plan_trace
from src.trace.schema import ReasonCode


def test_event_uncertain_prereq_assessment_passes_dependent_admissible():
    """Test 1: Uncertain prerequisite -> assessment passes -> BKT update -> dependent becomes admissible."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    g.add_node("B", baseline_duration=5)
    g.add_edge("A", "B")

    # Initial state: A is Uncertain
    states = {
        "A": ConceptState.cold_start(),
        "B": ConceptState.cold_start()
    }
    assert states["A"].classify() == "Uncertain"

    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 2,
        "target_node": "B",
        "current_day": 1
    }

    # Assessment passes: A gets 4 consecutive correct answers
    evt = assessment_result("A", [1, 1, 1, 1])
    result = replan(state, evt)

    # 1. BKT update executed: A is now Mastered
    assert states["A"].classify() == "Mastered"

    # 2. Dependent B became admissible and was scheduled
    assert result["status"] == FeasibilityStatus.FEASIBLE
    assert "B" in result["days"][0]["activities"]

    # 3. Trace passes check_trace
    universe = {"A", "B"}
    assert check_trace(universe, result["trace"], num_days=2)


def test_event_failed_assessment_prereq_dependent_stays_blocked():
    """Test 2: Uncertain prerequisite -> failed assessment -> BKT update (Weak) -> dependent stays blocked."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    g.add_node("B", baseline_duration=5)
    g.add_edge("A", "B")

    states = {
        "A": ConceptState.cold_start(),
        "B": ConceptState.cold_start()
    }
    assert states["A"].classify() == "Uncertain"

    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 2,
        "target_node": "B",
        "current_day": 1
    }

    # Assessment fails: A gets 4 consecutive incorrect answers
    evt = assessment_result("A", [0, 0, 0, 0])
    result = replan(state, evt)

    # 1. BKT update executed: A is now Weak
    assert states["A"].classify() == "Weak"

    # 2. Dependent B stays blocked and is not scheduled
    assert result["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN
    for d in result["days"]:
        assert "B" not in d["activities"]

    # B entries carry PREREQUISITE_UNMET
    b_entries = [e for e in result["trace"] if e["node_id"] == "B"]
    assert all(e["decision"] == "FILTERED" for e in b_entries)
    assert any(e["reason_code"] == ReasonCode.PREREQUISITE_UNMET.value for e in b_entries)

    # 3. Trace passes check_trace
    universe = {"A", "B"}
    assert check_trace(universe, result["trace"], num_days=2)


def test_event_missed_day_keeps_completed_work():
    """Test 3: Missed day keeps completed work and recomputes future plan."""
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5)
    g.add_node("B", baseline_duration=5)
    g.add_edge("A", "B")

    # Day 1 was completed: learner did A and mastered it
    states = {
        "A": ConceptState(A=8.5, B=1.5, n=4, history=[1, 1, 1, 1]),
        "B": ConceptState.cold_start()
    }

    past_days = [{
        "day": 1,
        "activities": ["A"],
        "conditional_activities": [],
        "minutes_used": 5,
        "minutes_remaining": 0,
        "missed": False
    }]

    # Past trace for day 1
    past_trace = [
        {
            "node_id": "A",
            "day": 1,
            "concept_state": {"p": 0.85, "kappa": 10.0, "sigma2": 0.011, "n": 4, "class": "Mastered"},
            "constraints": {"budget": 5, "remaining_budget": 5, "prerequisites": {}},
            "score_terms": {},
            "decision": "SELECTED",
            "reason_code": ReasonCode.SELECTED.value,
            "policy_version": "static_baseline_v0"
        },
        {
            "node_id": "B",
            "day": 1,
            "concept_state": {"p": 0.5, "kappa": 2.0, "sigma2": 0.083, "n": 0, "class": "Uncertain"},
            "constraints": {"budget": 5, "remaining_budget": 0, "prerequisites": {"A": True}},
            "score_terms": {},
            "decision": "FILTERED",
            "reason_code": ReasonCode.BUDGET_EXCEEDED.value,
            "policy_version": "static_baseline_v0"
        }
    ]

    state = ReplanState(
        graph=g,
        learner_states=states,
        budget=5,
        deadline_days=3,
        target_node="B",
        current_day=2,
        completed_nodes={"A"},
        past_days=past_days,
        past_trace=past_trace
    )

    evt = missed_day()
    result = replan(state, evt)

    # 1. Completed work A is not deleted or overwritten
    assert "A" in result["completed_nodes"]
    assert result["days"][0]["activities"] == ["A"]

    # 2. Day 2 is recorded as missed
    assert result["days"][1]["missed"] is True
    assert result["days"][1]["activities"] == []

    # 3. Day 3 recomputes and schedules B
    assert "B" in result["days"][2]["activities"]

    # 4. Entire trace passes check_trace for all 3 days
    universe = {"A", "B"}
    assert check_trace(universe, result["trace"], num_days=3)


def test_event_budget_reduced_gives_valid_plan_or_structured_infeasibility():
    """Test 4: Budget reduced gives either a valid plan or a structured infeasibility result with alternatives."""
    # Subtest 4a: Infeasible case (task duration 6 exceeds reduced budget 5)
    g_infeasible = nx.DiGraph()
    g_infeasible.add_node("A", baseline_duration=6)

    state_inf = {
        "graph": g_infeasible,
        "learner_states": {"A": ConceptState.cold_start()},
        "budget": 10,
        "deadline_days": 2,
        "target_node": "A",
        "current_day": 1
    }

    result_inf = replan(state_inf, changed_budget(5))
    assert result_inf["status"] == FeasibilityStatus.INFEASIBLE_PROVED
    expl = result_inf["feasibility_explanation"]
    assert expl["reason_code"] == InfeasibilityReason.BLOCK_EXCEEDS_DAILY_BUDGET
    assert "minimum_fix" in expl
    assert "at least 6 minutes" in expl["minimum_fix"]
    assert check_no_plan_trace(result_inf["trace"])

    # Subtest 4b: Valid plan case (tasks duration 4 fit reduced budget 5)
    g_feasible = nx.DiGraph()
    g_feasible.add_node("A", baseline_duration=4)
    g_feasible.add_node("B", baseline_duration=4)
    g_feasible.add_edge("A", "B")

    state_fea = {
        "graph": g_feasible,
        "learner_states": {"A": ConceptState.cold_start(), "B": ConceptState.cold_start()},
        "budget": 10,
        "deadline_days": 2,
        "target_node": "B",
        "current_day": 1
    }

    result_fea = replan(state_fea, changed_budget(5))
    assert result_fea["status"] == FeasibilityStatus.FEASIBLE
    assert len(result_fea["days"]) == 2
    assert "A" in result_fea["days"][0]["activities"]
    assert "B" in result_fea["days"][1]["activities"]
    assert check_trace({"A", "B"}, result_fea["trace"], num_days=2)


def test_event_deadline_shortened_gives_valid_plan_or_structured_infeasibility():
    """Test 5: Deadline shortened gives either a valid plan or a structured infeasibility result with alternatives."""
    # Subtest 5a: Infeasible case (total work 12 exceeds reduced deadline 1 day * budget 10 = 10)
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=6)
    g.add_node("B", baseline_duration=6)
    g.add_edge("A", "B")

    state_inf = {
        "graph": g,
        "learner_states": {"A": ConceptState.cold_start(), "B": ConceptState.cold_start()},
        "budget": 10,
        "deadline_days": 3,
        "target_node": "B",
        "current_day": 1
    }

    result_inf = replan(state_inf, changed_deadline(1))
    assert result_inf["status"] == FeasibilityStatus.INFEASIBLE_PROVED
    expl = result_inf["feasibility_explanation"]
    assert expl["reason_code"] == InfeasibilityReason.CAPACITY_EXCEEDED
    assert "necessary_not_sufficient_fixes" in expl
    assert check_no_plan_trace(result_inf["trace"])

    # Subtest 5b: Feasible case (deadline shortened from 5 days to 2 days, capacity 20 >= 12)
    state_fea = {
        "graph": g,
        "learner_states": {"A": ConceptState.cold_start(), "B": ConceptState.cold_start()},
        "budget": 10,
        "deadline_days": 5,
        "target_node": "B",
        "current_day": 1
    }

    result_fea = replan(state_fea, changed_deadline(2))
    assert result_fea["status"] == FeasibilityStatus.FEASIBLE
    assert len(result_fea["days"]) == 2
    assert "A" in result_fea["days"][0]["activities"]
    assert "B" in result_fea["days"][1]["activities"]
    assert check_trace({"A", "B"}, result_fea["trace"], num_days=2)
