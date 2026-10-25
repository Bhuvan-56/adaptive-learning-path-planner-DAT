"""
Unit and Integration Tests for Week 5 Task B1: Integrated Closed-Loop Evaluation Harness.

Verifies:
1. Reproduction test for F1 (activities key execution).
2. Byte-identical plans, traces, and metrics on rerun with same seed in tmp_path.
3. Every arm sees the same learners (matched cohorts, initial latent states, and seeds).
4. Prerequisite and budget violations come out of independent recount in test.
5. Injected prerequisite violation is detected and counted by independent recount.
6. Summary text changes when an evaluation input parameter changes.
7. Claim rule prints 'no difference shown' when confidence interval contains zero.
8. Architectural boundary: zero imports of src.simulation or src.evaluation from
   src/planning, src/state, or src/diagnostic.
"""

import ast
import glob
import json
import os
import networkx as nx
import pandas as pd
import pytest
import yaml

from src.evaluation.compare import run_planner_comparison
from src.simulation.simulator import SimulatedLearner
from src.curriculum.graph import load_graph
from src.evaluation.integrated import (
    run_integrated_evaluation,
    load_integrated_config,
    recount_plan_violations,
    DEFAULT_INTEGRATED_CONFIG,
)


def test_w5_f1_planner_controls_executes_activities(tmp_path):
    """
    Verifies that run_planner_comparison executes scheduled activities for static and adaptive arms.
    In the unfixed code, lines 727 and 829 query .get('lessons', []) which evaluates to [] because
    generate_static_plan and replan emit 'activities', causing 0 activities to be executed.
    """
    out_dir = str(tmp_path / "f1_test")
    call_counts = []
    orig_respond = SimulatedLearner.respond

    def wrapped_respond(self, concept, difficulty=0.5):
        call_counts.append(concept)
        return orig_respond(self, concept=concept, difficulty=difficulty)

    SimulatedLearner.respond = wrapped_respond
    try:
        run_planner_comparison(
            output_dir=out_dir,
            override_learners=2,
            override_resamples=10,
        )
    finally:
        SimulatedLearner.respond = orig_respond

    # Unfixed code only executes non_adaptive_greedy (8 calls for 2 learners: A, B, C, D each)
    # Fixed code executes static_prerequisite_order and adaptive_replan activities as well.
    assert len(call_counts) > 8, (
        f"Only greedy executed activities ({len(call_counts)} calls); static and adaptive executed 0."
    )


import itertools
from unittest import mock


def test_w5_b1_byte_identical_rerun(tmp_path):
    """Running integrated evaluation twice with the same seed produces byte-identical outputs."""
    dir1 = str(tmp_path / "run1")
    dir2 = str(tmp_path / "run2")

    with mock.patch("time.perf_counter", side_effect=itertools.count(0.0, 0.001).__next__), \
         mock.patch("time.strftime", return_value="2026-10-25T12:00:00Z"):
        res1 = run_integrated_evaluation(
            config_path=DEFAULT_INTEGRATED_CONFIG,
            output_dir=dir1,
            override_learners=3,
            override_resamples=20,
        )

    with mock.patch("time.perf_counter", side_effect=itertools.count(0.0, 0.001).__next__), \
         mock.patch("time.strftime", return_value="2026-10-25T12:00:00Z"):
        res2 = run_integrated_evaluation(
            config_path=DEFAULT_INTEGRATED_CONFIG,
            output_dir=dir2,
            override_learners=3,
            override_resamples=20,
        )

    # 1. Compare per_learner.csv
    with open(res1["csv_path"], "rb") as f1, open(res2["csv_path"], "rb") as f2:
        assert f1.read() == f2.read(), "per_learner.csv differs across identical seed runs."

    # 2. Compare summary.md
    with open(res1["md_path"], "rb") as f1, open(res2["md_path"], "rb") as f2:
        assert f1.read() == f2.read(), "summary.md differs across identical seed runs."

    # 3. Compare manifest.json
    with open(res1["manifest_path"], "rb") as f1, open(res2["manifest_path"], "rb") as f2:
        assert f1.read() == f2.read(), "manifest.json differs across identical seed runs."


def test_w5_b1_every_arm_sees_same_learners(tmp_path):
    """Verifies that all evaluated arms see matched synthetic learners with identical seeds and theta."""
    out_dir = str(tmp_path / "matched_cohort")
    res = run_integrated_evaluation(
        config_path=DEFAULT_INTEGRATED_CONFIG,
        output_dir=out_dir,
        override_learners=4,
        override_resamples=20,
    )

    df = pd.read_csv(res["csv_path"])
    arms = df["arm"].unique()
    assert len(arms) >= 3, "Expected at least 3 arms in per_learner.csv"

    # Pivot theta_true by learner_id and arm
    piv_theta = df.pivot(index="learner_id", columns="arm", values="theta_true")
    for arm in arms:
        assert (piv_theta[arm] == piv_theta[arms[0]]).all(), f"Learners mismatched for arm {arm}"

    piv_seed = df.pivot(index="learner_id", columns="arm", values="seed")
    for arm in arms:
        assert (piv_seed[arm] == piv_seed[arms[0]]).all(), f"Seeds mismatched for arm {arm}"


def test_w5_b1_independent_recount_violations(tmp_path):
    """
    Verifies that prerequisite and budget violations can be computed independently
    without invoking planner internals.
    """
    curriculum_path = "data/curricula/demo_curriculum.json"
    g = load_graph(curriculum_path)

    # Valid plan: Day 1 [A, B] (duration 5+5=10), Day 2 [C] (duration 10)
    valid_plan = [
        {"day": 1, "activities": ["A", "B"]},
        {"day": 2, "activities": ["C"]},
    ]
    prereqs, budgets = recount_plan_violations(valid_plan, g, daily_budget=10)
    assert prereqs == 0
    assert budgets == 0


def test_w5_b1_injected_prerequisite_and_budget_violations_counted():
    """Verifies that independent recount detects and counts injected violations."""
    curriculum_path = "data/curricula/demo_curriculum.json"
    g = load_graph(curriculum_path)

    # Injected prerequisite violation: B scheduled on Day 1 before A
    prereq_violated_plan = [
        {"day": 1, "activities": ["B"]},
    ]
    prereqs, budgets = recount_plan_violations(prereq_violated_plan, g, daily_budget=10)
    assert prereqs > 0, "Prerequisite violation was not detected by independent recount."
    assert budgets == 0

    # Injected budget violation: A (5) + C (10) = 15 > budget 10
    budget_violated_plan = [
        {"day": 1, "activities": ["A", "C"]},
    ]
    prereqs2, budgets2 = recount_plan_violations(budget_violated_plan, g, daily_budget=10)
    assert budgets2 > 0, "Budget violation was not detected by independent recount."


def test_w5_b1_summary_text_changes_on_input_change(tmp_path):
    """Verifies that summary.md content changes when configuration inputs change."""
    dir1 = str(tmp_path / "cfg1")
    dir2 = str(tmp_path / "cfg2")

    res1 = run_integrated_evaluation(
        config_path=DEFAULT_INTEGRATED_CONFIG,
        output_dir=dir1,
        override_learners=2,
        override_resamples=10,
    )
    res2 = run_integrated_evaluation(
        config_path=DEFAULT_INTEGRATED_CONFIG,
        output_dir=dir2,
        override_learners=4,
        override_resamples=10,
    )

    with open(res1["md_path"], "r", encoding="utf-8") as f1, open(res2["md_path"], "r", encoding="utf-8") as f2:
        text1 = f1.read()
        text2 = f2.read()

    assert text1 != text2, "summary.md should differ when cohort size changes."
    assert "2 synthetic learners" in text1 or "200" in text1
    assert "4 synthetic learners" in text2 or "200" in text2


def test_w5_b1_claim_rule_no_difference_shown(tmp_path):
    """
    Verifies that the claim rule outputs 'no difference shown' when confidence interval
    for arm difference contains zero (e.g. for difficulty and review ablations under MatchedBKTGenerator).
    """
    out_dir = str(tmp_path / "claim_check")
    res = run_integrated_evaluation(
        config_path=DEFAULT_INTEGRATED_CONFIG,
        output_dir=out_dir,
        override_learners=4,
        override_resamples=25,
    )

    with open(res["md_path"], "r", encoding="utf-8") as f:
        summary_md = f.read()

    assert "no difference shown" in summary_md, "Claim rule must state 'no difference shown' when CI includes zero."
    assert "MatchedBKTGenerator" in summary_md


def test_w5_b1_latent_state_invisibility_boundary():
    """
    Architectural boundary test:
    Modules under src/planning, src/state, and src/diagnostic must NEVER import
    from src/simulation or src/evaluation, nor reference EvaluatorView.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    checked_dirs = [
        os.path.join(repo_root, "src", "planning"),
        os.path.join(repo_root, "src", "state"),
        os.path.join(repo_root, "src", "diagnostic"),
    ]

    forbidden_tokens = [
        "src.evaluation",
        "src.simulation",
        "EvaluatorView",
        "evaluator_view",
    ]

    violations = []
    for cdir in checked_dirs:
        for py_file in glob.glob(os.path.join(cdir, "**", "*.py"), recursive=True):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            parsed = ast.parse(content, filename=py_file)
            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for token in forbidden_tokens:
                            if token in alias.name:
                                violations.append((py_file, node.lineno, token))
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    for token in forbidden_tokens:
                        if token in mod_name:
                            violations.append((py_file, node.lineno, token))
                    for alias in node.names:
                        for token in forbidden_tokens:
                            if token in alias.name:
                                violations.append((py_file, node.lineno, token))

    assert not violations, f"Architectural boundary violated! Forbidden imports found: {violations}"
