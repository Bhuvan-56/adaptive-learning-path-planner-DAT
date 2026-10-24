import os
import pytest
import yaml

from src.state.policy import load_policy, PolicyConfig
from src.state.learner_state import load_bkt_params
from src.state.bkt_adapter import load_fitted_bkt_params

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BKT_PARAMS_PATH = os.path.join(REPO_ROOT, "config", "bkt_params.yaml")
BKT_FITTED_PATH = os.path.join(REPO_ROOT, "config", "bkt_fitted.yaml")


def test_w4_d3_only_typo_raises_and_names_missing_keys(tmp_path):
    typo_file = tmp_path / "only_typo.yaml"
    typo_file.write_text("p_GG: 0.9\n", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        load_policy(str(typo_file))
    msg = str(excinfo.value)
    for req in ["p_S", "p_G", "p_T", "window_size"]:
        assert req in msg


def test_w4_d3_complete_file_plus_unknown_key_raises_and_names_key(tmp_path):
    extra_file = tmp_path / "extra_key.yaml"
    extra_file.write_text(
        "p_S: 0.10\n"
        "p_G: 0.25\n"
        "p_T: 0.10\n"
        "window_size: 4\n"
        "unknown_extra_key: 123\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as excinfo:
        load_policy(str(extra_file))
    assert "unknown_extra_key" in str(excinfo.value)


def test_w4_d3_misspelled_key_raises(tmp_path):
    misspelled_file = tmp_path / "misspelled.yaml"
    misspelled_file.write_text(
        "p_s: 0.10\n"
        "p_G: 0.25\n"
        "p_T: 0.10\n"
        "window_size: 4\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as excinfo:
        load_policy(str(misspelled_file))
    msg = str(excinfo.value)
    assert "p_s" in msg or "p_S" in msg


def test_w4_d3_shipped_bkt_params_loads():
    policy = load_policy(BKT_PARAMS_PATH)
    assert isinstance(policy, PolicyConfig)
    assert policy.p_S == 0.10
    assert policy.p_G == 0.25
    assert policy.p_T == 0.10
    assert policy.window_size == 4

    params = load_bkt_params(BKT_PARAMS_PATH)
    assert params["p_S"] == 0.10
    assert params["p_G"] == 0.25
    assert params["p_T"] == 0.10
    assert params["window_size"] == 4


def test_w4_d3_shipped_bkt_fitted_loads_through_fitted_path():
    fitted = load_fitted_bkt_params(BKT_FITTED_PATH)
    assert fitted["p_S"] == pytest.approx(0.09389350193119235)
    assert fitted["p_G"] == pytest.approx(0.3251211164969382)
    assert fitted["p_T"] == pytest.approx(0.22159130231353227)
    assert fitted["prior"] == pytest.approx(0.04792007810298316)
    assert fitted["forget"] == 0.0
    assert fitted["window_size"] == 4
    assert fitted["mastered_p"] == 0.85
    assert fitted["weak_p"] == 0.40
    assert fitted["sigma2_max"] == 0.05
    assert fitted["min_obs"] == 3
    assert fitted["kappa0"] == 2.0


def test_w4_d3_defaulted_fields_reported_to_caller(tmp_path):
    policy = load_policy(BKT_PARAMS_PATH)
    assert hasattr(policy, "defaulted_fields")
    expected_defaulted = {"mastered_p", "weak_p", "sigma2_max", "min_obs", "kappa0"}
    assert set(policy.defaulted_fields) == expected_defaulted

    params = load_bkt_params(BKT_PARAMS_PATH)
    assert "defaulted_fields" in params
    assert set(params["defaulted_fields"]) == expected_defaulted

    # When all fields are provided, defaulted_fields should be empty
    full_file = tmp_path / "full_policy.yaml"
    full_file.write_text(
        "p_S: 0.10\n"
        "p_G: 0.25\n"
        "p_T: 0.10\n"
        "window_size: 4\n"
        "mastered_p: 0.85\n"
        "weak_p: 0.40\n"
        "sigma2_max: 0.05\n"
        "min_obs: 3\n"
        "kappa0: 2.0\n",
        encoding="utf-8",
    )
    full_policy = load_policy(str(full_file))
    assert list(full_policy.defaulted_fields) == []


def test_w4_d3_bad_file_fails_consistently_across_three_loaders(tmp_path):
    bad_file = tmp_path / "bad_policy.yaml"
    bad_file.write_text(
        "p_S: 0.10\n"
        "p_G: 0.25\n"
        "p_T: 0.10\n"
        "window_size: 4\n"
        "unexpected_field: 999\n",
        encoding="utf-8",
    )
    err1, err2, err3 = None, None, None
    with pytest.raises(ValueError) as exc1:
        load_policy(str(bad_file))
    err1 = str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        load_bkt_params(str(bad_file))
    err2 = str(exc2.value)

    with pytest.raises(ValueError) as exc3:
        load_fitted_bkt_params(str(bad_file))
    err3 = str(exc3.value)

    assert "unexpected_field" in err1
    assert "unexpected_field" in err2
    assert "unexpected_field" in err3
    assert err1 == err2 == err3


import networkx as nx
from src.curriculum.graph import load_graph, validate_graph
from src.curriculum.errors import GraphErrorCode


def test_w4_d5_nan_edge_importance_fixture_returns_non_finite_value():
    fixture_path = os.path.join(REPO_ROOT, "tests", "fixtures", "graphs", "non_finite_edge_importance.json")
    g = load_graph(fixture_path)
    errors = validate_graph(g)
    assert errors == [GraphErrorCode.NON_FINITE_VALUE]


def test_w4_d5_inf_edge_importance_returns_non_finite_value():
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=10.0, base_difficulty=0.20)
    g.add_node("B", baseline_duration=15.0, base_difficulty=0.35)
    g.add_edge("A", "B", importance=float("inf"))
    g.graph["raw_edges"] = [("A", "B", float("inf"))]
    errors = validate_graph(g)
    assert errors == [GraphErrorCode.NON_FINITE_VALUE]

    # Also check negative infinity
    g2 = nx.DiGraph()
    g2.add_node("A", baseline_duration=10.0, base_difficulty=0.20)
    g2.add_node("B", baseline_duration=15.0, base_difficulty=0.35)
    g2.add_edge("A", "B", importance=float("-inf"))
    g2.graph["raw_edges"] = [("A", "B", float("-inf"))]
    errors2 = validate_graph(g2)
    assert errors2 == [GraphErrorCode.NON_FINITE_VALUE]



