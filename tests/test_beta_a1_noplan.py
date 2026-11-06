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


def test_replan_practises_uncertain_prereqs_instead_of_starving(tmp_path):
    """
    W7 deadlock fix (docs/w7/preregistration_deadlock_fix.md). Before the fix this
    setup starved: 0 activities on Day 2 and HEURISTIC_NO_PLAN.
    On Day 2, after Day 1 completed A and B with 1 observation each:
    - Both A and B are Uncertain (n=1 < min_obs=3) and block C and D.
    - Day 2 practises A and B (PRACTICE_FOR_EVIDENCE); C and D stay blocked that day.
    - C (Day 3) and D (Day 4) follow conditionally, and the plan is FEASIBLE.
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

    assert result["status"] == FeasibilityStatus.FEASIBLE

    days = {d["day"]: d for d in result["days"]}
    assert days[2]["activities"] == ["A", "B"]
    assert days[2]["minutes_remaining"] == 0
    assert days[3]["activities"] == ["C"] and days[3]["conditional_activities"] == ["C"]
    assert days[4]["activities"] == ["D"] and days[4]["conditional_activities"] == ["D"]

    day2 = {t["node_id"]: t for t in result["trace"] if isinstance(t, dict) and t.get("day") == 2}
    assert day2["A"]["reason_code"] == ReasonCode.PRACTICE_FOR_EVIDENCE
    assert day2["B"]["reason_code"] == ReasonCode.PRACTICE_FOR_EVIDENCE
    assert day2["C"]["reason_code"] == ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT
    assert day2["D"]["reason_code"] == ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT

    assert set(result["assessment_candidates"]) == {"A", "B", "C"}


def test_five_day_adaptive_horizon_keeps_learner_working(tmp_path):
    """
    W7 deadlock fix. Before the fix this always-correct learner did A and B on Day 1
    and then got 4 no-plan days with nothing to do.
    Now (loop as in src/evaluation/integrated.py, which runs a HEURISTIC_NO_PLAN
    plan's listed work): A and B are practised until they leave Uncertain
    (min_obs 3), then C starts. Every day has work; only Day 5 starts from a
    plan that cannot fit D any more.
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
    assert executed_per_day[2] == ["A", "B"]
    assert executed_per_day[3] == ["A", "B"]
    assert executed_per_day[4] == ["C"]
    assert executed_per_day[5] == ["C"]
    assert no_plan_count == 1


def test_candidate_pending_d1_uncertain_prereq_yields_non_empty_plan(tmp_path):
    """
    Candidate test pending D1 decision:
    When a learner has completed prerequisite A (with n=1, Uncertain), and has 10 minutes of daily
    budget available, downstream candidate C (duration 10, requires A) or practice on A itself
    should be scheduled so the learner receives a non-empty daily plan rather than halting.
    Under the unfixed codebase, this test strictly failed because replan returned 0 activities
    and HEURISTIC_NO_PLAN. It passes since the W7 deadlock fix, which reverses D1
    (docs/w7/preregistration_deadlock_fix.md); the xfail marker was removed.
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

