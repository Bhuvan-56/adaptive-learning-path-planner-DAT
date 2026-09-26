"""
Acceptance tests for Milestone 6: Dynamic Replanning & Infeasibility.
Mapped to TRACEABILITY.md (TC-6.1, TC-6.2).
"""

import pytest


def test_tc_6_1_missed_day_triggers_dynamic_replanning_without_overwriting_progress():
    """
    TC-6.1: Missed Session Dynamic Replanning
    Scenario: Learner misses a scheduled day.
    Expected Result: The remaining schedule is dynamically replanned without deleting
    or overwriting already-completed progress.
    """
    pass  # TODO: implement once dynamic replanning module exists


def test_tc_6_2_reduced_budget_outputs_valid_plan_or_infeasibility_trace_with_alternatives():
    """
    TC-6.2: Mid-Plan Budget Reduction & Infeasibility Alternatives
    Scenario: Daily budget is reduced mid-plan.
    Expected Result: System outputs either a still-valid compressed plan, or an explicit
    capacity-infeasibility trace with computed alternatives (extend deadline by X days,
    raise budget by Y minutes, or reduce optional scope).
    """
    pass  # TODO: implement once infeasibility trace module exists
