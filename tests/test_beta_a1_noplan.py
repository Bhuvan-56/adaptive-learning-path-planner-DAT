import pytest
import networkx as nx
from src.curriculum.graph import load_graph
from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig, default_policy
from src.planning.replan import ReplanState, replan, assessment_result
from src.planning.feasibility import FeasibilityStatus, InfeasibilityReason
from src.trace.schema import ReasonCode
from src.planning.difficulty import DifficultyState
from src.planning.review import ReviewLog
from src.planning.static_baseline import generate_static_plan


def test_single_observation_leaves_concept_uncertain(tmp_path):
    """
    Characterization: A single practice observation on cold-start or diagnostic state
    increments n to 1. Since policy.min_obs == 3, the concept state remains 'Uncertain'.
    """
    policy, _ = default_policy()
    assert policy.min_obs == 3

    # Initial state with prior
    state = ConceptState.init_from_ability(0.6)
    assert state.n == 0
    assert state.classify(policy) == "Uncertain"

    # One correct observation
    state.update(correct=1, policy=policy)
    assert state.n == 1
    # n < min_obs strictly forces Uncertain classification
    assert state.classify(policy) == "Uncertain"


def test_replan_prerequisite_gate_blocks_on_uncertain_with_reason_code(tmp_path):
    """
    Characterization: In replan.py (line 509), when a prerequisite is in completed_nodes
    but has classify() == 'Uncertain', it fails the prerequisite gate.
    The downstream candidate is filtered with UNCERTAIN_NEEDS_ASSESSMENT, and the
    prerequisite is added to assessment_candidates.
    """
    policy, _ = default_policy()
    g = load_graph("data/curricula/demo_curriculum.json")

    # Prerequisite A is completed with 1 observation -> Uncertain
    st_a = ConceptState.cold_start()
    st_a.update(correct=1, policy=policy)
    assert st_a.classify(policy) == "Uncertain"

    learner_states = {
        "A": st_a,
        "B": ConceptState.cold_start(),
        "C": ConceptState.cold_start(),
        "D": ConceptState.cold_start(),
    }
    diff_states = {c: DifficultyState(difficulty=0.5) for c in g.nodes()}

    replan_state = ReplanState(
        graph=g,
        learner_states=learner_states,
        budget=10,
        deadline_days=5,
        target_node="D",
        completed_nodes={"A"},
        current_day=2,
        difficulty_states=diff_states,
        review_log=ReviewLog(),
        policy=policy,
    )

    ev = assessment_result("A", [1])
    result = replan(replan_state, ev)

    # Concept C requires A. In trace, C must be filtered with UNCERTAIN_NEEDS_ASSESSMENT
    trace_day2 = [t for t in result["trace"] if isinstance(t, dict) and t.get("day") == 2]
    c_trace = next((t for t in trace_day2 if t.get("node_id") == "C"), None)
    assert c_trace is not None
    assert c_trace["decision"] == "FILTERED"
    assert c_trace["reason_code"] == ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT

    # A was flagged as needing assessment
    assert "A" in result["assessment_candidates"]


def test_replan_starvation_when_all_prereqs_uncertain(tmp_path):
    """
    Characterization: On Day 2, after Day 1 completed A and B with 1 observation each:
    - Both A and B are Uncertain (n=1 < min_obs=3).
    - Downstream candidates C and D are blocked by Uncertain prerequisites.
    - Completed nodes A and B are not in remaining_nodes, not in remed_queue, and not in review.
    - Planner schedules 0 activities, remaining budget stays 10, resulting in HEURISTIC_NO_PLAN.
    """
    policy, _ = default_policy()
    g = load_graph("data/curricula/demo_curriculum.json")

    st_a = ConceptState.cold_start()
    st_a.update(correct=1, policy=policy)
    st_b = ConceptState.cold_start()
    st_b.update(correct=1, policy=policy)

    learner_states = {
        "A": st_a,
        "B": st_b,
        "C": ConceptState.cold_start(),
        "D": ConceptState.cold_start(),
    }
    diff_states = {c: DifficultyState(difficulty=0.5) for c in g.nodes()}

    replan_state = ReplanState(
        graph=g,
        learner_states=learner_states,
        budget=10,
        deadline_days=5,
        target_node="D",
        completed_nodes={"A", "B"},
        current_day=2,
        difficulty_states=diff_states,
        review_log=ReviewLog(),
        policy=policy,
        past_days=[{"day": 1, "activities": ["A", "B"]}],
    )

    ev = assessment_result("B", [1])
    result = replan(replan_state, ev)

    assert result["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN
    assert result["feasibility_explanation"]["reason_code"] == InfeasibilityReason.SCHEDULING_CONSTRAINTS_UNMET

    # Day 2 activities are empty despite 10 minutes of remaining budget
    day2_plan = next((d for d in result["days"] if d["day"] == 2), None)
    assert day2_plan is not None
    assert day2_plan["activities"] == []
    assert day2_plan["minutes_remaining"] == 10

    # Assessment candidates collected but never scheduled
    assert set(result["assessment_candidates"]) == {"A", "B", "C"}


def test_five_day_adaptive_horizon_reproduces_four_no_plan_days(tmp_path):
    """
    Characterization: Simulates a 5-day horizon for an adaptive learner:
    - Day 1: Schedules and executes ['A', 'B'].
    - Days 2-5: Each day evaluates to HEURISTIC_NO_PLAN with SCHEDULING_CONSTRAINTS_UNMET
      and 0 scheduled activities.
    Total no-plan days for this learner = 4.
    """
    policy, _ = default_policy()
    g = load_graph("data/curricula/demo_curriculum.json")

    initial_states = {c: ConceptState.cold_start() for c in g.nodes()}
    diff_states = {c: DifficultyState(difficulty=0.5) for c in g.nodes()}
    review_log = ReviewLog()

    active_plan = generate_static_plan(
        g=g,
        learner_states=initial_states,
        budget=10,
        deadline_days=5,
        target_node="D",
        policy=policy,
    )

    cur_replan_state = ReplanState(
        graph=g,
        learner_states=dict(initial_states),
        budget=10,
        deadline_days=5,
        target_node="D",
        difficulty_states=dict(diff_states),
        review_log=review_log,
        policy=policy,
    )

    completed_so_far = set()
    no_plan_count = 0
    executed_per_day = {}

    for day_idx in range(1, 6):
        status_str = str(active_plan.get("status"))
        if status_str in ("HEURISTIC_NO_PLAN", "FeasibilityStatus.HEURISTIC_NO_PLAN"):
            no_plan_count += 1
            day_activities = []
        else:
            day_activities = []
            for d in active_plan.get("days", []):
                if d.get("day") == day_idx:
                    day_activities = d.get("activities", [])
                    break

        executed_per_day[day_idx] = list(day_activities)

        for act in day_activities:
            completed_so_far.add(act)
            cur_replan_state.completed_nodes = set(completed_so_far)
            cur_replan_state.current_day = day_idx + 1
            ev = assessment_result(act, [1])
            active_plan = replan(cur_replan_state, ev)
            cur_replan_state.learner_states = active_plan["learner_states"]

    assert executed_per_day[1] == ["A", "B"]
    assert executed_per_day[2] == []
    assert executed_per_day[3] == []
    assert executed_per_day[4] == []
    assert executed_per_day[5] == []
    assert no_plan_count == 4


@pytest.mark.xfail(strict=True, reason="Candidate pending D1: learner whose only blocker is an Uncertain prerequisite still gets a non-empty plan")
def test_candidate_pending_d1_uncertain_prereq_yields_non_empty_plan(tmp_path):
    """
    Candidate test pending D1 decision:
    When a learner has completed prerequisite A (with n=1, Uncertain), and has 10 minutes of daily
    budget available, downstream candidate C (duration 10, requires A) or practice on A itself
    should be scheduled so the learner receives a non-empty daily plan rather than halting.
    Under the unfixed codebase, this test strictly fails because replan returns 0 activities
    and HEURISTIC_NO_PLAN.
    """
    policy, _ = default_policy()
    g = load_graph("data/curricula/demo_curriculum.json")

    st_a = ConceptState.cold_start()
    st_a.update(correct=1, policy=policy)
    assert st_a.classify(policy) == "Uncertain"

    learner_states = {
        "A": st_a,
        "B": ConceptState.cold_start(),
        "C": ConceptState.cold_start(),
        "D": ConceptState.cold_start(),
    }
    diff_states = {c: DifficultyState(difficulty=0.5) for c in g.nodes()}

    replan_state = ReplanState(
        graph=g,
        learner_states=learner_states,
        budget=10,
        deadline_days=5,
        target_node="D",
        completed_nodes={"A"},
        current_day=2,
        difficulty_states=diff_states,
        review_log=ReviewLog(),
        policy=policy,
        past_days=[{"day": 1, "activities": ["A"]}],
    )

    ev = assessment_result("A", [1])
    result = replan(replan_state, ev)

    day2_plan = next((d for d in result["days"] if d["day"] == 2), None)
    assert day2_plan is not None
    # A non-empty plan is expected if an Uncertain prerequisite does not completely starve the schedule
    assert len(day2_plan["activities"]) > 0, (
        f"Learner received empty plan on Day 2 due to Uncertain prerequisite A: {result.get('feasibility_explanation')}"
    )
    assert result["status"] != FeasibilityStatus.HEURISTIC_NO_PLAN

