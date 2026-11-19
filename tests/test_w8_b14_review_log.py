"""W8 B14 fix: replan() must not log the reviews it plans as done.

Before the fix, packing a due review into a future day wrote a correct attempt at that
day into the shared ReviewLog, so a later replan or a missed day dropped the review
(docs/final/LIMITATIONS.md B14; scripts/w8_b14_planned_reviews.py).
"""
import networkx as nx

from src.planning.replan import ReplanState, assessment_result, changed_deadline, missed_day, replan
from src.planning.review import ReviewLog
from src.state.learner_state import ConceptState


def _start():
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=10, base_difficulty=0.3)
    g.add_node("T", baseline_duration=10, base_difficulty=0.5)
    g.add_edge("A", "T", importance=1.0)
    a = ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1])
    assert a.classify() == "Mastered"
    rl = ReviewLog()
    rl.record_attempt("A", time_in_days=1.0, correct=True)
    st = ReplanState(graph=g, learner_states={"A": a, "T": ConceptState.cold_start()}, budget=20,
                     deadline_days=20, target_node="T", current_day=2, review_log=rl)
    st.completed_nodes = {"A"}
    plan = replan(st, assessment_result("T", [1]))
    st.learner_states, st.review_log = plan["learner_states"], plan["review_log"]
    return st, plan


def _reviews(plan):
    return [d["day"] for d in plan["days"] if "A" in d.get("activities", [])]


def test_planned_reviews_are_not_logged_as_done():
    st, plan = _start()
    assert _reviews(plan) == [5, 9, 13, 17]  # still planned, spaced, not every day
    assert [r.time_in_days for r in plan["review_log"].get_records("A")] == [1.0]  # only real practice
    # the answered event itself is still recorded
    assert [r.time_in_days for r in plan["review_log"].get_records("T")] == [2.0]


def test_replan_keeps_planned_reviews():
    st, _ = _start()
    st.current_day = 3
    plan = replan(st, changed_deadline(20))
    assert _reviews(plan) == [5, 9, 13, 17]


def test_review_comes_back_after_missed_days():
    st, _ = _start()
    past = []
    for day in range(3, 9):
        st.current_day = day
        plan = replan(st, missed_day())
        st.learner_states, st.review_log = plan["learner_states"], plan["review_log"]
        past.append({"day": day, "activities": [], "missed": True})
        st.past_days = list(past)
    st.current_day = 9
    plan = replan(st, changed_deadline(20))
    assert 9 in _reviews(plan)  # recall 2^(-8/14) = 0.673 < 0.85: due on day 9
