"""
Parity tests between pyBKT offline model and the project's online BKT adapter.

CONVENTION DIFFERENCE SPECIFICATION:
------------------------------------
pyBKT's predict API (Model.predict) outputs one-step-ahead predictions:
  - `state_predictions[t]`: The latent mastery probability entering interaction t,
    BEFORE observing the outcome of interaction t.
    Specifically, `state_predictions[0]` is the initial prior belief P(L_0).
  - `correct_predictions[t]`: The predicted probability that the learner will respond
    correctly on interaction t given the entering belief:
        P(correct) = P(L_t) * (1 - p_S) + (1 - P(L_t)) * p_G.

In contrast, an online adapter's update method (`adapter.update(correct)`):
  - Ingests the observed outcome for interaction t, computes the Bayes evidence
    update P(L_t | obs), and immediately applies the skill transition step P_T.
  - The resulting posterior mastery belief P(L_{t+1}) is the belief entering
    interaction t+1.

MATHEMATICAL CORRESPONDENCE:
  1. Entering belief at interaction t:
     `adapter.p` BEFORE update(t) == `pyBKT.state_predictions[t]`
  2. Predicted response correctness at interaction t:
     `adapter.predict_correct_probability()` == `pyBKT.correct_predictions[t]`
  3. Posterior belief after interaction t:
     `adapter.p` AFTER update(t) == `pyBKT.state_predictions[t+1]`

TOLERANCE:
  All assertions enforce max absolute difference <= 1e-6 without widening.
"""

import os
import pytest
import pandas as pd
from pyBKT.models import Model

from src.state.bkt_adapter import (
    BKTOnlineAdapter,
    load_fitted_bkt_params,
    DEFAULT_FITTED_CONFIG_PATH,
)


@pytest.fixture(scope="module")
def fitted_setup():
    """Sets up synthetic data, fits pyBKT model, and loads adapter."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_path = os.path.join(repo_root, "data", "processed", "synthetic_bkt_responses.csv")
    assert os.path.exists(data_path), f"Synthetic dataset missing: {data_path}"

    df = pd.read_csv(data_path)
    heldout_student_id = "student_10"
    train_df = df[df["user_id"] != heldout_student_id].copy()
    test_df = df[df["user_id"] == heldout_student_id].copy()

    # Fit pyBKT on training students
    model = Model(seed=42, num_fits=1, parallel=False)
    model.fit(data=train_df)

    # To evaluate posterior after the final (15th) interaction in pyBKT,
    # append a 16th dummy trial to test_df. pyBKT's state_predictions at index 15
    # will be the posterior entering trial 16, which is exactly post-trial-15 belief.
    dummy_row = test_df.iloc[-1:].copy()
    dummy_row["order_id"] = test_df["order_id"].max() + 1
    dummy_row["correct"] = 0
    extended_test_df = pd.concat([test_df, dummy_row], ignore_index=True)

    preds_extended = model.predict(data=extended_test_df)

    return {
        "model": model,
        "test_df": test_df,
        "preds_extended": preds_extended,
        "adapter": BKTOnlineAdapter.from_config(DEFAULT_FITTED_CONFIG_PATH),
    }


def test_bkt_parity_on_heldout_student(fitted_setup):
    """
    Feeds held-out student's response sequence through both pyBKT and BKTOnlineAdapter.
    Asserts exact posterior mastery match after each interaction to within 1e-6.
    """
    test_df = fitted_setup["test_df"]
    preds = fitted_setup["preds_extended"]
    adapter = fitted_setup["adapter"]

    pybkt_states = preds["state_predictions"].tolist()
    pybkt_correct = preds["correct_predictions"].tolist()

    max_state_diff = 0.0
    max_correct_diff = 0.0

    for t, (_, row) in enumerate(test_df.iterrows()):
        obs = int(row["correct"])

        # 1. Parity check on belief entering trial t
        entering_pybkt = pybkt_states[t]
        entering_adapter = adapter.p
        diff_entering = abs(entering_adapter - entering_pybkt)
        assert diff_entering <= 1e-6, (
            f"Entering mastery mismatch at step {t}: "
            f"adapter={entering_adapter}, pybkt={entering_pybkt}, diff={diff_entering}"
        )
        if diff_entering > max_state_diff:
            max_state_diff = diff_entering

        # 2. Parity check on predicted probability of correct response
        pred_corr_adapter = adapter.predict_correct_probability()
        pred_corr_pybkt = pybkt_correct[t]
        diff_corr = abs(pred_corr_adapter - pred_corr_pybkt)
        assert diff_corr <= 1e-6, (
            f"Predicted correct probability mismatch at step {t}: "
            f"adapter={pred_corr_adapter}, pybkt={pred_corr_pybkt}, diff={diff_corr}"
        )
        if diff_corr > max_correct_diff:
            max_correct_diff = diff_corr

        # 3. Apply online observation update + learning transition
        post_mastery_adapter = adapter.update(obs)

        # 4. Parity check on posterior mastery probability after interaction t
        # pyBKT's entering belief at index t + 1 corresponds to posterior after interaction t
        post_mastery_pybkt = pybkt_states[t + 1]
        diff_post = abs(post_mastery_adapter - post_mastery_pybkt)
        assert diff_post <= 1e-6, (
            f"Posterior mastery mismatch after step {t}: "
            f"adapter={post_mastery_adapter}, pybkt={post_mastery_pybkt}, diff={diff_post}"
        )
        if diff_post > max_state_diff:
            max_state_diff = diff_post

    # Verify that total comparisons were made and precision remained well within 1e-6
    assert len(test_df) == 15
    assert max_state_diff < 1e-6
    assert max_correct_diff < 1e-6


def test_bkt_adapter_validation_and_forget_zero():
    """Validates adapter error handling and enforcement of zero forgetting."""
    # Non-zero forgetting must raise ValueError
    with pytest.raises(ValueError, match="Standard BKT requires forget == 0.0"):
        BKTOnlineAdapter(p_S=0.1, p_G=0.2, p_T=0.1, prior=0.5, forget=0.05)

    # Probabilities outside [0, 1] must raise ValueError
    with pytest.raises(ValueError, match="p_S must be in"):
        BKTOnlineAdapter(p_S=1.5, p_G=0.2, p_T=0.1, prior=0.5)

    with pytest.raises(ValueError, match="prior must be in"):
        BKTOnlineAdapter(p_S=0.1, p_G=0.2, p_T=0.1, prior=-0.1)


def test_bkt_adapter_to_concept_state():
    """Tests conversion of adapter state to ConceptState."""
    adapter = BKTOnlineAdapter(p_S=0.1, p_G=0.2, p_T=0.15, prior=0.3)
    adapter.update(1)
    adapter.update(0)
    cs = adapter.to_concept_state()

    assert cs.n == 2
    assert cs.history == [1, 0]
    assert abs(cs.p - adapter.p) <= 1e-9
    assert cs.A + cs.B == pytest.approx(cs.policy.kappa0)
