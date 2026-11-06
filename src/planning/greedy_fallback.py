"""Best-singleton fallback for the score-per-minute greedy scheduler.

Week 7 opt-in improvement, specified in docs/w7/preregistration.md.
Greedy by density can lose badly when one large item is worth more than the
whole greedy packing; taking the better of greedy and the best single
admissible item removes that failure mode. src/planning/greedy.py is unchanged.
"""
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from src.planning.admissibility import is_admissible
from src.planning.greedy import run_greedy_scheduler


def _normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalise item fields exactly as run_greedy_scheduler does."""
    normalized = []
    for idx, item in enumerate(items):
        node_id = item.get("node_id") or item.get("id", f"item_{idx}")
        dur = item.get("duration") if "duration" in item else item.get("baseline_duration", 0)
        normalized.append({
            "node_id": str(node_id),
            "duration": int(dur),
            "score": float(item.get("score", 0)),
            "prerequisites": item.get("prerequisites", []),
        })
    return normalized


def _best_single_item(
    normalized: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None,
) -> Optional[Dict[str, Any]]:
    """Best item admissible with an empty selected set.

    Preference: higher score, then lower duration, then lower node_id.
    """
    mastered = set() if mastered_set is None else mastered_set
    admissible = [it for it in normalized if is_admissible(it, set(), mastered, budget, g)]
    if not admissible:
        return None
    return min(admissible, key=lambda it: (-it["score"], it["duration"], it["node_id"]))


def best_single_score(
    items: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None,
) -> float:
    """Highest score of one item admissible with an empty selected set; 0.0 if none."""
    best = _best_single_item(_normalize_items(items), budget, mastered_set, g)
    return 0.0 if best is None else float(best["score"])


def run_greedy_best_singleton(
    items: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None,
) -> float:
    """max(run_greedy_scheduler(...), best_single_score(...))."""
    greedy = run_greedy_scheduler(items, budget, mastered_set, g)
    single = best_single_score(items, budget, mastered_set, g)
    return float(max(greedy, single))


def best_singleton_fallback(
    greedy_picks: List[str],
    items: List[Dict[str, Any]],
    budget: int,
) -> List[str]:
    """[best single node_id] if its score is strictly greater than the summed
    score of greedy_picks, else greedy_picks unchanged (ties keep greedy)."""
    normalized = _normalize_items(items)
    best = _best_single_item(normalized, budget)
    if best is None:
        return greedy_picks
    score_by_id = {it["node_id"]: it["score"] for it in normalized}
    greedy_total = sum(score_by_id.get(str(nid), 0.0) for nid in greedy_picks)
    if best["score"] > greedy_total:
        return [best["node_id"]]
    return greedy_picks
