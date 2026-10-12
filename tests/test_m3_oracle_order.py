from src.planning.oracle import run_exact_dp_oracle, run_exhaustive_oracle


def test_oracle_order_independence():
    """Defect 1: oracle returns optimal score independent of item input order."""
    budget = 20
    item_a = {"node_id": "A", "duration": 10, "score": 10, "prerequisites": []}
    item_b = {"node_id": "B", "duration": 10, "score": 20, "prerequisites": ["A"]}

    score_ab = run_exact_dp_oracle([item_a, item_b], budget)
    score_ba = run_exact_dp_oracle([item_b, item_a], budget)

    assert score_ab == 30
    assert score_ba == 30

    # Also verify with run_exhaustive_oracle directly
    assert run_exhaustive_oracle([item_a, item_b], budget) == 30
    assert run_exhaustive_oracle([item_b, item_a], budget) == 30
