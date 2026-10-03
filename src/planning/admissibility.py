from typing import Set, Dict, Any, Optional
import networkx as nx


def is_admissible(
    activity: Dict[str, Any],
    selected_set: Set[str],
    mastered_set: Set[str],
    remaining_budget: int,
    g: Optional[nx.DiGraph] = None
) -> bool:
    """
    Evaluates whether an activity block is admissible for scheduling on a given day.

    An activity is admissible iff:
    1. Its duration is <= remaining daily budget.
    2. All of its mandatory prerequisite activities are present in selected_set or mastered_set.
    """
    node_id = activity.get("node_id") or activity.get("id")
    dur = activity.get("duration") if "duration" in activity else activity.get("baseline_duration", 0)

    if dur > remaining_budget:
        return False

    if g is not None and node_id in g:
        prereqs = set(g.predecessors(node_id))
    else:
        prereqs = set(activity.get("prerequisites", []))

    unmet = prereqs - (selected_set | mastered_set)
    return len(unmet) == 0
