"""W7 A1: best-singleton fallback for the greedy scheduler (docs/w7/preregistration.md)."""
import pytest

from src.planning.greedy import run_greedy_scheduler
from src.planning.oracle import run_exhaustive_oracle



def _item(node_id, duration, score, prerequisites=None):
    return {"node_id": node_id, "duration": duration, "score": score, "prerequisites": prerequisites or []}


def test_12_18_counterexample_stays_at_12():
    from src.planning.greedy_fallback import best_single_score, run_greedy_best_singleton

    items = [_item("item_1", 6, 12), _item("item_2", 5, 9), _item("item_3", 5, 9)]
    assert run_greedy_scheduler(items, 10) == 12
    assert best_single_score(items, 10) == 12.0
    assert run_greedy_best_singleton(items, 10) == 12
    assert run_exhaustive_oracle(items, 10) == 18


def test_single_large_item_beats_greedy():
    from src.planning.greedy_fallback import best_singleton_fallback, run_greedy_best_singleton

    items = [_item("a", 1, 2), _item("b", 10, 10)]
    assert run_greedy_scheduler(items, 10) == 2
    assert run_greedy_best_singleton(items, 10) == 10
    assert run_exhaustive_oracle(items, 10) == 10
    assert best_singleton_fallback(["a"], items, 10) == ["b"]


def test_unmet_prerequisites_never_single_pick():
    from src.planning.greedy_fallback import best_single_score, best_singleton_fallback

    items = [_item("a", 2, 1), _item("b", 3, 50, prerequisites=["z"])]
    assert best_single_score(items, 10) == 1.0
    assert best_singleton_fallback([], items, 10) == ["a"]
    # Prerequisite met through mastered_set makes it admissible.
    assert best_single_score(items, 10, mastered_set={"z"}) == 50.0
    # Over-budget item is never the single pick either.
    assert best_single_score([_item("c", 11, 99)], 10) == 0.0


def test_tie_keeps_greedy_picks():
    from src.planning.greedy_fallback import best_singleton_fallback, run_greedy_best_singleton

    items = [_item("a", 1, 5), _item("b", 1, 5), _item("c", 10, 10)]
    assert run_greedy_scheduler(items, 10) == 10
    assert best_singleton_fallback(["a", "b"], items, 10) == ["a", "b"]
    assert run_greedy_best_singleton(items, 10) == 10


def test_single_pick_tie_break_order():
    from src.planning.greedy_fallback import best_singleton_fallback

    # Same score: lower duration wins; same score and duration: lower node_id wins.
    items = [_item("z", 9, 10), _item("y", 8, 10), _item("x", 8, 10), _item("w", 1, 1)]
    assert best_singleton_fallback(["w"], items, 10) == ["x"]


def test_no_items():
    from src.planning.greedy_fallback import (
        best_single_score,
        best_singleton_fallback,
        run_greedy_best_singleton,
    )

    assert best_single_score([], 10) == 0.0
    assert best_singleton_fallback([], [], 10) == []
    assert run_greedy_best_singleton([], 10) == 0.0
