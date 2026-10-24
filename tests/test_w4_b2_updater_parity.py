"""
Updater Parity Verification (WP10).

This module verifies exact mathematical parity between the runtime concept state updater
(ConceptState.update with PolicyConfig), the online adapter (BKTOnlineAdapter), and the
pyBKT reference model (pyBKT.models.Model).

PROVENANCE STATEMENT:
---------------------
The pyBKT parameters in config/bkt_fitted.yaml are fitted to synthetic data
(specifically data/processed/synthetic_bkt_responses.csv generated for testing
and evaluation). They do NOT represent real-world learner data.

MATHEMATICAL CORRESPONDENCE:
----------------------------
1. ConceptState.update implements standard two-phase Bayesian Knowledge Tracing (BKT):
   - Phase 1 (Evidence Update):
     For outcome Y_t in {0, 1}:
       P(L_t | Y_t = 1) = [P(L_t) * (1 - p_S)] / [P(L_t) * (1 - p_S) + (1 - P(L_t)) * p_G]
       P(L_t | Y_t = 0) = [P(L_t) * p_S]       / [P(L_t) * p_S       + (1 - P(L_t)) * (1 - p_G)]
   - Phase 2 (Learning Transition):
     P(L_{t+1}) = P(L_t | Y_t) + (1 - P(L_t | Y_t)) * p_T
   - In addition, ConceptState tracks:
     kappa_{t+1} = kappa_t + 1.0, n_{t+1} = n_t + 1,
     A_{t+1} = P(L_{t+1}) * kappa_{t+1}, B_{t+1} = (1 - P(L_{t+1})) * kappa_{t+1},
     and trailing outcome history bounded by policy.window_size.

2. BKTOnlineAdapter executes identical two-phase updates with forget == 0.0,
   verified against pyBKT offline predictions in tests/test_m1_bkt_parity.py.

3. Tolerance: Enforced at <= 1e-6 across all sequences without widening.
"""

import os
from typing import List, Dict, Any, Tuple
import pandas as pd
import pytest
from pyBKT.models import Model

from src.state.bkt_adapter import (
    BKTOnlineAdapter,
    DEFAULT_FITTED_CONFIG_PATH,
    load_fitted_bkt_params,
)
from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig


@pytest.fixture(scope="module")
def pybkt_fitted_model():
    """
    Fits pyBKT reference model on training split of synthetic dataset.
    Note: Parameters are fitted to synthetic data.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_path = os.path.join(repo_root, "data", "processed", "synthetic_bkt_responses.csv")
    assert os.path.exists(data_path), f"Synthetic dataset missing: {data_path}"

    df = pd.read_csv(data_path)
    train_df = df[df["user_id"] != "student_10"].copy()

    model = Model(seed=42, num_fits=1, parallel=False)
    model.fit(data=train_df)
    return model


@pytest.fixture(scope="module")
def fitted_policy_and_adapter():
    """Loads fitted policy and BKTOnlineAdapter from config/bkt_fitted.yaml."""
    adapter = BKTOnlineAdapter.from_config(DEFAULT_FITTED_CONFIG_PATH)
    policy = adapter.policy
    return adapter, policy


def _run_pybkt_sequence(model: Model, sequence: List[int], skill_name: str = "Addition") -> List[float]:
    """
    Evaluates response sequence with pyBKT and returns posterior mastery states after each trial.
    pyBKT predict outputs state_predictions entering trial t.
    We append a dummy trial at the end so state_predictions[t+1] gives the posterior after trial t.
    """
    rows = []
    for i, obs in enumerate(sequence):
        rows.append({
            "user_id": "eval_student",
            "skill_name": skill_name,
            "order_id": i + 1,
            "correct": obs,
        })
    # Dummy interaction to obtain posterior after final interaction
    rows.append({
        "user_id": "eval_student",
        "skill_name": skill_name,
        "order_id": len(sequence) + 1,
        "correct": 0,
    })
    test_df = pd.DataFrame(rows)
    preds = model.predict(data=test_df)
    pybkt_states = preds["state_predictions"].tolist()
    # Posteriors after trials 0..len(sequence)-1 are state_predictions[1..len(sequence)]
    return pybkt_states[1:]


# =============================================================================
# 1. ALL CORRECT SEQUENCE
# =============================================================================

def test_updater_parity_all_correct(pybkt_fitted_model, fitted_policy_and_adapter):
    """Verifies parity on an all-correct sequence [1, 1, 1, 1, 1, 1] within 1e-6."""
    _, policy = fitted_policy_and_adapter
    seq = [1, 1, 1, 1, 1, 1]
    pybkt_posteriors = _run_pybkt_sequence(pybkt_fitted_model, seq)

    # Initialize ConceptState and adapter with fitted prior
    init_prior = policy.p_S  # or fitted prior
    fitted_params = load_fitted_bkt_params(DEFAULT_FITTED_CONFIG_PATH)
    prior = fitted_params["prior"]

    cs = ConceptState.init_from_ability(prior)
    cs.policy = policy
    adapter = BKTOnlineAdapter.from_config(DEFAULT_FITTED_CONFIG_PATH)

    max_diff_adapter = 0.0
    max_diff_pybkt = 0.0

    for t, obs in enumerate(seq):
        post_adapter = adapter.update(obs)
        cs.update(obs, policy=policy)
        post_pybkt = pybkt_posteriors[t]

        diff_ad = abs(cs.p - post_adapter)
        diff_py = abs(cs.p - post_pybkt)

        assert diff_ad <= 1e-6, f"Step {t}: ConceptState vs Adapter diff {diff_ad} > 1e-6"
        assert diff_py <= 1e-6, f"Step {t}: ConceptState vs pyBKT diff {diff_py} > 1e-6"

        max_diff_adapter = max(max_diff_adapter, diff_ad)
        max_diff_pybkt = max(max_diff_pybkt, diff_py)

    assert max_diff_adapter <= 1e-6
    assert max_diff_pybkt <= 1e-6


# =============================================================================
# 2. ALL INCORRECT SEQUENCE
# =============================================================================

def test_updater_parity_all_incorrect(pybkt_fitted_model, fitted_policy_and_adapter):
    """Verifies parity on an all-incorrect sequence [0, 0, 0, 0, 0, 0] within 1e-6."""
    _, policy = fitted_policy_and_adapter
    seq = [0, 0, 0, 0, 0, 0]
    pybkt_posteriors = _run_pybkt_sequence(pybkt_fitted_model, seq)

    fitted_params = load_fitted_bkt_params(DEFAULT_FITTED_CONFIG_PATH)
    prior = fitted_params["prior"]

    cs = ConceptState.init_from_ability(prior)
    cs.policy = policy
    adapter = BKTOnlineAdapter.from_config(DEFAULT_FITTED_CONFIG_PATH)

    for t, obs in enumerate(seq):
        post_adapter = adapter.update(obs)
        cs.update(obs, policy=policy)
        post_pybkt = pybkt_posteriors[t]

        assert abs(cs.p - post_adapter) <= 1e-6
        assert abs(cs.p - post_pybkt) <= 1e-6


# =============================================================================
# 3. ALTERNATING SEQUENCE
# =============================================================================

def test_updater_parity_alternating(pybkt_fitted_model, fitted_policy_and_adapter):
    """Verifies parity on alternating observations [1, 0, 1, 0, 1, 0] within 1e-6."""
    _, policy = fitted_policy_and_adapter
    seq = [1, 0, 1, 0, 1, 0]
    pybkt_posteriors = _run_pybkt_sequence(pybkt_fitted_model, seq)

    fitted_params = load_fitted_bkt_params(DEFAULT_FITTED_CONFIG_PATH)
    prior = fitted_params["prior"]

    cs = ConceptState.init_from_ability(prior)
    cs.policy = policy
    adapter = BKTOnlineAdapter.from_config(DEFAULT_FITTED_CONFIG_PATH)

    for t, obs in enumerate(seq):
        post_adapter = adapter.update(obs)
        cs.update(obs, policy=policy)
        post_pybkt = pybkt_posteriors[t]

        assert abs(cs.p - post_adapter) <= 1e-6
        assert abs(cs.p - post_pybkt) <= 1e-6


# =============================================================================
# 4. CROSSING WEAK BOUNDARY (p < 0.40)
# =============================================================================

def test_updater_parity_crossing_weak_boundary(pybkt_fitted_model, fitted_policy_and_adapter):
    """
    Verifies parity on a sequence crossing the Weak boundary (p < 0.40).
    Using sequence [1, 1, 0, 0] starting from fitted prior (0.04792):
    - At step 1 (obs=1): p reaches 0.660914 (>= 0.40, not weak)
    - At step 2 (obs=0): p drops to 0.387645 (< 0.40, crossing Weak boundary)
    Checks exact parity with pyBKT and BKTOnlineAdapter within 1e-6.
    """
    _, policy = fitted_policy_and_adapter
    fitted_params = load_fitted_bkt_params(DEFAULT_FITTED_CONFIG_PATH)
    prior = fitted_params["prior"]

    seq = [1, 1, 0, 0]
    pybkt_posteriors = _run_pybkt_sequence(pybkt_fitted_model, seq)

    cs = ConceptState.init_from_ability(prior)
    cs.policy = policy
    adapter = BKTOnlineAdapter.from_config(DEFAULT_FITTED_CONFIG_PATH)

    crossed_weak = False
    for t, obs in enumerate(seq):
        prev_p = cs.p
        post_adapter = adapter.update(obs)
        cs.update(obs, policy=policy)
        post_pybkt = pybkt_posteriors[t]

        assert abs(cs.p - post_adapter) <= 1e-6
        assert abs(cs.p - post_pybkt) <= 1e-6

        # Check crossing weak boundary from above 0.40 to below 0.40
        if prev_p >= policy.weak_p > cs.p:
            crossed_weak = True

    assert crossed_weak, f"Sequence did not cross Weak boundary {policy.weak_p}"
    assert cs.p < policy.weak_p



# =============================================================================
# 5. CROSSING MASTERED BOUNDARY (p >= 0.85)
# =============================================================================

def test_updater_parity_crossing_mastered_boundary(pybkt_fitted_model, fitted_policy_and_adapter):
    """
    Verifies parity on a sequence crossing the Mastered boundary (p >= 0.85).
    Starts with cold start / fitted prior (< 0.85), receives successive correct responses
    until crossing 0.85.
    """
    _, policy = fitted_policy_and_adapter
    fitted_params = load_fitted_bkt_params(DEFAULT_FITTED_CONFIG_PATH)
    prior = fitted_params["prior"]
    assert prior < 0.85

    seq = [1, 1, 1]  # Steps: ~0.317 -> ~0.661 -> ~0.879 (crosses 0.85 at step 2)
    pybkt_posteriors = _run_pybkt_sequence(pybkt_fitted_model, seq)

    cs = ConceptState.init_from_ability(prior)
    cs.policy = policy
    adapter = BKTOnlineAdapter.from_config(DEFAULT_FITTED_CONFIG_PATH)

    crossed = False
    for t, obs in enumerate(seq):
        prev_p = cs.p
        post_adapter = adapter.update(obs)
        cs.update(obs, policy=policy)
        post_pybkt = pybkt_posteriors[t]

        assert abs(cs.p - post_adapter) <= 1e-6
        assert abs(cs.p - post_pybkt) <= 1e-6

        if prev_p < policy.mastered_p <= cs.p:
            crossed = True

    assert crossed, f"Sequence did not cross mastered boundary {policy.mastered_p}"
    assert cs.p >= policy.mastered_p


# =============================================================================
# 6. WINDOW SIZE 6 SEQUENCE
# =============================================================================

def test_updater_parity_window_size_6(pybkt_fitted_model):
    """
    Verifies parity on an extended 10-observation sequence with policy window_size=6.
    Ensures history length is strictly capped at window_size=6 while belief parity
    matches pyBKT and BKTOnlineAdapter within 1e-6 at every step.
    """
    fitted_params = load_fitted_bkt_params(DEFAULT_FITTED_CONFIG_PATH)
    policy = PolicyConfig(
        p_S=fitted_params["p_S"],
        p_G=fitted_params["p_G"],
        p_T=fitted_params["p_T"],
        window_size=6,
        mastered_p=fitted_params["mastered_p"],
        weak_p=fitted_params["weak_p"],
        sigma2_max=fitted_params["sigma2_max"],
        min_obs=fitted_params["min_obs"],
        kappa0=fitted_params["kappa0"],
    )
    prior = fitted_params["prior"]

    seq = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1]
    pybkt_posteriors = _run_pybkt_sequence(pybkt_fitted_model, seq)

    cs = ConceptState.init_from_ability(prior)
    cs.policy = policy
    adapter = BKTOnlineAdapter(
        p_S=policy.p_S,
        p_G=policy.p_G,
        p_T=policy.p_T,
        prior=prior,
        forget=0.0,
        policy=policy,
    )

    for t, obs in enumerate(seq):
        post_adapter = adapter.update(obs)
        cs.update(obs, policy=policy)
        post_pybkt = pybkt_posteriors[t]

        # Check exact parity within 1e-6
        assert abs(cs.p - post_adapter) <= 1e-6
        assert abs(cs.p - post_pybkt) <= 1e-6

        # Check window size capping
        expected_window = seq[: t + 1][-6:]
        assert cs.history == expected_window
        assert len(cs.history) <= 6

    assert len(cs.history) == 6
    assert cs.n == len(seq)
