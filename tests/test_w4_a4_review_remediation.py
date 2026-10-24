"""
Tests for Module W4/A4: Spaced Review and Prerequisite Remediation.

Covers:
1. Eligibility at threshold boundary (just above and just below 0.85).
2. Review never displacing required work.
3. Review deferred when budget is short.
4. k failures trigger remediation and k-1 do not.
5. Remediation inside the same daily budget.
6. Remediation that cannot fit returns a structured reason (never a silent drop).
7. Every new trace passes check_trace.
8. Timestamps recorded in ReviewLog (simulated days since plan start).
9. DECAY_BASELINE naming and strict configuration loading.
"""

import networkx as nx
import pytest

from src.state.learner_state import ConceptState
from src.trace.schema import ReasonCode
from src.trace.checker import check_trace, check_no_plan_trace
from src.trace.universe import get_candidate_universe
from src.planning.feasibility import FeasibilityStatus
from src.planning.replan import replan, assessment_result, ReplanState
from src.planning.review import (
    ReviewLog,
    ReviewRecord,
    is_review_eligible,
    calculate_recall_decay,
    get_remediation_ancestors,
    load_review_eval_config,
    load_remediation_config,
    DECAY_BASELINE,
)


def make_mastered_state() -> ConceptState:
    """Helper creating an evidence-Mastered ConceptState."""
    s = ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1])
    assert s.classify() == "Mastered"
    return s


def test_decay_baseline_naming_and_config():
    """DECAY_BASELINE is explicitly named and read from experiments/m8_learner_eval.yaml."""
    assert DECAY_BASELINE == "DECAY_BASELINE"

    eval_cfg = load_review_eval_config()
    assert eval_cfg["half_life_prior_days"] == pytest.approx(14.0)
    assert eval_cfg["review_eligibility_recall_threshold"] == pytest.approx(0.85)

    rem_k = load_remediation_config()
    assert rem_k == 2


def test_review_eligibility_boundary_above_and_below():
    """
    Evaluates review eligibility at the threshold boundary under DECAY_BASELINE.

    Formula: R(dt) = 2 ** (-dt / 14.0)
    Threshold = 0.85
    Exact boundary: dt* = -14.0 * log2(0.85) ≈ 3.2825 days.
    - dt = 3.0 days: R(3) ≈ 0.8619 > 0.85 -> NOT eligible.
    - dt = 3.5 days: R(3.5) ≈ 0.8409 < 0.85 -> ELIGIBLE.
    """
    mastered_state = make_mastered_state()

    rl = ReviewLog()
    rl.record_attempt("C1", time_in_days=1.0, correct=True)

    # 1. Below boundary: day 4.0 -> dt = 3.0 days -> R ≈ 0.8619 > 0.85 (Not eligible)
    is_elig_below, r_below = is_review_eligible(
        "C1", mastered_state, rl, current_day=4.0, half_life_days=14.0, threshold=0.85
    )
    assert not is_elig_below
    assert r_below > 0.85
    assert r_below == pytest.approx(2 ** (-3.0 / 14.0))

    # 2. Above boundary: day 4.5 -> dt = 3.5 days -> R ≈ 0.8409 < 0.85 (Eligible)
    is_elig_above, r_above = is_review_eligible(
        "C1", mastered_state, rl, current_day=4.5, half_life_days=14.0, threshold=0.85
    )
    assert is_elig_above
    assert r_above < 0.85
    assert r_above == pytest.approx(2 ** (-3.5 / 14.0))

    # 3. Non-Mastered state is never eligible even with high decay
    weak_state = ConceptState(A=1.0, B=4.0, n=5, history=[0, 0, 0, 0])
    is_elig_weak, _ = is_review_eligible(
        "C1", weak_state, rl, current_day=10.0, half_life_days=14.0, threshold=0.85
    )
    assert not is_elig_weak


def test_review_never_displaces_required_work():
    """
    Daily budget rule: Planned work toward the target is scheduled before due reviews.
    Reviews never displace required work.
    """
    g = nx.DiGraph()
    # A is Mastered; B is required target work
    g.add_node("A", baseline_duration=5, base_difficulty=0.5)
    g.add_node("B", baseline_duration=8, base_difficulty=0.5)
    g.add_edge("A", "B")

    states = {
        "A": make_mastered_state(),
        "B": ConceptState.cold_start(),
    }

    # A was practiced on day 1; current_day is 10 (dt = 9 days -> R ≈ 0.64 < 0.85, due)
    rl = ReviewLog()
    rl.record_attempt("A", time_in_days=1.0, correct=True)

    state = {
        "graph": g,
        "learner_states": states,
        "budget": 10,
        "deadline_days": 10,
        "target_node": "B",
        "current_day": 10,
        "review_log": rl,
    }

    res = replan(state, assessment_result("B", [1]))

    day10 = res["days"][0]
    # Required work B takes 8 minutes, leftover is 2 minutes
    assert day10["activities"] == ["B"]
    assert day10["minutes_used"] == 8
    assert day10["minutes_remaining"] == 2

    # A did not fit in leftover budget (dur 5 > rem 2), filtered with BUDGET_EXCEEDED
    a_trace = [e for e in res["trace"] if e["node_id"] == "A" and e["day"] == 10][0]
    assert a_trace["decision"] == "FILTERED"
    assert a_trace["reason_code"] == ReasonCode.BUDGET_EXCEEDED.value

    # B was selected
    b_trace = [e for e in res["trace"] if e["node_id"] == "B" and e["day"] == 10][0]
    assert b_trace["decision"] == "SELECTED"
    assert b_trace["reason_code"] == ReasonCode.SELECTED.value


def test_review_deferred_when_budget_is_short():
    """
    A due review that does not fit into leftover budget is filtered with BUDGET_EXCEEDED.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=4, base_difficulty=0.5)
    g.add_node("B", baseline_duration=7, base_difficulty=0.5)
    g.add_edge("A", "B")

    states = {
        "A": make_mastered_state(),
        "B": ConceptState.cold_start(),
    }

    rl = ReviewLog()
    rl.record_attempt("A", time_in_days=1.0, correct=True)

    cand_univ = get_candidate_universe(g, "B")
    past_days = []
    past_trace = []
    for d in range(1, 6):
        past_days.append({
            "day": d,
            "activities": ["A"] if d == 1 else [],
            "conditional_activities": [],
            "minutes_used": 4 if d == 1 else 0,
            "minutes_remaining": 6 if d == 1 else 10,
            "missed": (d > 1),
        })
        for nid in sorted(list(cand_univ)):
            st = states[nid]
            past_trace.append({
                "node_id": nid,
                "day": d,
                "concept_state": {"p": st.p, "kappa": st.kappa, "sigma2": st.sigma2, "n": st.n, "class": st.classify()},
                "constraints": {"budget": 10, "remaining_budget": 6 if (d == 1 and nid == "A") else 10, "prerequisites": {}},
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

    res = replan(state, assessment_result("B", [1]))

    day6 = [d for d in res["days"] if d["day"] == 6][0]
    assert day6["activities"] == ["B"]
    assert day6["minutes_remaining"] == 3  # leftover 3 < A duration 4

    a_entry = [e for e in res["trace"] if e["node_id"] == "A" and e["day"] == 6][0]
    assert a_entry["decision"] == "FILTERED"
    assert a_entry["reason_code"] == ReasonCode.BUDGET_EXCEEDED.value

    assert check_trace(cand_univ, res["trace"], num_days=6, budget=10) is True


def test_k_failures_trigger_remediation_and_k_minus_1_do_not():
    """
    k consecutive failures trigger prerequisite remediation, while k-1 do not.
    With k=2:
    - 1 failure: consecutive_failures = 1 < 2 -> no remediation.
    - 2 failures: consecutive_failures = 2 >= 2 -> remediation triggered.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=3, base_difficulty=0.5)
    g.add_node("B", baseline_duration=3, base_difficulty=0.5)
    g.add_node("C", baseline_duration=3, base_difficulty=0.5)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    states = {
        "A": make_mastered_state(),
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

    # 1 failure (k-1): consecutive failures = 1
    res1 = replan(state, assessment_result("C", [0]))
    assert res1["review_log"].get_consecutive_failures("C") == 1
    # B was not scheduled with REMEDIATION_TRIGGERED
    b_trace1 = [e for e in res1["trace"] if e["node_id"] == "B" and e["day"] == 1][0]
    assert b_trace1["reason_code"] != ReasonCode.REMEDIATION_TRIGGERED.value

    # 2nd failure (reaching k=2)
    state2 = {
        "graph": g,
        "learner_states": res1["learner_states"],
        "difficulty_states": res1["difficulty_states"],
        "review_log": res1["review_log"],
        "budget": 10,
        "deadline_days": 2,
        "target_node": "C",
        "current_day": 1,
    }
    res2 = replan(state2, assessment_result("C", [0]))
    assert res2["review_log"].get_consecutive_failures("C") == 2

    # Prerequisite remediation triggered for unmastered ancestor B!
    b_trace2 = [e for e in res2["trace"] if e["node_id"] == "B" and e["day"] == 1][0]
    assert b_trace2["decision"] == "SELECTED"
    assert b_trace2["reason_code"] == ReasonCode.REMEDIATION_TRIGGERED.value
    assert res2["days"][0]["activities"][0] == "B"


def test_remediation_inside_same_daily_budget():
    """
    Remediation of unmastered ancestors is scheduled first inside the same daily budget.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=3, base_difficulty=0.5)
    g.add_node("B", baseline_duration=3, base_difficulty=0.5)
    g.add_node("C", baseline_duration=3, base_difficulty=0.5)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    # A is Mastered; B is cold start; C is cold start
    states = {
        "A": make_mastered_state(),
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

    # C fails 2 assessments -> triggers remediation of B
    res = replan(state, assessment_result("C", [0, 0]))

    day1 = res["days"][0]
    # B (duration 3) is scheduled first inside budget of 10
    assert day1["activities"][0] == "B"
    assert day1["minutes_used"] >= 3

    cand_univ = get_candidate_universe(g, "C")
    assert check_trace(cand_univ, res["trace"], num_days=2, budget=10) is True


def test_remediation_cannot_fit_returns_structured_reason():
    """
    When remediation cannot fit in the daily budget, replan returns a structured outcome
    with a supported reason code, never a silent drop.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=3, base_difficulty=0.5)
    # Ancestor B has duration 15, exceeding daily budget of 10
    g.add_node("B", baseline_duration=15, base_difficulty=0.5)
    g.add_node("C", baseline_duration=3, base_difficulty=0.5)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    states = {
        "A": make_mastered_state(),
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

    # C fails twice -> triggers remediation for B
    res = replan(state, assessment_result("C", [0, 0]))

    # B duration 15 exceeds daily budget 10 -> INFEASIBLE_PROVED with BLOCK_EXCEEDS_DAILY_BUDGET
    assert res["status"] == FeasibilityStatus.INFEASIBLE_PROVED
    assert res["trace"]["reason_code"] == ReasonCode.BLOCK_EXCEEDS_DAILY_BUDGET.value
    assert check_no_plan_trace(res["trace"]) is True


def test_every_new_trace_passes_check_trace():
    """
    Verifies that traces containing REVIEW_DUE and REMEDIATION_TRIGGERED pass check_trace.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=2, base_difficulty=0.5)
    g.add_node("B", baseline_duration=2, base_difficulty=0.5)
    g.add_node("C", baseline_duration=2, base_difficulty=0.5)
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    states = {
        "A": make_mastered_state(),
        "B": ConceptState.cold_start(),
        "C": ConceptState.cold_start(),
    }

    rl = ReviewLog()
    rl.record_attempt("A", time_in_days=1.0, correct=True)

    cand_univ = get_candidate_universe(g, "C")
    past_days = []
    past_trace = []
    for d in range(1, 6):
        past_days.append({
            "day": d,
            "activities": ["A"] if d == 1 else [],
            "conditional_activities": [],
            "minutes_used": 2 if d == 1 else 0,
            "minutes_remaining": 8 if d == 1 else 10,
            "missed": (d > 1),
        })
        for nid in sorted(list(cand_univ)):
            st = states[nid]
            past_trace.append({
                "node_id": nid,
                "day": d,
                "concept_state": {"p": st.p, "kappa": st.kappa, "sigma2": st.sigma2, "n": st.n, "class": st.classify()},
                "constraints": {"budget": 10, "remaining_budget": 8 if (d == 1 and nid == "A") else 10, "prerequisites": {}},
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
        "target_node": "C",
        "current_day": 6,
        "review_log": rl,
        "past_days": past_days,
        "past_trace": past_trace,
    }

    # C fails 2 assessments on day 6 -> triggers remediation of B; A is due for review
    res = replan(state, assessment_result("C", [0, 0]))

    # Trace includes REMEDIATION_TRIGGERED for B and REVIEW_DUE for A
    trace_b = [e for e in res["trace"] if e["node_id"] == "B" and e["day"] == 6][0]
    trace_a = [e for e in res["trace"] if e["node_id"] == "A" and e["day"] == 6][0]
    assert trace_b["decision"] == "SELECTED"
    assert trace_b["reason_code"] == ReasonCode.REMEDIATION_TRIGGERED.value
    assert trace_a["decision"] == "SELECTED"
    assert trace_a["reason_code"] == ReasonCode.REVIEW_DUE.value

    assert check_trace(cand_univ, res["trace"], num_days=6, budget=10) is True


def test_timestamps_recorded_in_review_log():
    """
    ReviewLog accurately records simulated days since plan start across assessment events.
    """
    rl = ReviewLog()
    rl.record_attempt("C1", time_in_days=1.0, correct=True)
    rl.record_attempt("C1", time_in_days=3.5, correct=False)
    rl.record_attempt("C1", time_in_days=5.0, correct=False)

    records = rl.get_records("C1")
    assert len(records) == 3
    assert records[0].time_in_days == 1.0
    assert records[0].correct is True
    assert records[1].time_in_days == 3.5
    assert records[1].correct is False
    assert records[2].time_in_days == 5.0
    assert records[2].correct is False

    assert rl.get_last_review_time("C1") == 5.0
    assert rl.get_consecutive_failures("C1") == 2
