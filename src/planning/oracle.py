import time
from typing import List, Dict, Any, Set, Optional
import networkx as nx

from src.planning.admissibility import is_admissible


def run_exact_dp_oracle(
    items: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None,
    timeout_seconds: float = 2.0
) -> int:
    """
    Exact dynamic programming / exhaustive oracle for single-day schedule optimization.
    Finds maximum achievable score over precedence-closed subsets of duration <= budget.

    Hard cap at 20 activities and per-instance timeout to protect CI.
    """
    if len(items) > 20:
        raise ValueError(f"Oracle hard cap exceeded: {len(items)} items > 20 item cap.")

    if mastered_set is None:
        mastered_set = set()

    normalized_items = []
    for idx, item in enumerate(items):
        node_id = str(item.get("node_id") or item.get("id", f"item_{idx}"))
        dur = int(item.get("duration") if "duration" in item else item.get("baseline_duration", 0))
        score = float(item.get("score", 0))
        prereqs = item.get("prerequisites", [])
        normalized_items.append({
            "node_id": node_id,
            "duration": dur,
            "score": score,
            "prerequisites": prereqs,
            "raw": item
        })

    n = len(normalized_items)
    start_time = time.time()
    max_score = 0.0

    # Exhaustive search over valid precedence-closed combinations
    # Since n <= 20, bitmask / recursive search with memoization or subset search is ultra fast
    def search(idx: int, current_selected: Set[str], current_budget: int, current_score: float):
        nonlocal max_score
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Oracle execution timed out.")

        if current_score > max_score:
            max_score = current_score

        for i in range(idx, n):
            item = normalized_items[i]
            node_id = item["node_id"]
            if node_id not in current_selected:
                if is_admissible(item, current_selected, mastered_set, current_budget, g):
                    current_selected.add(node_id)
                    search(
                        i + 1,
                        current_selected,
                        current_budget - item["duration"],
                        current_score + item["score"]
                    )
                    current_selected.remove(node_id)

    search(0, set(), budget, 0.0)
    return int(round(max_score))
