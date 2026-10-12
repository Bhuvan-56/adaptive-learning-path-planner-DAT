import pytest
from src.trace.checker import check_trace, check_no_plan_trace
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


def test_check_trace_missing_whole_day_2_of_2():
    """Defect 2 / Step 5: check_trace must fail when day 2 is missing from a 2-day trace."""
    universe = {"A"}
    trace = [make_valid_entry(node_id="A", day=1)]
    with pytest.raises(ValueError, match="day 2 of 2"):
        check_trace(universe, trace, num_days=2)


def test_check_trace_bogus_decision():
    """Defect 2 / Step 5: check_trace must fail when decision is not in valid set."""
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1, decision="BOGUS")
    with pytest.raises(ValueError, match="invalid decision"):
        check_trace(universe, [entry], num_days=1)


def test_check_trace_missing_constraints_field():
    """Defect 2 / Step 5: check_trace must fail when constraints field is missing."""
    universe = {"A"}
    entry = make_valid_entry(node_id="A", day=1)
    del entry["constraints"]
    with pytest.raises(ValueError, match="missing schema field: 'constraints'"):
        check_trace(universe, [entry], num_days=1)


def test_check_trace_extra_candidate():
    """Defect 2 / Step 5: check_trace must fail when trace contains extra candidates not in universe."""
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="EXTRA", day=1)
    ]
    with pytest.raises(ValueError, match="unexpected candidate"):
        check_trace(universe, trace, num_days=1)


def test_check_trace_duplicate_node():
    """Defect 2 / Step 5: duplicate node in a day must raise ValueError."""
    universe = {"A"}
    trace = [
        make_valid_entry(node_id="A", day=1),
        make_valid_entry(node_id="A", day=1)
    ]
    with pytest.raises(ValueError, match="Duplicate trace entry"):
        check_trace(universe, trace, num_days=1)


def test_check_trace_mastered_reason_with_uncertain_state():
    """Defect 2 / Step 5: check_trace must reject ALREADY_MASTERED reason with Uncertain state."""
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


def test_check_no_plan_trace_contract():
    """Step 3: verify check_no_plan_trace validates the no-plan trace contract."""
    valid_no_plan = {
        "status": "INFEASIBLE_PROVED",
        "reason_code": "BLOCK_EXCEEDS_DAILY_BUDGET",
        "constraints": {
            "budget": 5,
            "deadline_days": 2
        }
    }
    assert check_no_plan_trace(valid_no_plan) is True

    # Cannot contain daily candidate entries
    invalid_with_daily = {
        "status": "INFEASIBLE_PROVED",
        "reason_code": "BLOCK_EXCEEDS_DAILY_BUDGET",
        "constraints": {"budget": 5},
        "node_id": "A",
        "day": 1
    }
    with pytest.raises(ValueError, match="daily candidate entries"):
        check_no_plan_trace(invalid_with_daily)

    # Missing status
    with pytest.raises(ValueError, match="status"):
        check_no_plan_trace({"reason_code": "BLOCK_EXCEEDS_DAILY_BUDGET", "constraints": {"budget": 5}})

    # Missing reason_code
    with pytest.raises(ValueError, match="reason_code"):
        check_no_plan_trace({"status": "INFEASIBLE_PROVED", "constraints": {"budget": 5}})

    # Missing constraints
    with pytest.raises(ValueError, match="constraints"):
        check_no_plan_trace({"status": "INFEASIBLE_PROVED", "reason_code": "BLOCK_EXCEEDS_DAILY_BUDGET"})
