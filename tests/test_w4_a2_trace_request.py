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


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts concept_state=None")
def test_w4_d4_concept_state_none():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["concept_state"] = None
    with pytest.raises(ValueError, match="concept_state"):
        check_trace(universe, [entry], num_days=1)


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts constraints=None")
def test_w4_d4_constraints_none():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["constraints"] = None
    with pytest.raises(ValueError, match="constraints"):
        check_trace(universe, [entry], num_days=1)


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts score_terms=None")
def test_w4_d4_score_terms_none():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["score_terms"] = None
    with pytest.raises(ValueError, match="score_terms"):
        check_trace(universe, [entry], num_days=1)


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts negative remaining_budget")
def test_w4_d4_negative_remaining_budget():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["constraints"]["remaining_budget"] = -5
    with pytest.raises(ValueError, match="remaining_budget"):
        check_trace(universe, [entry], num_days=1)


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts day 0 entry")
def test_w4_d4_day_zero():
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="A", day=0),
    ]
    with pytest.raises(ValueError, match="day"):
        check_trace(universe, trace, num_days=1)


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts day D+1 entry")
def test_w4_d4_day_d_plus_one():
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="A", day=2),
    ]
    with pytest.raises(ValueError, match="day"):
        check_trace(universe, trace, num_days=1)


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace raises AttributeError on non-dict entry")
def test_w4_d4_non_dict_entry():
    universe = {"A"}
    with pytest.raises(ValueError, match="dictionary"):
        check_trace(universe, ["not_a_dict"], num_days=1)


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts non-finite numbers in concept_state or score_terms")
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


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts concept_state p outside [0,1]")
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


@pytest.mark.xfail(strict=True, reason="W4 D4: check_trace accepts negative n in concept_state")
def test_w4_d4_concept_state_n_negative():
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    entry["concept_state"]["n"] = -1
    with pytest.raises(ValueError, match=r"n.*negative|n.*>= 0"):
        check_trace(universe, [entry], num_days=1)
