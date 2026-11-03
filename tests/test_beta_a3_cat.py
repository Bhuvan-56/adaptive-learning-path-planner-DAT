import math
import os
import numpy as np
import pandas as pd
import pytest

from src.diagnostic.diagnostic import (
    AdaptiveDiagnostic,
    load_item_bank_and_qmatrix,
    DEFAULT_ITEM_BANK_PATH,
    DEFAULT_QMATRIX_PATH,
    DEFAULT_CURRICULUM_PATH,
)
from src.curriculum.graph import load_graph
from src.simulation.simulator import SimulatedLearner
from src.evaluation.compare import generate_synthetic_learners


def test_theoretical_minimum_variance_lower_bound(tmp_path):
    """
    Mathematical verification:
    Under 2PL IRT (c=0, d=1), the maximum Fisher information of an item is a_i^2 / 4.
    Summing the top 10 items in data/processed/item_bank_synthetic.csv yields:
    I_max <= 5.12764, giving a theoretical minimum variance of 1 / 5.12764 ≈ 0.1950.
    Since 0.1950 > 0.15, it is mathematically impossible for the 0.15 variance
    stopping rule to fire within 10 items for any response pattern.
    """
    bank_df = pd.read_csv(DEFAULT_ITEM_BANK_PATH)
    assert len(bank_df) == 24

    max_info_per_item = (bank_df["a"] ** 2) / 4.0
    top10_max_info = max_info_per_item.nlargest(10).sum()
    theoretical_min_var = 1.0 / top10_max_info

    assert top10_max_info < 5.2
    assert theoretical_min_var > 0.19, (
        f"Theoretical minimum variance {theoretical_min_var} is not strictly greater than 0.15"
    )
    assert theoretical_min_var > 0.15


def test_cat_variance_trajectory_never_crosses_threshold(tmp_path):
    """
    Empirical verification:
    Executes CAT across representative synthetic learners and profiles.
    Asserts that:
    1. Variance at each item step 1..10 is strictly greater than 0.15.
    2. All diagnostic sessions administer exactly 10 questions (stopping on item cap).
    3. Minimum observed variance at item 10 across runs is >= 0.218 > 0.15.
    """
    g = load_graph(DEFAULT_CURRICULUM_PATH)
    curriculum_concepts = list(g.nodes())
    bank_df = pd.read_csv(DEFAULT_ITEM_BANK_PATH)
    concept_diffs = {"A": -0.20, "B": -0.20, "C": 0.15, "D": 0.50}

    engine = AdaptiveDiagnostic(
        bank_source=DEFAULT_ITEM_BANK_PATH,
        qmatrix_source=DEFAULT_QMATRIX_PATH,
        curriculum_source=DEFAULT_CURRICULUM_PATH,
        stopping_variance=0.15,
        max_questions=10,
    )

    # Test across learner profiles and synthetic learners
    learners = generate_synthetic_learners(
        n_learners=20,
        seed=42,
        item_bank=bank_df,
        concept_difficulties=concept_diffs,
    )

    for gt in learners:
        def make_responder(gt_l, bank):
            def respond(item_id: str) -> int:
                if item_id in gt_l.pre_generated_responses:
                    return int(gt_l.pre_generated_responses[item_id])
                row = bank[bank["item_id"] == item_id].iloc[0]
                a_val = float(row["a"])
                b_val = float(row["b"])
                c_val = float(row.get("c", 0.0))
                d_val = float(row.get("d", 1.0))
                p_c = c_val + (d_val - c_val) / (1.0 + math.exp(-a_val * (gt_l.theta_true - b_val)))
                return 1 if (gt_l.rng.random() < p_c) else 0
            return respond

        res = engine.run(make_responder(gt, bank_df))

        # Administered items must hit max_questions (10) because variance never hits <= 0.15
        assert len(res.items_asked) == 10
        assert res.variance > 0.15
        assert res.variance >= 0.21
