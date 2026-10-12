import pytest
from src.trace.checker import check_trace
from src.trace.schema import ReasonCode


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


@pytest.mark.xfail(strict=True, reason="Defect 2: check_trace ignores num_days and passes day-1-only trace")
def test_check_trace_missing_whole_day_2_of_2():
    """Defect 2: check_trace must fail when day 2 is missing from a 2-day trace."""
    universe = {"A"}
    trace = [make_valid_entry(node_id="A", day=1)]
    with pytest.raises(ValueError, match="day 2"):
        check_trace(universe, trace, num_days=2)


@pytest.mark.xfail(strict=True, reason="Defect 2: check_trace passes BOGUS decision")
def test_check_trace_bogus_decision():
    """Defect 2: check_trace must fail when decision is not in valid set."""
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1, decision="BOGUS")
    with pytest.raises(ValueError, match="decision"):
        check_trace(universe, [entry], num_days=1)


@pytest.mark.xfail(strict=True, reason="Defect 2: check_trace does not enforce all schema fields")
def test_check_trace_missing_constraints_field():
    """Defect 2: check_trace must fail when constraints field is missing."""
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    del entry["constraints"]
    with pytest.raises(ValueError, match="constraints"):
        check_trace(universe, [entry], num_days=1)


@pytest.mark.xfail(strict=True, reason="Defect 2: check_trace ignores extra candidate nodes")
def test_check_trace_extra_candidate():
    """Defect 2: check_trace must fail when trace contains extra candidates not in universe."""
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="EXTRA", day=1)
    ]
    with pytest.raises(ValueError, match="unexpected candidate|extra candidate"):
        check_trace(universe, trace, num_days=1)


def test_check_trace_duplicate_node():
    """Test required by Step 5: duplicate node in a day must raise ValueError."""
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="A", day=1)
    ]
    with pytest.raises(ValueError, match="Duplicate trace entry"):
        check_trace(universe, trace, num_days=1)


@pytest.mark.xfail(strict=True, reason="Defect 2: check_trace allows ALREADY_MASTERED with Uncertain state")
def test_check_trace_mastered_reason_with_uncertain_state():
    """Defect 2: check_trace must reject ALREADY_MASTERED reason with Uncertain state."""
    universe = {"A"}
    entry = make_valid_entry(
        node_id="A",
        day=1,
        decision="FILTERED",
        reason_code=ReasonCode.ALREADY_MASTERED.value,
        concept_class="Uncertain"
    )
    with pytest.raises(ValueError, match="ALREADY_MASTERED"):
        check_trace(universe, [entry], num_days=1)
