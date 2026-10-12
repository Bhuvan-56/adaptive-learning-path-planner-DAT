import itertools
import random
from typing import List, Dict, Any, Set, Optional
import networkx as nx
import pytest

from src.planning.oracle import run_exhaustive_oracle, run_exact_dp_oracle


def bruteforce_reference(
    items: List[Dict[str, Any]],
    budget: int,
    mastered_set: Optional[Set[str]] = None,
    g: Optional[nx.DiGraph] = None
) -> int:
    """
    Independent brute-force reference implementation.
    Iterates all 2^n subsets for n <= 12, filters by precedence-closure and budget,
    and returns the maximum achievable score.
    """
    if mastered_set is None:
        mastered_set = set()

    n = len(items)
    assert n <= 12, "Brute-force reference is designed for n <= 12"

    item_info = []
    for idx, item in enumerate(items):
        nid = str(item.get("node_id") or item.get("id", f"item_{idx}"))
        dur = int(item.get("duration") if "duration" in item else item.get("baseline_duration", 0))
        sc = float(item.get("score", 0))
        if g is not None and nid in g:
            pr = set(g.predecessors(nid))
        else:
            pr = set(item.get("prerequisites", []))
        item_info.append((nid, dur, sc, pr))

    max_score = 0.0

    for r in range(n + 1):
        for combo in itertools.combinations(item_info, r):
            tot_dur = sum(x[1] for x in combo)
            if tot_dur > budget:
                continue

            selected_ids = {x[0] for x in combo}
            # Precedence-closure check: every selected item's prerequisites must be in selected_ids or mastered_set
            valid = True
            for x in combo:
                unmet = x[3] - (selected_ids | mastered_set)
                if unmet:
                    valid = False
                    break

            if valid:
                combo_score = sum(x[2] for x in combo)
                if combo_score > max_score:
                    max_score = combo_score

    return int(round(max_score))


def test_bruteforce_comparison_200_random_instances():
    """Independent check: Compare exhaustive oracle with brute force on 200 random instances."""
    rng = random.Random(20261012)
    agreements = 0

    for inst_idx in range(200):
        n_items = rng.randint(1, 10)
        budget = rng.choice([5, 10, 15, 30])
        nodes = [f"node_{i}" for i in range(n_items)]
        items = []

        for i, nid in enumerate(nodes):
            dur = rng.randint(1, 15)
            sc = rng.randint(1, 50)
            pr = [nodes[j] for j in range(i) if rng.random() < 0.35]
            items.append({
                "node_id": nid,
                "duration": dur,
                "score": sc,
                "prerequisites": pr
            })

        # Randomize input list order
        rng.shuffle(items)

        bf_score = bruteforce_reference(items, budget)
        oracle_score = run_exhaustive_oracle(items, budget)
        alias_score = run_exact_dp_oracle(items, budget)

        assert oracle_score == bf_score, (
            f"Instance {inst_idx} mismatch: oracle={oracle_score}, bf={bf_score}"
        )
        assert alias_score == bf_score
        agreements += 1

    assert agreements == 200


def test_permutations_two_item_example():
    """Verify agreement across all permutations of the two-item dependency example."""
    item_a = {"node_id": "A", "duration": 10, "score": 10, "prerequisites": []}
    item_b = {"node_id": "B", "duration": 10, "score": 20, "prerequisites": ["A"]}

    for perm in itertools.permutations([item_a, item_b]):
        items = list(perm)
        bf_score = bruteforce_reference(items, 20)
        oracle_score = run_exhaustive_oracle(items, 20)
        assert bf_score == 30
        assert oracle_score == 30


def test_permutations_four_item_branching_case():
    """Verify agreement across all permutations of 4-item branching case (A->B, A->C, B&C->D)."""
    items_4 = [
        {"node_id": "A", "duration": 5, "score": 10, "prerequisites": []},
        {"node_id": "B", "duration": 5, "score": 15, "prerequisites": ["A"]},
        {"node_id": "C", "duration": 5, "score": 20, "prerequisites": ["A"]},
        {"node_id": "D", "duration": 5, "score": 30, "prerequisites": ["B", "C"]},
    ]

    for budget in [5, 10, 15, 20, 25]:
        for perm in itertools.permutations(items_4):
            items = list(perm)
            bf_score = bruteforce_reference(items, budget)
            oracle_score = run_exhaustive_oracle(items, budget)
            assert oracle_score == bf_score, (
                f"Branching case mismatch at budget {budget}: oracle={oracle_score}, bf={bf_score}"
            )


def test_oracle_hard_cap_raises_value_error():
    """Verifies that 21 items raises ValueError due to the N <= 20 cap."""
    items = [{"node_id": f"item_{i}", "duration": 1, "score": 1} for i in range(21)]
    with pytest.raises(ValueError, match="Oracle hard cap exceeded: 21 items > 20 item cap."):
        run_exhaustive_oracle(items, 10)


def test_oracle_timeout_raises_timeout_error():
    """Verifies that exceeding timeout_seconds raises TimeoutError."""
    items = [{"node_id": f"item_{i}", "duration": 1, "score": 1} for i in range(15)]
    with pytest.raises(TimeoutError, match="Oracle execution timed out."):
        run_exhaustive_oracle(items, 10, timeout_seconds=-1.0)


def test_oracle_zero_feasible_items_returns_zero():
    """Verifies that cases with zero feasible items return a score of 0."""
    # Case 1: Empty list
    assert run_exhaustive_oracle([], 10) == 0

    # Case 2: All items exceed budget
    items_too_large = [
        {"node_id": "A", "duration": 15, "score": 20, "prerequisites": []},
        {"node_id": "B", "duration": 25, "score": 30, "prerequisites": []},
    ]
    assert run_exhaustive_oracle(items_too_large, 10) == 0

    # Case 3: Items cannot be scheduled due to unmet missing prerequisites
    items_unmet = [
        {"node_id": "A", "duration": 5, "score": 20, "prerequisites": ["UNMET_PREREQ"]},
    ]
    assert run_exhaustive_oracle(items_unmet, 10) == 0
