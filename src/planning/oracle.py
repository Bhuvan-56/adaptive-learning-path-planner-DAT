import time
from typing import List, Dict, Any, Set, Optional
import networkx as nx

from src.planning.admissibility import is_admissible


def run_exhaustive_oracle(
    items: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None,
    timeout_seconds: float = 2.0
) -> int:
    """
    Exhaustive oracle for single-day schedule optimization.
    Finds maximum achievable score over precedence-closed subsets of duration <= budget,
    independent of the input list order.

    Hard cap at 20 activities and per-instance timeout to protect CI.
    """
    if len(items) > 20:
        raise ValueError(f"Oracle hard cap exceeded: {len(items)} items > 20 item cap.")

    if mastered_set is None:
        mastered_set = set()

    start_time = time.time()

    # Normalize items
    normalized_items = []
    for idx, item in enumerate(items):
        node_id = str(item.get("node_id") or item.get("id", f"item_{idx}"))
        dur = int(item.get("duration") if "duration" in item else item.get("baseline_duration", 0))
        score = float(item.get("score", 0))
        if g is not None and node_id in g:
            prereqs = set(g.predecessors(node_id))
        else:
            prereqs = set(item.get("prerequisites", []))
        normalized_items.append({
            "node_id": node_id,
            "duration": dur,
            "score": score,
            "prerequisites": prereqs,
            "raw": item
        })

    # Build dependency graph among input items to find topological ordering for search
    item_nids = {it["node_id"] for it in normalized_items}
    dep_graph = nx.DiGraph()
    for it in normalized_items:
        dep_graph.add_node(it["node_id"])
    for it in normalized_items:
        for p in it["prerequisites"]:
            if p in item_nids:
                dep_graph.add_edge(p, it["node_id"])

    try:
        topo_order = list(nx.topological_sort(dep_graph))
        order_map = {nid: i for i, nid in enumerate(topo_order)}
        sorted_items = sorted(normalized_items, key=lambda it: order_map[it["node_id"]])
    except nx.NetworkXUnfeasible:
        sorted_items = normalized_items

    n = len(sorted_items)
    # Precompute suffix score sums for branch-and-bound pruning
    suffix_scores = [0.0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_scores[i] = suffix_scores[i + 1] + max(0.0, sorted_items[i]["score"])

    max_score = 0.0

    def search(idx: int, selected_set: Set[str], cur_budget: int, cur_score: float):
        nonlocal max_score
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Oracle execution timed out.")

        if cur_score > max_score:
            max_score = cur_score

        if idx == n or cur_score + suffix_scores[idx] <= max_score:
            return

        item = sorted_items[idx]
        nid = item["node_id"]
        dur = item["duration"]

        # Check admissibility: fits within remaining budget and all prerequisites satisfied
        can_include = (dur <= cur_budget) and item["prerequisites"].issubset(selected_set | mastered_set)

        # Branch 1: include item
        if can_include:
            selected_set.add(nid)
            search(
                idx + 1,
                selected_set,
                cur_budget - dur,
                cur_score + item["score"]
            )
            selected_set.remove(nid)

        # Branch 2: exclude item
        search(
            idx + 1,
            selected_set,
            cur_budget,
            cur_score
        )

    search(0, set(), budget, 0.0)
    return int(round(max_score))


def run_exact_dp_oracle(
    items: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None,
    timeout_seconds: float = 2.0
) -> int:
    """
    Deprecated alias for run_exhaustive_oracle.
    Retained for backward compatibility.
    """
    return run_exhaustive_oracle(
        items=items,
        budget=budget,
        mastered_set=mastered_set,
        g=g,
        timeout_seconds=timeout_seconds
    )
