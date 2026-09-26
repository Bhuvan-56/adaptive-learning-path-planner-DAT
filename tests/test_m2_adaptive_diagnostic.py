"""
Acceptance tests for Milestone 2: Adaptive Diagnostic Policy.
Mapped to TRACEABILITY.md (TC-2.1, TC-2.2).
"""

import pytest


def test_tc_2_1_incorrect_response_lowers_mastery_and_selects_max_fisher_item():
    """
    TC-2.1: Fisher Information Item Selection & Mastery Update
    Scenario: Learner answers a diagnostic item incorrectly.
    Expected Result: The relevant concept's mastery estimate decreases, and the next item
    is selected via maximum Fisher information given the updated ability estimate.
    """
    pass  # TODO: implement once diagnostic CAT module exists


def test_tc_2_2_diagnostic_terminates_on_variance_or_question_limit():
    """
    TC-2.2: Diagnostic Stopping Rule
    Scenario: Diagnostic is in progress.
    Expected Result: Calibration terminates immediately once ability variance <= 0.15,
    or at exactly 10 questions, whichever comes first.
    """
    pass  # TODO: implement once diagnostic CAT module exists
