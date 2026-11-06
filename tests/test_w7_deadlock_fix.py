"""W7 adaptive deadlock fix (docs/w7/preregistration_deadlock_fix.md).

1. replan practises completed prerequisites that are still Uncertain or Weak
   and block remaining work (PRACTICE_FOR_EVIDENCE), instead of stalling.
2. The adaptive loop runs the work listed by a HEURISTIC_NO_PLAN plan.
3. A prerequisite planned on an earlier day satisfies the gate conditionally,
   also when it is Weak (static planner and replan).
"""
import random

import pandas as pd

from src.curriculum.graph import load_graph
from src.evaluation.integrated import run_integrated_evaluation
from src.planning.feasibility import FeasibilityStatus
from src.planning.replan import ReplanState, assessment_result, replan
from src.planning.review import ReviewLog
from src.planning.static_baseline import generate_static_plan
from src.state.learner_state import ConceptState
from src.state.policy import default_policy
from src.trace.checker import check_trace
from src.trace.schema import ReasonCode
from src.trace.universe import get_candidate_universe

CURRICULUM = "data/curricula/demo_curriculum.json"
POLICY, _ = default_policy()


def _state(answers):
    st = ConceptState.cold_start()
    for a in answers:
        st.update(int(a), policy=POLICY)
    return st


def _days(plan):
    return {d["day"]: d for d in plan["days"]}


def test_static_plan_weak_prereq_planned_earlier_unlocks_dependent():
    g = load_graph(CURRICULUM)
    states = {n: _state("") for n in g.nodes}
    states["A"] = _state("1111")
    states["B"] = _state("0000")
    assert states["B"].classify(POLICY) == "Weak"

    plan = generate_static_plan(g=g, learner_states=states, budget=10, deadline_days=5,
                                target_node="D", policy=POLICY)

    assert plan["status"] == FeasibilityStatus.FEASIBLE
    days = _days(plan)
    assert days[1]["activities"] == ["B"]
    assert days[2]["activities"] == ["C"]
    assert days[3]["activities"] == ["D"]
    assert "D" in days[3]["conditional_activities"]
    d1 = next(t for t in plan["trace"] if t["day"] == 1 and t["node_id"] == "D")
    assert d1["reason_code"] in (ReasonCode.PREREQUISITE_UNMET.value, ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT.value)
    assert check_trace(get_candidate_universe(g, "D"), plan["trace"], num_days=5, budget=10)


def test_replan_practises_completed_weak_prereq_then_dependents_follow():
    g = load_graph(CURRICULUM)
    states = {n: _state("") for n in g.nodes}
    states["A"] = _state("000")
    st = ReplanState(graph=g, learner_states=states, budget=10, deadline_days=5, target_node="D",
                     completed_nodes={"A"}, current_day=2, review_log=ReviewLog(), policy=POLICY,
                     past_days=[{"day": 1, "activities": ["A"]}])
    plan = replan(st, assessment_result("A", [0]))
    assert plan["learner_states"]["A"].classify(POLICY) == "Weak"

    days = _days(plan)
    assert days[2]["activities"][0] == "A"
    a2 = next(t for t in plan["trace"] if t["day"] == 2 and t["node_id"] == "A")
    assert a2["decision"] == "SELECTED" and a2["reason_code"] == ReasonCode.PRACTICE_FOR_EVIDENCE.value
    # B and C need A: not on the practice day, conditionally afterwards.
    for nid in ("B", "C"):
        first = min(d for d, e in days.items() if nid in e["activities"])
        assert first > 2
        assert nid in days[first]["conditional_activities"]
    assert plan["status"] == FeasibilityStatus.FEASIBLE
    assert check_trace(get_candidate_universe(g, "D"), [t for t in plan["trace"] if t["day"] >= 2] +
                       [dict(t, day=1) for t in plan["trace"] if t["day"] == 2], num_days=5, budget=10)


def test_replan_never_starts_a_concept_on_the_day_its_prereq_is_practised():
    """New (not yet completed) work never relies on a prerequisite practised the
    same day. Practising two completed concepts on one day is allowed: neither
    is new work, and prerequisite violations count first-time study only."""
    g = load_graph(CURRICULUM)
    rng = random.Random(3)
    for _ in range(300):
        answers = {n: "".join(rng.choice("01") for _ in range(rng.choice([0, 1, 2, 4]))) for n in g.nodes}
        done = {n for n in g.nodes if answers[n] and rng.random() < 0.7}
        states = {n: _state(answers[n]) for n in g.nodes}
        st = ReplanState(graph=g, learner_states=states, budget=rng.choice([10, 15, 20]), deadline_days=5,
                         target_node="D", completed_nodes=done, current_day=1, review_log=ReviewLog(),
                         policy=POLICY)
        plan = replan(st, {"type": "changed_deadline", "new_days": 5})
        if not isinstance(plan["trace"], list):
            continue
        practised = {(t["day"], t["node_id"]) for t in plan["trace"]
                     if t["reason_code"] == ReasonCode.PRACTICE_FOR_EVIDENCE.value}
        for day in plan["days"]:
            for nid in day["activities"]:
                if nid in done:
                    continue
                for p in g.predecessors(nid):
                    assert (day["day"], p) not in practised, (answers, done, plan["days"])
        assert check_trace(get_candidate_universe(g, "D"), plan["trace"], num_days=5, budget=st.budget)


def test_integrated_adaptive_arm_no_longer_starves(tmp_path):
    res = run_integrated_evaluation(
        config_path="experiments/w5_final.yaml",
        output_dir=str(tmp_path / "w7_fix"),
        override_learners=6,
        override_resamples=10,
    )
    df = pd.read_csv(res["csv_path"])
    adaptive = df[df.arm == "adaptive_full"]
    assert len(adaptive) == 6
    # Before the fix every adaptive learner had 4 no-plan days out of 5.
    assert adaptive.no_plan_days.max() < 4
    replan_arms = ["adaptive_full", "ablation_no_diagnostic", "ablation_no_difficulty_step",
                   "ablation_no_review", "ablation_no_remediation"]
    for arm in replan_arms:
        g = df[df.arm == arm]
        assert (g.prereq_violations == 0).all(), arm
        assert (g.budget_violations == 0).all(), arm
