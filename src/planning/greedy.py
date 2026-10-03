from typing import List, Dict, Any, Set, Optional
import networkx as nx

from src.planning.admissibility import is_admissible


def run_greedy_scheduler(
    items: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None
) -> int:
    """
    Executes score-per-minute greedy scheduler selection for a single daily budget.

    Rank candidates by score/duration descending.
    Tie-breaking precedence: higher score, lower duration, lower node_id.
    Repeatedly picks the top admissible candidate and re-evaluates admissibility after each pick.
    Returns total accumulated score.
    """
    if mastered_set is None:
        mastered_set = set()

    # Pre-format item dict fields for consistency
    normalized_items = []
    for idx, item in enumerate(items):
        node_id = item.get("node_id") or item.get("id", f"item_{idx}")
        dur = item.get("duration") if "duration" in item else item.get("baseline_duration", 0)
        score = item.get("score", 0)
        prereqs = item.get("prerequisites", [])
        normalized_items.append({
            "node_id": str(node_id),
            "duration": int(dur),
            "score": float(score),
            "prerequisites": prereqs,
            "raw": item
        })

    remaining_budget = budget
    selected_set: Set[str] = set()
    total_score = 0.0

    while True:
        # Find all admissible unselected items
        admissible_candidates = []
        for item in normalized_items:
            if item["node_id"] not in selected_set:
                if is_admissible(item, selected_set, mastered_set, remaining_budget, g):
                    density = item["score"] / item["duration"] if item["duration"] > 0 else 0.0
                    admissible_candidates.append((density, item["score"], -item["duration"], item["node_id"], item))

        if not admissible_candidates:
            break

        # Sort by density desc, score desc, duration asc, node_id asc
        # Lexicographical sort on tuple: (-density, -score, duration, node_id)
        admissible_candidates.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
        best_pick = admissible_candidates[0][4]

        selected_set.add(best_pick["node_id"])
        total_score += best_pick["score"]
        remaining_budget -= best_pick["duration"]

    return int(round(total_score))
