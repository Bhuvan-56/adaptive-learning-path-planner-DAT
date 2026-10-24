"""
Milestone M5 tests: Spaced Review and Prerequisite Remediation.

Covers:
- TC-5.1: Failed assessments trigger prerequisite remediation.
- TC-5.2: Decayed recall schedules spaced review under DECAY_BASELINE.
"""

import networkx as nx
import pytest

from src.state.learner_state import ConceptState
from src.trace.schema import ReasonCode
from src.trace.checker import check_trace
from src.trace.universe import get_candidate_universe
from src.planning.replan import replan, assessment_result, ReplanState
from src.planning.review import ReviewLog, DECAY_BASELINE


def test_tc_5_1_failed_assessments_trigger_prerequisite_remediation():
    """
    TC-5.1: Failed assessments trigger prerequisite remediation.

    When a concept has k consecutive failed assessments (k=2 from config/adaptive.yaml),
    replan returns a remediation plan: the not-Mastered ancestors of that concept
    in topological order, scheduled first inside the same daily budget, carrying
    reason code REMEDIATION_TRIGGERED.
    """
    # Graph: A -> B -> C
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=3, base_difficulty=0.5)
    g.add_node("B", baseline_duration=3, base_difficulty=0.5)
    g.add_node("C", baseline_duration=3, base_difficulty=0.5)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    # A is Mastered; B is not Mastered; C is not Mastered
    states = {
        "A": ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1]),
        "B": ConceptState.cold_start(),
        "C": ConceptState.cold_start(),
    }

    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 2,
        "target_node": "C",
        "current_day": 1,
    }

    # C receives 2 consecutive failed assessments (k=2)
    res = replan(state, assessment_result("C", [0, 0]))

    # Prerequisite remediation triggered for C's unmastered ancestor B
    day1_activities = res["days"][0]["activities"]
    assert len(day1_activities) >= 1
    # B is scheduled first as remediation
    assert day1_activities[0] == "B"

    # Trace carries REMEDIATION_TRIGGERED for B on day 1
    b_trace = [e for e in res["trace"] if e["node_id"] == "B" and e["day"] == 1]
    assert len(b_trace) == 1
    assert b_trace[0]["decision"] == "SELECTED"
    assert b_trace[0]["reason_code"] == ReasonCode.REMEDIATION_TRIGGERED.value

    # Verify trace completeness and checker rules
    cand_univ = get_candidate_universe(g, "C")
    assert check_trace(cand_univ, res["trace"], num_days=2, budget=10) is True


def test_tc_5_2_decayed_hlr_recall_schedules_spaced_review():
    """
    TC-5.2: Decayed recall schedules spaced review.

    Note: This test uses DECAY_BASELINE (R(dt) = 2 ** (-dt / H) with H fixed at
    half_life_prior_days = 14.0 days from experiments/m8_learner_eval.yaml; H is not
    learned or fitted).

    When a concept's evidence state is Mastered and its recall decays below
    review_eligibility_recall_threshold (0.85), it becomes review-eligible. Due reviews
    fill the leftover daily budget after required work, carrying reason code REVIEW_DUE.
    """
    # Graph: A -> B
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=3, base_difficulty=0.5)
    g.add_node("B", baseline_duration=4, base_difficulty=0.5)
    g.add_edge("A", "B")

    states = {
        "A": ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1]),
        "B": ConceptState.cold_start(),
    }

    # A was practiced on day 1; current day is day 6 (dt = 5.0 days)
    # Under DECAY_BASELINE: R(5) = 2 ** (-5 / 14) ≈ 0.781 < 0.85 (due for review)
    rl = ReviewLog()
    rl.record_attempt("A", time_in_days=1.0, correct=True)

    cand_univ = get_candidate_universe(g, "B")

    # Past history for days 1..5
    past_days = []
    past_trace = []
    for d in range(1, 6):
        past_days.append({
            "day": d,
            "activities": ["A"] if d == 1 else [],
            "conditional_activities": [],
            "minutes_used": 3 if d == 1 else 0,
            "minutes_remaining": 7 if d == 1 else 10,
            "missed": (d > 1),
        })
        for nid in sorted(list(cand_univ)):
            st = states[nid]
            past_trace.append({
                "node_id": nid,
                "day": d,
                "concept_state": {"p": st.p, "kappa": st.kappa, "sigma2": st.sigma2, "n": st.n, "class": st.classify()},
                "constraints": {"budget": 10, "remaining_budget": 7 if (d == 1 and nid == "A") else 10, "prerequisites": {}},
                "score_terms": {},
                "decision": "SELECTED" if (d == 1 and nid == "A") else "FILTERED",
                "reason_code": ReasonCode.SELECTED.value if (d == 1 and nid == "A") else (ReasonCode.ALREADY_MASTERED.value if nid == "A" else ReasonCode.PREREQUISITE_UNMET.value),
                "policy_version": "static_baseline_v0",
            })

    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 6,
        "target_node": "B",
        "current_day": 6,
        "review_log": rl,
        "past_days": past_days,
        "past_trace": past_trace,
    }

    # B has an assessment event on day 6 (initial success)
    res = replan(state, assessment_result("B", [1]))

    day6 = [d for d in res["days"] if d["day"] == 6][0]
    # Required target work B is scheduled, and leftover budget (10 - 4 = 6) fits review A (dur 3)
    assert "B" in day6["activities"]
    assert "A" in day6["activities"]
    # Required work B is scheduled before due review A
    assert day6["activities"].index("B") < day6["activities"].index("A")

    # Trace entry for A carries REVIEW_DUE on day 6
    a_trace = [e for e in res["trace"] if e["node_id"] == "A" and e["day"] == 6]
    assert len(a_trace) == 1
    assert a_trace[0]["decision"] == "SELECTED"
    assert a_trace[0]["reason_code"] == ReasonCode.REVIEW_DUE.value

    # Verify trace completeness across all 6 days
    assert check_trace(cand_univ, res["trace"], num_days=6, budget=10) is True
