import os
import pytest
import yaml

from src.state.learner_state import ConceptState, load_bkt_params


def test_cold_start_uncertain():
    """Cold start state (A=1, B=1, n=0) classifies as Uncertain and never Mastered or Weak."""
    state = ConceptState.cold_start()
    assert state.n == 0
    assert state.p == pytest.approx(0.5)
    assert state.kappa == pytest.approx(2.0)
    assert state.sigma2 == pytest.approx(1.0 / 12.0)
    assert state.classify() == "Uncertain"
    assert state.classify() not in ["Mastered", "Weak"]


def test_conflicting_evidence_no_unsupported_confidence():
    """Alternating 20 outcomes never produces Mastered or Weak classification under default model params."""
    state = ConceptState.cold_start()
    for i in range(20):
        correct = (i % 2 == 0)
        state.update(correct)
        assert state.classify() not in ["Mastered", "Weak"]


def test_conflicting_evidence_realistic_params():
    """Alternating outcomes for 20 and 100 steps under realistic BKT params (learn=0.10) never classify as Mastered or Weak."""
    params = load_bkt_params()
    assert params["p_T"] == 0.10
    state = ConceptState.cold_start()

    for step in range(1, 101):
        correct = (step % 2 != 0)
        state.update(correct, params=params)

        assert state.classify() not in ["Mastered", "Weak"]

        if step in [4, 8, 20, 100]:
            print(f"Step {step}: p={state.p:.4f}, kappa={state.kappa:.1f}, sigma2={state.sigma2:.4f}, n={state.n}, class={state.classify()}")


def test_consistent_correct_reaches_mastered():
    """All-correct sequence from cold start reaches Mastered; reports step number."""
    params = load_bkt_params()
    state = ConceptState.cold_start()
    reached_step = None

    for step in range(1, 20):
        state.update(True, params=params)
        if state.classify() == "Mastered" and reached_step is None:
            reached_step = step

    assert reached_step is not None
    assert reached_step == 4  # Reaches Mastered at step 4 when n=4 and window=4 full
    print(f"All-correct sequence reached Mastered at step {reached_step}")


def test_consistent_incorrect_reaches_weak():
    """All-incorrect sequence from cold start reaches Weak; reports step number."""
    params = load_bkt_params()
    state = ConceptState.cold_start()
    reached_step = None

    for step in range(1, 20):
        state.update(False, params=params)
        if state.classify() == "Weak" and reached_step is None:
            reached_step = step

    assert reached_step is not None
    assert reached_step == 4  # Reaches Weak at step 4 when n=4 and window=4 full
    print(f"All-incorrect sequence reached Weak at step {reached_step}")


def test_window_gate_boundaries():
    """Verifies evidence window gate boundaries (2/4 correct is Developing, 3/4 with p>=0.85 can be Mastered, incomplete window is not Mastered/Weak)."""
    # Incomplete window (history len 3 < 4) with high p and low variance
    state_inc = ConceptState(A=9.0, B=1.0, n=3, history=[1, 1, 1])
    assert state_inc.classify() == "Developing"  # Window len 3 < 4 fails window gate

    # 2/4 correct (window full, 2 correct, 2 incorrect) with high p
    state_2_4 = ConceptState(A=9.0, B=1.0, n=4, history=[1, 0, 1, 0])
    assert state_2_4.classify() == "Developing"

    # 3/4 correct (window full, 3 correct) with p >= 0.85, sigma2 <= 0.05, n >= 3
    state_3_4 = ConceptState(A=9.0, B=1.0, n=4, history=[1, 1, 1, 0])
    assert state_3_4.classify() == "Mastered"


def test_bkt_params_loaded_from_config():
    """Verifies that BKT parameters and window size are loaded correctly from config YAML."""
    params = load_bkt_params()
    assert "p_S" in params
    assert "p_G" in params
    assert "p_T" in params
    assert "window_size" in params
    assert params["p_S"] == 0.10
    assert params["p_G"] == 0.25
    assert params["p_T"] == 0.10
    assert params["window_size"] == 4


def test_boundary_variance_0_05():
    """Variance boundary test for 0.05 threshold."""
    state = ConceptState(A=4.25, B=0.75, n=4, history=[1, 1, 1, 1])
    assert state.sigma2 <= 0.05
    assert state.classify() == "Mastered"


def test_boundary_p_0_85():
    """Mastery threshold: p=0.85 is Mastered, p=0.8499 is Developing (given low variance, n>=3, and window gate)."""
    state_mastered = ConceptState(A=8.5, B=1.5, n=4, history=[1, 1, 1, 1])
    assert state_mastered.p == pytest.approx(0.85)
    assert state_mastered.classify() == "Mastered"

    state_dev = ConceptState(A=8.499, B=1.501, n=4, history=[1, 1, 1, 1])
    assert state_dev.p < 0.85
    assert state_dev.classify() == "Developing"


def test_boundary_p_0_40():
    """Weak threshold: 0.40 is Developing, 0.399 is Weak (given low variance, n>=3, and window gate)."""
    state_dev = ConceptState(A=4.0, B=6.0, n=4, history=[0, 0, 0, 0])
    assert state_dev.p == pytest.approx(0.40)
    assert state_dev.classify() == "Developing"

    state_weak = ConceptState(A=3.99, B=6.01, n=4, history=[0, 0, 0, 0])
    assert state_weak.p < 0.40
    assert state_weak.classify() == "Weak"


def test_boundary_n_3():
    """Evidence count boundary: n=2 is never Mastered or Weak, n=3 can be (with full window)."""
    state_n2 = ConceptState(A=9.0, B=1.0, n=2, history=[1, 1])
    assert state_n2.classify() == "Uncertain"

    state_n4 = ConceptState(A=9.0, B=1.0, n=4, history=[1, 1, 1, 1])
    assert state_n4.classify() == "Mastered"


def test_unprobed_high_p_is_uncertain():
    """An unprobed concept with high prior ability (p0=0.95, n=0) must classify as Uncertain."""
    state = ConceptState.init_from_ability(0.95)
    assert state.n == 0
    assert state.p == pytest.approx(0.95)
    assert state.classify() == "Uncertain"


def test_profiles_yaml_pairs_valid():
    """Loads every profile from config/profiles.yaml and verifies state validation."""
    path = os.path.join(os.path.dirname(__file__), "..", "config", "profiles.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profiles = data.get("profiles", {})
    assert len(profiles) == 4

    for prof_id, prof in profiles.items():
        assert "daily_budget_minutes" in prof
        assert prof["daily_budget_minutes"] in [5, 10, 15, 30]

        init_states = prof.get("initial_states", {})
        for group, params in init_states.items():
            p = params["p"]
            kappa = params["kappa"]
            n = params["n"]
            A = p * kappa
            B = (1.0 - p) * kappa
            state = ConceptState(A=A, B=B, n=n)
            assert state.validate()


def test_variance_validity():
    """Verifies that 0 <= sigma2 <= p*(1-p) holds across a spectrum of state values."""
    for p_val in [0.01, 0.1, 0.4, 0.5, 0.85, 0.99]:
        for kappa_val in [2.0, 5.0, 10.0, 50.0]:
            state = ConceptState(A=p_val * kappa_val, B=(1.0 - p_val) * kappa_val, n=3)
            assert state.validate()
