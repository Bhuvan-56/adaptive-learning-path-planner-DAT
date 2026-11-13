"""W8 fix 4 (LIMITATIONS.md B11): due reviews are packed into the leftover budget by
priority = (1 - recall) * w, where w is the largest edge importance from the concept
to a not-yet-mastered dependent (1.0 if there is none). Threshold, decay model and
budget rule are unchanged; review decisions carry recall, weight and priority."""
import networkx as nx
import pytest

from src.planning import review
from src.planning.replan import assessment_result, replan
from src.planning.review import ReviewLog, calculate_recall_decay
from src.state.learner_state import ConceptState
from src.trace.checker import check_trace
from src.trace.schema import ReasonCode
from src.trace.universe import get_candidate_universe


def _mastered():
    s = ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1])
    assert s.classify() == "Mastered"
    return s


def _plan(reviews, budget, target_dur=4, review_dur=4):
    """reviews: {concept: (days_since_last_review, importance of its edge to target T)}.
    One planning day (day 1); past reviews are logged before plan start (negative time)."""
    g = nx.DiGraph()
    g.add_node("T", baseline_duration=target_dur, base_difficulty=0.5)
    states = {"T": ConceptState.cold_start()}
    rl = ReviewLog()
    for c, (dt, imp) in reviews.items():
        g.add_node(c, baseline_duration=review_dur, base_difficulty=0.5)
        g.add_edge(c, "T", importance=imp)
        states[c] = _mastered()
        rl.record_attempt(c, time_in_days=1.0 - dt, correct=True)
    state = {"graph": g, "learner_states": states, "budget": budget, "deadline_days": 1,
             "target_node": "T", "current_day": 1, "review_log": rl}
    res = replan(state, assessment_result("T", [1]))
    day = res["days"][0]
    entries = {e["node_id"]: e for e in res["trace"] if e["day"] == 1}
    return g, res, day, entries


def test_equal_recall_higher_importance_is_reviewed():
    # Equal recall; budget 8 fits T (4) and one review (4). X sorts first by name.
    g, res, day, e = _plan({"X": (9.0, 0.3), "Y": (9.0, 0.9)}, budget=8)
    assert day["activities"] == ["T", "Y"]
    assert e["Y"]["decision"] == "SELECTED" and e["Y"]["reason_code"] == ReasonCode.REVIEW_DUE.value
    assert e["X"]["decision"] == "FILTERED" and e["X"]["reason_code"] == ReasonCode.BUDGET_EXCEEDED.value
    r = calculate_recall_decay(9.0)
    assert e["X"]["score_terms"]["review_priority"] == pytest.approx((1 - r) * 0.3)
    assert e["Y"]["score_terms"]["review_priority"] == pytest.approx((1 - r) * 0.9)
    assert check_trace(get_candidate_universe(g, "T"), res["trace"], num_days=1, budget=8)


def test_higher_forgetting_risk_outweighs_lower_importance():
    # X: dt 40 -> recall 0.138, priority 0.862 * 0.3 = 0.259
    # Y: dt 4  -> recall 0.820, priority 0.180 * 0.9 = 0.162
    _, _, day, e = _plan({"X": (40.0, 0.3), "Y": (4.0, 0.9)}, budget=8)
    assert e["X"]["score_terms"]["review_priority"] > e["Y"]["score_terms"]["review_priority"]
    assert day["activities"] == ["T", "X"]
    # ... and lower importance wins when the risk gap is small
    _, _, day, _ = _plan({"X": (6.0, 0.3), "Y": (5.0, 0.9)}, budget=8)
    assert day["activities"] == ["T", "Y"]


def test_unit_importances_keep_old_lowest_recall_order():
    reviews = {"P": (8.0, 1.0), "Q": (20.0, 1.0), "R": (8.0, 1.0), "S": (12.0, 1.0)}
    _, _, day, _ = _plan(reviews, budget=4 + 4 * len(reviews))
    old = sorted(reviews, key=lambda c: (calculate_recall_decay(reviews[c][0]), c))
    assert day["activities"] == ["T"] + old  # Q, S, P, R

    g = nx.DiGraph()
    g.add_edge("P", "T", importance=1.0)
    g.add_edge("Q", "T", importance=1.0)
    due = [(0.7, "Q"), (0.6, "P"), (0.7, "A")]
    ranked = review.rank_due_reviews(g, due, mastered=set())
    assert [d["node_id"] for d in ranked] == [nid for _, nid in sorted(due)]


def test_weight_uses_only_not_yet_mastered_dependents():
    g = nx.DiGraph()
    g.add_edge("A", "B", importance=0.9)
    g.add_edge("A", "C", importance=0.4)
    assert review.review_importance_weight(g, "A", mastered=set()) == pytest.approx(0.9)
    assert review.review_importance_weight(g, "A", mastered={"B"}) == pytest.approx(0.4)
    assert review.review_importance_weight(g, "A", mastered={"B", "C"}) == pytest.approx(1.0)
    assert review.review_importance_weight(g, "C", mastered=set()) == pytest.approx(1.0)  # no outgoing


def test_trace_records_recall_importance_and_priority():
    g, res, _, e = _plan({"X": (9.0, 0.3), "Y": (9.0, 0.9)}, budget=8)
    r = calculate_recall_decay(9.0)
    for c, w in (("X", 0.3), ("Y", 0.9)):
        terms = e[c]["score_terms"]
        assert terms["recall"] == pytest.approx(r)
        assert terms["importance_weight"] == pytest.approx(w)
        assert terms["review_priority"] == pytest.approx((1 - r) * w)
        assert e[c]["constraints"]["review_due"] is True
    assert "review_priority" not in e["T"]["score_terms"]
    assert check_trace(get_candidate_universe(g, "T"), res["trace"], num_days=1, budget=8)
