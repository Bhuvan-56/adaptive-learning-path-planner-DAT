"""
Tests for computerized adaptive testing (CAT) diagnostic module (Task B3).

Verifies:
1. Stops at item cap (max_questions).
2. Stops at variance rule on a constructed case (variance <= 0.15).
3. Selects maximum-information item for a known ability, verified against hand-computed Fisher information:
   a**2 * P * (1 - P).
4. Determinism: same responses yield identical item sequence.
5. Validation errors:
   - item with no concept (raises with 'concept' named)
   - item mapped to concept not in curriculum (raises with 'concept' named)
   - duplicate item_id (raises with 'item_id' named)
   - non-finite parameter (raises with parameter field named)
6. Cold-start concept states:
   - Concepts with direct items (A, B, C) initialized via init_from_ability(sigmoid(theta_hat))
   - Concepts without items (D) initialized via cold_start()
   - All states classify as Uncertain because n == 0.
7. Architectural boundary: zero imports of src.simulation anywhere under src/diagnostic.
"""

import glob
import math
import os
import pytest
import pandas as pd

from src.diagnostic.diagnostic import (
    AdaptiveDiagnostic,
    DiagnosticResult,
    ability_to_prior,
    load_cat_hyperparameters,
    load_item_bank_and_qmatrix,
    run_adaptive_diagnostic,
    DEFAULT_ITEM_BANK_PATH,
    DEFAULT_QMATRIX_PATH,
    DEFAULT_CURRICULUM_PATH,
)


def _fisher_info_formula(a: float, b: float, theta: float) -> float:
    """Hand-computed Fisher information formula for 2PL model: a**2 * P * (1 - P)."""
    p = 1.0 / (1.0 + math.exp(-a * (theta - b)))
    return (a ** 2) * p * (1.0 - p)


def test_diagnostic_stops_at_item_cap():
    """Diagnostic terminates strictly at max_questions cap when variance remains above threshold."""
    # Strict stopping variance of 0.001 ensures variance condition is not triggered
    counter = 0

    def alternating_respond(item_id: str) -> int:
        nonlocal counter
        ans = counter % 2
        counter += 1
        return ans

    result = run_adaptive_diagnostic(
        respond=alternating_respond,
        bank_source=DEFAULT_ITEM_BANK_PATH,
        qmatrix_source=DEFAULT_QMATRIX_PATH,
        curriculum_source=DEFAULT_CURRICULUM_PATH,
        stopping_variance=0.001,
        max_questions=7,
    )

    assert len(result.items_asked) == 7
    assert result.variance > 0.001


def test_diagnostic_stops_at_variance_rule_constructed_case():
    """
    Diagnostic terminates early on variance rule (<= 0.15) before reaching max_questions.
    Uses constructed bank with high discrimination items (a=2.8) so information accumulates rapidly.
    """
    constructed_bank = [
        {"item_id": f"item_{i:02d}", "a": 2.80, "b": 0.0, "c": 0.0, "d": 1.0}
        for i in range(12)
    ]
    constructed_qmatrix = {f"item_{i:02d}": "A" for i in range(12)}

    def correct_respond(item_id: str) -> int:
        return 1

    result = run_adaptive_diagnostic(
        respond=correct_respond,
        bank_source=constructed_bank,
        qmatrix_source=constructed_qmatrix,
        curriculum_source=["A", "B", "C", "D"],
        stopping_variance=0.15,
        max_questions=10,
    )

    assert result.variance <= 0.15
    assert len(result.items_asked) < 10


def test_diagnostic_selects_max_fisher_information_hand_computed():
    """
    Selects maximum-information item for a known ability, checked against
    hand-computed Fisher information formula a**2 * P * (1 - P) written in the test.
    """
    # Create item bank with 4 known items:
    # item_1: a=1.0, b=0.0
    # item_2: a=2.0, b=1.0
    # item_3: a=1.5, b=-0.5
    # item_4: a=2.5, b=-0.2
    bank_data = [
        {"item_id": "item_1", "a": 1.0, "b": 0.0, "c": 0.0, "d": 1.0},
        {"item_id": "item_2", "a": 2.0, "b": 1.0, "c": 0.0, "d": 1.0},
        {"item_id": "item_3", "a": 1.5, "b": -0.5, "c": 0.0, "d": 1.0},
        {"item_id": "item_4", "a": 2.5, "b": -0.2, "c": 0.0, "d": 1.0},
    ]
    q_data = {f"item_{i}": "A" for i in range(1, 5)}

    test_theta = -0.15

    # Hand compute Fisher info for all items at test_theta using a**2 * P * (1 - P)
    info_map = {}
    for row in bank_data:
        iid = row["item_id"]
        a = row["a"]
        b = row["b"]
        info_map[iid] = _fisher_info_formula(a, b, test_theta)

    best_item = max(info_map.keys(), key=lambda k: info_map[k])

    # Let catsim's MaxInfoSelector select at test_theta
    diagnostic = AdaptiveDiagnostic(
        bank_source=bank_data,
        qmatrix_source=q_data,
        curriculum_source=["A"],
    )

    import catsim.selection as sel
    selector = sel.MaxInfoSelector()
    selected_idx = selector.select(
        item_bank=diagnostic.catsim_bank,
        administered_items=[],
        est_theta=test_theta,
    )
    selected_item_id = diagnostic.item_ids[selected_idx]

    assert selected_item_id == best_item
    # Explicitly check that item_4 has the highest information
    assert selected_item_id == "item_4"
    assert info_map["item_4"] > info_map["item_1"]
    assert info_map["item_4"] > info_map["item_2"]
    assert info_map["item_4"] > info_map["item_3"]


def test_diagnostic_same_responses_give_same_item_sequence():
    """Deterministic repeatability: same response pattern yields identical item sequence."""
    def static_responder_1(item_id: str) -> int:
        return 1 if "1" in item_id or "3" in item_id else 0

    def static_responder_2(item_id: str) -> int:
        return 1 if "1" in item_id or "3" in item_id else 0

    res1 = run_adaptive_diagnostic(
        respond=static_responder_1,
        bank_source=DEFAULT_ITEM_BANK_PATH,
        qmatrix_source=DEFAULT_QMATRIX_PATH,
        curriculum_source=DEFAULT_CURRICULUM_PATH,
        stopping_variance=0.15,
        max_questions=6,
    )
    res2 = run_adaptive_diagnostic(
        respond=static_responder_2,
        bank_source=DEFAULT_ITEM_BANK_PATH,
        qmatrix_source=DEFAULT_QMATRIX_PATH,
        curriculum_source=DEFAULT_CURRICULUM_PATH,
        stopping_variance=0.15,
        max_questions=6,
    )

    assert res1.items_asked == res2.items_asked
    assert math.isclose(res1.theta_hat, res2.theta_hat, abs_tol=1e-9)
    assert math.isclose(res1.variance, res2.variance, abs_tol=1e-9)


def test_diagnostic_validation_errors():
    """
    Validation errors must raise ValueError naming the offending field:
    - Item with no concept in Q-matrix ('concept')
    - Item mapped to unknown curriculum concept ('concept')
    - Duplicate item_id in item bank or Q-matrix ('item_id')
    - Non-finite parameter ('a', 'b', etc.)
    """
    valid_bank = [
        {"item_id": "it_1", "a": 1.2, "b": 0.0, "c": 0.0, "d": 1.0},
        {"item_id": "it_2", "a": 1.5, "b": 0.5, "c": 0.0, "d": 1.0},
    ]
    valid_q = {"it_1": "A", "it_2": "B"}
    curr = ["A", "B", "C", "D"]

    # 1. Item with no concept in Q-matrix
    missing_q = {"it_1": "A"}  # it_2 missing
    with pytest.raises(ValueError, match="concept"):
        AdaptiveDiagnostic(bank_source=valid_bank, qmatrix_source=missing_q, curriculum_source=curr)

    # Empty concept in Q-matrix
    empty_q = {"it_1": "A", "it_2": ""}
    with pytest.raises(ValueError, match="concept"):
        AdaptiveDiagnostic(bank_source=valid_bank, qmatrix_source=empty_q, curriculum_source=curr)

    # 2. Item mapped to concept not in curriculum
    invalid_concept_q = {"it_1": "A", "it_2": "UNKNOWN_CONCEPT"}
    with pytest.raises(ValueError, match="concept"):
        AdaptiveDiagnostic(bank_source=valid_bank, qmatrix_source=invalid_concept_q, curriculum_source=curr)

    # 3. Duplicate item_id in bank
    dup_bank = [
        {"item_id": "it_1", "a": 1.2, "b": 0.0, "c": 0.0, "d": 1.0},
        {"item_id": "it_1", "a": 1.5, "b": 0.5, "c": 0.0, "d": 1.0},
    ]
    with pytest.raises(ValueError, match="item_id"):
        AdaptiveDiagnostic(bank_source=dup_bank, qmatrix_source=valid_q, curriculum_source=curr)

    # 4. Non-finite parameter (NaN, inf)
    nan_bank_a = [
        {"item_id": "it_1", "a": float("nan"), "b": 0.0, "c": 0.0, "d": 1.0},
        {"item_id": "it_2", "a": 1.5, "b": 0.5, "c": 0.0, "d": 1.0},
    ]
    with pytest.raises(ValueError, match="a"):
        AdaptiveDiagnostic(bank_source=nan_bank_a, qmatrix_source=valid_q, curriculum_source=curr)

    inf_bank_b = [
        {"item_id": "it_1", "a": 1.2, "b": float("inf"), "c": 0.0, "d": 1.0},
        {"item_id": "it_2", "a": 1.5, "b": 0.5, "c": 0.0, "d": 1.0},
    ]
    with pytest.raises(ValueError, match="b"):
        AdaptiveDiagnostic(bank_source=inf_bank_b, qmatrix_source=valid_q, curriculum_source=curr)


def test_diagnostic_concept_states_unprobed_uncertain():
    """
    Verifies ADR-009 initialization rules:
    - Concepts with items (A, B, C) receive ConceptState from init_from_ability(sigmoid(theta_hat))
    - Concept without items (D) receives ConceptState from cold_start() (p=0.5, kappa=2.0, n=0)
    - All concept states classify as 'Uncertain' because n == 0 < min_obs.
    """
    def all_ones(item_id: str) -> int:
        return 1

    result = run_adaptive_diagnostic(
        respond=all_ones,
        bank_source=DEFAULT_ITEM_BANK_PATH,
        qmatrix_source=DEFAULT_QMATRIX_PATH,
        curriculum_source=DEFAULT_CURRICULUM_PATH,
        stopping_variance=0.15,
        max_questions=5,
    )

    states = result.concept_states
    assert set(states.keys()) == {"A", "B", "C", "D"}

    expected_p = ability_to_prior(result.theta_hat)

    # Probed concepts A, B, C
    for c in ["A", "B", "C"]:
        cs = states[c]
        assert math.isclose(cs.p, expected_p, abs_tol=1e-6)
        assert cs.kappa == 2.0
        assert cs.n == 0
        assert cs.history == []
        assert cs.classify() == "Uncertain"

    # Unprobed concept D
    cs_d = states["D"]
    assert cs_d.p == 0.50
    assert cs_d.kappa == 2.0
    assert cs_d.n == 0
    assert cs_d.history == []
    assert cs_d.classify() == "Uncertain"


def test_no_simulation_imports_under_diagnostic():
    """
    Architectural boundary audit:
    Modules under src/diagnostic must NEVER import or reference src.simulation,
    SimulatedLearner, or EvaluatorView.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    diag_dir = os.path.join(repo_root, "src", "diagnostic")

    forbidden = [
        "from src.simulation",
        "import src.simulation",
        "import SimulatedLearner",
        "import EvaluatorView",
        "EvaluatorView",
        "SimulatedLearner",
    ]

    violations = []
    for py_file in glob.glob(os.path.join(diag_dir, "**", "*.py"), recursive=True):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
            for pattern in forbidden:
                if pattern in content:
                    violations.append(f"{os.path.relpath(py_file, repo_root)} contains '{pattern}'")

    assert len(violations) == 0, f"Architectural boundary violated: {violations}"
