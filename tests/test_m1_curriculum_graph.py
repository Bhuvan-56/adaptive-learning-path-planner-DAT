"""
Acceptance tests for Milestone 1: Curriculum Graph & Learner State Models.
Mapped to TRACEABILITY.md (TC-1.1, TC-1.2).
"""

import pytest


def test_tc_1_1_no_lesson_before_unmet_prerequisite():
    """
    TC-1.1: Prerequisite Gating
    Scenario: A plan is generated for a target concept with an unmet mandatory prerequisite.
    Expected Result: The plan contains no lesson for that target before the prerequisite
    is explicitly Mastered (p >= 0.85, sigma^2 <= 0.05, n >= 3).
    """
    pass  # TODO: implement once planner module exists


def test_tc_1_2_dag_passes_five_validation_checks():
    """
    TC-1.2: Curriculum Graph Validation
    Scenario: A curriculum DAG is submitted to the validator before planning.
    Expected Result: The DAG passes all 5 automated checks:
      1. Existing prerequisite nodes
      2. Positive durations
      3. Difficulty bounds in [0.05, 0.95]
      4. No self-loops
      5. No cyclic components via Tarjan's SCC
    """
    pass  # TODO: implement once graph validation module exists
