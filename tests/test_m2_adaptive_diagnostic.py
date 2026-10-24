"""
Milestone M2: Adaptive Diagnostic Tests (TC-2.1, TC-2.2).
"""

import math
import numpy as np
import pytest

from src.diagnostic.diagnostic import (
    AdaptiveDiagnostic,
    run_adaptive_diagnostic,
    DEFAULT_ITEM_BANK_PATH,
    DEFAULT_QMATRIX_PATH,
    DEFAULT_CURRICULUM_PATH,
    ability_to_prior,
)


def _compute_fisher_info(a: float, b: float, theta: float) -> float:
    """Computes 2PL Fisher Information: a**2 * P * (1 - P)."""
    p = 1.0 / (1.0 + math.exp(-a * (theta - b)))
    return (a ** 2) * p * (1.0 - p)


def test_tc_2_1_incorrect_response_lowers_mastery_and_selects_max_fisher_item():
    """
    TC-2.1: An incorrect response lowers the ability estimate, and the next item
    is the maximum Fisher-information item at the new estimate.
    """
    diagnostic = AdaptiveDiagnostic(
        bank_source=DEFAULT_ITEM_BANK_PATH,
        qmatrix_source=DEFAULT_QMATRIX_PATH,
        curriculum_source=DEFAULT_CURRICULUM_PATH,
    )

    catsim_bank = diagnostic.catsim_bank
    initial_theta = 0.0

    # 1. First item selected at initial_theta = 0.0
    item_0_idx = catsim_bank.information(initial_theta).argmax()
    item_0_id = diagnostic.item_ids[item_0_idx]

    # 2. Ingest an incorrect response (0)
    def respond_incorrect(item_id: str) -> int:
        return 0

    # Step through one response manually or via diagnostic components
    estimator = diagnostic.catsim_bank  # verify via catsim estimator
    import catsim.estimation as est
    import catsim.selection as sel
    estimator = est.NumericalSearchEstimator()
    selector = sel.MaxInfoSelector()

    # After incorrect response on item_0_idx
    new_theta = float(
        estimator.estimate(
            item_bank=catsim_bank,
            administered_items=[item_0_idx],
            response_vector=[False],
            est_theta=initial_theta,
        )
    )

    # Assert that incorrect response strictly lowers ability estimate
    assert new_theta < initial_theta, (
        f"Incorrect response did not lower ability estimate: new_theta={new_theta} >= initial_theta={initial_theta}"
    )

    # Assert mapped mastery prior also decreases
    prior_initial = ability_to_prior(initial_theta)
    prior_after = ability_to_prior(new_theta)
    assert prior_after < prior_initial, (
        f"Mastery prior did not decrease: prior_after={prior_after} >= prior_initial={prior_initial}"
    )

    # 3. Next item selected at new_theta
    next_idx = selector.select(
        item_bank=catsim_bank,
        administered_items=[item_0_idx],
        est_theta=new_theta,
    )
    assert next_idx is not None
    assert next_idx != item_0_idx

    # 4. Verify selected item maximizes Fisher information at new_theta among unadministered items
    infos = [
        _compute_fisher_info(row[0], row[1], new_theta) if idx != item_0_idx else -1.0
        for idx, row in enumerate(catsim_bank)
    ]
    expected_max_idx = int(np.argmax(infos))

    assert next_idx == expected_max_idx, (
        f"Next item {next_idx} does not match maximum Fisher info item {expected_max_idx} at theta={new_theta}"
    )
    assert infos[next_idx] >= max(infos) - 1e-9


def test_tc_2_2_diagnostic_terminates_on_variance_or_question_limit():
    """
    TC-2.2: Diagnostic terminates when the variance rule (Var(theta) <= 0.15)
    is satisfied or the question cap (10 items) is reached.
    """
    # ---------------------------------------------------------
    # Case A: Terminates on Question Limit (Cap = 10)
    # ---------------------------------------------------------
    # Alternating responses [0, 1, 0, 1, ...] keep ability oscillating near 0,
    # requiring full test length to reduce variance, reaching the question cap.
    response_counter = 0

    def alternating_responder(item_id: str) -> int:
        nonlocal response_counter
        ans = response_counter % 2
        response_counter += 1
        return ans

    result_capped = run_adaptive_diagnostic(
        respond=alternating_responder,
        bank_source=DEFAULT_ITEM_BANK_PATH,
        qmatrix_source=DEFAULT_QMATRIX_PATH,
        curriculum_source=DEFAULT_CURRICULUM_PATH,
        stopping_variance=0.01,  # Strict variance requirement forces item cap stop
        max_questions=10,
    )

    assert len(result_capped.items_asked) == 10, (
        f"Expected question cap termination at 10 items, got {len(result_capped.items_asked)}"
    )

    # ---------------------------------------------------------
    # Case B: Terminates on Variance Rule (Var(theta) <= 0.15)
    # ---------------------------------------------------------
    # High-information items provide large Fisher information, dropping
    # variance <= 0.15 well before the 10-item cap.
    high_info_bank = [
        {"item_id": f"item_{i:02d}", "a": 2.50, "b": 0.0, "c": 0.0, "d": 1.0}
        for i in range(15)
    ]
    qmatrix_high_info = {f"item_{i:02d}": "A" for i in range(15)}

    def consistent_responder(item_id: str) -> int:
        return 1

    result_var = run_adaptive_diagnostic(
        respond=consistent_responder,
        bank_source=high_info_bank,
        qmatrix_source=qmatrix_high_info,
        curriculum_source=["A", "B", "C", "D"],
        stopping_variance=0.15,
        max_questions=10,
    )

    assert result_var.variance <= 0.15, (
        f"Expected variance <= 0.15, got {result_var.variance}"
    )
    assert len(result_var.items_asked) < 10, (
        f"Expected termination before item cap, got {len(result_var.items_asked)} items"
    )
