import pytest
from src.planning.oracle import run_exact_dp_oracle


@pytest.mark.xfail(strict=True, reason="Defect 1: Oracle result depends on input order")
def test_oracle_order_independence():
    """Defect 1: run_exact_dp_oracle returns suboptimal score when prerequisites appear after dependent items."""
    budget = 20
    item_a = {"node_id": "A", "duration": 10, "score": 10, "prerequisites": []}
    item_b = {"node_id": "B", "duration": 10, "score": 20, "prerequisites": ["A"]}

    score_ab = run_exact_dp_oracle([item_a, item_b], budget)
    score_ba = run_exact_dp_oracle([item_b, item_a], budget)

    assert score_ab == 30
    assert score_ba == 30
