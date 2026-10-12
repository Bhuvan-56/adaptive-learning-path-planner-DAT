from typing import Set, Dict, Any, Optional
import networkx as nx


def is_admissible(
    activity: Dict[str, Any],
    selected_set: Set[str],
    mastered_set: Set[str],
    remaining_budget: int,
    g: Optional[nx.DiGraph] = None,
    planned_set: Optional[Set[str]] = None,
    allow_conditional: bool = False,
    learner_states: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Evaluates whether an activity block is admissible for scheduling on a given day.

    An activity is admissible iff:
    1. Its duration is <= remaining daily budget.
    2. All of its mandatory prerequisite activities are present in:
       - mastered_set (unconditional unlocking), or
       - planned_set (only if allow_conditional is True, e.g. placed conditionally on a later day), or
       - selected_set (for intra-day selections when allow_conditional is not used).
    3. No prerequisite has a failed (Weak) or Uncertain learner state, unless already mastered or planned.
    """
    node_id = activity.get("node_id") or activity.get("id")
    dur = activity.get("duration") if "duration" in activity else activity.get("baseline_duration", 0)

    if dur > remaining_budget:
        return False

    if g is not None and node_id in g:
        prereqs = set(g.predecessors(node_id))
    else:
        prereqs = set(activity.get("prerequisites", []))

    if planned_set is None:
        planned_set = set()

    if learner_states is not None:
        for p in prereqs:
            st = learner_states.get(p)
            if st is not None:
                st_class = st.classify() if hasattr(st, "classify") else (st.get("class") if isinstance(st, dict) else None)
                if st_class == "Weak" and p not in mastered_set:
                    return False
                if st_class == "Uncertain" and p not in mastered_set and (not allow_conditional or p not in planned_set):
                    return False

    if allow_conditional:
        unmet = prereqs - (mastered_set | planned_set)
    else:
        unmet = prereqs - (mastered_set | selected_set)

    return len(unmet) == 0
