import math
import pytest
from src.trace.checker import check_trace


def make_valid_entry(node_id="A", day=1, decision="SELECTED", reason_code="SELECTED", concept_class="Developing"):
    return {
        "node_id": node_id,
        "day": day,
        "concept_state": {
            "p": 0.5,
            "kappa": 2.0,
            "sigma2": 0.05,
            "n": 3,
            "class": concept_class
        },
        "constraints": {
            "budget": 15,
            "remaining_budget": 15,
            "prerequisites": {}
        },
        "score_terms": {},
        "decision": decision,
        "reason_code": reason_code,
        "policy_version": "static_baseline_v0"
    }


def test_w4_d4_concept_state_none():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["concept_state"] = None
    with pytest.raises(ValueError, match="concept_state"):
        check_trace(universe, [entry], num_days=1)


def test_w4_d4_constraints_none():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["constraints"] = None
    with pytest.raises(ValueError, match="constraints"):
        check_trace(universe, [entry], num_days=1)


def test_w4_d4_score_terms_none():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["score_terms"] = None
    with pytest.raises(ValueError, match="score_terms"):
        check_trace(universe, [entry], num_days=1)


def test_w4_d4_negative_remaining_budget():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["constraints"]["remaining_budget"] = -5
    with pytest.raises(ValueError, match="remaining_budget"):
        check_trace(universe, [entry], num_days=1)


def test_w4_d4_day_zero():
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="A", day=0),
    ]
    with pytest.raises(ValueError, match="day"):
        check_trace(universe, trace, num_days=1)


def test_w4_d4_day_d_plus_one():
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="A", day=2),
    ]
    with pytest.raises(ValueError, match="day"):
        check_trace(universe, trace, num_days=1)


def test_w4_d4_non_dict_entry():
    universe = {"A"}
    with pytest.raises(ValueError, match="dictionary"):
        check_trace(universe, ["not_a_dict"], num_days=1)


def test_w4_d4_non_finite_number():
    universe = {"A"}
    entry1 = make_valid_entry(node_id="A", day=1)
    entry1["concept_state"]["p"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        check_trace(universe, [entry1], num_days=1)

    entry2 = make_valid_entry(node_id="A", day=1)
    entry2["score_terms"]["term"] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        check_trace(universe, [entry2], num_days=1)


def test_w4_d4_concept_state_p_outside_unit_interval():
    universe = {"A"}
    entry_high = make_valid_entry(node_id="A", day=1)
    entry_high["concept_state"]["p"] = 1.5
    with pytest.raises(ValueError, match=r"p.*\[0.*1\]|probability"):
        check_trace(universe, [entry_high], num_days=1)

    entry_low = make_valid_entry(node_id="A", day=1)
    entry_low["concept_state"]["p"] = -0.1
    with pytest.raises(ValueError, match=r"p.*\[0.*1\]|probability"):
        check_trace(universe, [entry_low], num_days=1)


def test_w4_d4_concept_state_n_negative():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["concept_state"]["n"] = -1
    with pytest.raises(ValueError, match=r"n.*negative|n.*>= 0"):
        check_trace(universe, [entry], num_days=1)


def test_w4_d4_remaining_budget_exceeds_budget_param():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["constraints"]["remaining_budget"] = 20
    with pytest.raises(ValueError, match="exceeding daily budget"):
        check_trace(universe, [entry], num_days=1, budget=15)


# ==============================================================================
# D6 Reproduction Tests
# ==============================================================================
from src.cli import run_demo
from src.curriculum.graph import load_graph
from src.planning.service import plan_request
from src.state.learner_state import ConceptState


@pytest.mark.xfail(strict=True, reason="W4 D6: demo budget 5 fails with TRACE_CHECK_FAILED on valid no-plan")
def test_w4_d6_demo_budgets_exit_by_status(tmp_path, capsys):
    out_dir = str(tmp_path / "budget_5")
    ret = run_demo(out_dir=out_dir, budget=5, curriculum_path="data/curricula/demo_curriculum.json")
    captured = capsys.readouterr()
    assert "TRACE_CHECK_FAILED" not in captured.err
    assert ret == 0


@pytest.mark.xfail(strict=True, reason="W4 D6: plan_request with multiple targets silently plans only first target")
def test_w4_d6_multiple_targets_rejected():
    g = load_graph("data/curricula/demo_curriculum.json")
    states = {nid: ConceptState.cold_start() for nid in g.nodes}
    res = plan_request(
        graph=g,
        learner_states=states,
        budget=10,
        deadline_days=3,
        targets=["A", "B"]
    )
    assert not res.is_valid
    assert res.status == "INVALID_INPUT"
    assert "MULTIPLE_TARGETS_UNSUPPORTED" in res.error_codes


@pytest.mark.xfail(strict=True, reason="W4 D6: missing/invalid policy path handling")
def test_w4_d6_policy_path_handling(tmp_path, capsys):
    # Non-existent policy path should fail cleanly with a useful message
    out_dir = str(tmp_path / "bad_policy")
    ret = run_demo(out_dir=out_dir, budget=10, policy_path="non_existent_policy.yaml")
    captured = capsys.readouterr()
    assert ret != 0
    assert "MISSING_POLICY_FILE" in captured.err or "Policy file does not exist" in captured.err

    # Default policy path should state in human output that declared default was used
    out_default = str(tmp_path / "default_policy")
    ret_default = run_demo(out_dir=out_default, budget=10)
    captured_default = capsys.readouterr()
    assert ret_default == 0
    assert "declared default" in captured_default.out.lower()


@pytest.mark.xfail(strict=True, reason="W4 D6: demo output text is hardcoded instead of derived from emitted state")
def test_w4_d6_outcome_text_derived_from_state(tmp_path, capsys):
    out_15 = str(tmp_path / "out_15")
    ret = run_demo(out_dir=out_15, budget=15)
    captured = capsys.readouterr()
    assert ret == 0
    assert "Reduced from 15m to 5m" in captured.out
    assert "Reduced from 10m to 5m" not in captured.out

