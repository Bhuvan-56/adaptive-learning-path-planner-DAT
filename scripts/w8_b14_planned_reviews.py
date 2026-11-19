"""Evidence for LIMITATIONS.md B14: replan() logs the reviews it *plans* as done.

src/planning/replan.py, review packing: when a due review is scheduled for a future day,
review_log.record_attempt(r_nid, time_in_days=day_num, correct=True) is called at planning
time ("record review attempt so it won't be immediately due next day"). The shared
ReviewLog then holds future-dated "reviews" that never happened, so any later replan
(missed day, new event) sees a fresh review and drops the review the learner still needs.

Usage: python scripts/w8_b14_planned_reviews.py   (prints the evidence; no engine change)
"""
import os
import sys

import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.planning.replan import ReplanState, assessment_result, changed_deadline, missed_day, replan  # noqa: E402
from src.planning.review import ReviewLog, calculate_recall_decay  # noqa: E402
from src.state.learner_state import ConceptState  # noqa: E402


def graph():
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=10, base_difficulty=0.3)
    g.add_node("T", baseline_duration=10, base_difficulty=0.5)
    g.add_edge("A", "T", importance=1.0)
    return g


def start():
    a = ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1])
    assert a.classify() == "Mastered"
    rl = ReviewLog()
    rl.record_attempt("A", time_in_days=1.0, correct=True)  # the only real practice of A
    st = ReplanState(graph=graph(), learner_states={"A": a, "T": ConceptState.cold_start()}, budget=20,
                     deadline_days=20, target_node="T", current_day=2, review_log=rl)
    st.completed_nodes = {"A"}
    plan = replan(st, assessment_result("T", [1]))
    st.learner_states, st.review_log = plan["learner_states"], plan["review_log"]
    return st, plan


def reviews(plan):
    return [d["day"] for d in plan["days"] if "A" in d.get("activities", [])]


def main():
    out = []
    st, plan = start()
    out.append("Setup: A Mastered, practised once on day 1; target T answered on day 2; budget 20, 20 days.")
    out.append(f"Day-2 plan schedules A reviews on days {reviews(plan)}.")
    out.append(f"ReviewLog for A right after planning: {[r.time_in_days for r in st.review_log.get_records('A')]}"
               " (only day 1 really happened).")

    # Case 1: the learner misses days 3-8.
    past = []
    for day in range(3, 9):
        st.current_day = day
        plan = replan(st, missed_day())
        st.learner_states, st.review_log = plan["learner_states"], plan["review_log"]
        past.append({"day": day, "activities": [], "missed": True})
        st.past_days = list(past)
    st.current_day = 9
    plan = replan(st, changed_deadline(20))
    out.append("")
    out.append("Case 1, missed days 3-8, replan on day 9:")
    out.append(f"  true recall of A on day 9 = {calculate_recall_decay(9 - 1.0):.3f} (< 0.85, so a review is due)")
    out.append(f"  A reviews in the day-9 plan: {reviews(plan)}")

    # Case 2: no missed day, one replan on day 3 before the day-5 review.
    st, plan = start()
    st.current_day = 3
    plan = replan(st, changed_deadline(20))
    out.append("")
    out.append("Case 2, any replan on day 3 (no answers, same deadline):")
    out.append(f"  A reviews in the day-3 plan: {reviews(plan)} (the day-2 plan had them on 5, 9, 13, 17)")
    print("\n".join(out))


if __name__ == "__main__":
    main()
