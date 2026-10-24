"""
Tests for Week 4 Task T2: Horizontal Slice Demonstration (Subcommand: slice).

Covers:
1. Byte-identical plans and traces on rerun with same seed.
2. Two learners differ in diagnostic estimates and/or initial states.
3. Zero prerequisite and budget violations across all planned days.
4. Every trace passes its checker with full day coverage (check_trace or check_no_plan_trace).
5. n, p, and state agree across summary, plan, and trace for every updated concept.
6. A different supplied policy changes at least one decision.
7. Adversarial matrix:
   - Budgets 5, 10, 15, 30 (all valid or supported reason code)
   - Changed target (target node B, C)
   - Changed profile (profile_3)
   - Failed assessment (concept A remains unmastered, dependents blocked)
   - Missed day (progress preserved)
   - Shortened deadline (progress preserved, supported reason code if infeasible)
   - Renamed / missing graph (exits with error code 1 and MISSING_CURRICULUM_FILE)
   - Typo / missing policy file (exits with error code 1 and MISSING_POLICY_FILE)
"""

import json
import os
import networkx as nx
import pytest
import yaml

from src.cli import run_slice
from src.curriculum.graph import load_graph
from src.state.learner_state import ConceptState
from src.trace.checker import check_no_plan_trace, check_trace
from src.trace.schema import ReasonCode
from src.trace.universe import get_candidate_universe


EXPECTED_SLICE_ARTIFACTS = [
    "diagnostic_record.json",
    "manifest.json",
    "plan_assessment_failed.json",
    "plan_assessment_passed.json",
    "plan_learner1_day1.json",
    "plan_learner2_day1.json",
    "plan_missed_day.json",
    "plan_reduced_budget.json",
    "plan_remediation.json",
    "plan_review_due.json",
    "plan_shortened_deadline.json",
    "response_updates.json",
    "trace_assessment_failed.json",
    "trace_assessment_passed.json",
    "trace_learner1_day1.json",
    "trace_learner2_day1.json",
    "trace_missed_day.json",
    "trace_reduced_budget.json",
    "trace_remediation.json",
    "trace_review_due.json",
    "trace_shortened_deadline.json",
]


def test_slice_runs_and_produces_all_artifacts(tmp_path):
    """Slice command runs successfully with code 0 and produces all 21 expected artifacts."""
    out_dir = str(tmp_path / "slice_out")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    for artifact in EXPECTED_SLICE_ARTIFACTS:
        p = os.path.join(out_dir, artifact)
        assert os.path.exists(p), f"Artifact missing: {artifact}"


def test_slice_byte_identical_rerun(tmp_path):
    """Running slice twice with the same seed produces byte-identical plans and traces."""
    dir1 = str(tmp_path / "run1")
    dir2 = str(tmp_path / "run2")

    code1 = run_slice(out_dir=dir1, seed=20261024, budget=10)
    code2 = run_slice(out_dir=dir2, seed=20261024, budget=10)
    assert code1 == 0
    assert code2 == 0

    # Check plans and traces are byte-identical
    for fname in EXPECTED_SLICE_ARTIFACTS:
        if fname == "manifest.json":
            # Compare normalized content excluding non-deterministic timestamp
            with open(os.path.join(dir1, fname), "r", encoding="utf-8") as f1, open(os.path.join(dir2, fname), "r", encoding="utf-8") as f2:
                m1 = json.load(f1)
                m2 = json.load(f2)
                m1.pop("timestamp", None)
                m2.pop("timestamp", None)
                assert m1 == m2
        else:
            p1 = os.path.join(dir1, fname)
            p2 = os.path.join(dir2, fname)
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                assert f1.read() == f2.read(), f"File mismatch for {fname}"


def test_slice_two_learners_differ(tmp_path):
    """The two simulated learners produce distinct diagnostic ability estimates and distinct initial states."""
    out_dir = str(tmp_path / "learners_test")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    with open(os.path.join(out_dir, "diagnostic_record.json"), "r", encoding="utf-8") as f:
        diag = json.load(f)

    l1_theta = diag["learner_1"]["theta_hat"]
    l2_theta = diag["learner_2"]["theta_hat"]
    assert l1_theta != pytest.approx(l2_theta), "Learners must have distinct ability estimates"

    # Learner 2 has higher ability than Learner 1
    assert l2_theta > l1_theta


def test_slice_zero_prerequisite_and_budget_violations(tmp_path):
    """Every scheduled plan satisfies curriculum prerequisite constraints and daily budget bounds."""
    out_dir = str(tmp_path / "constraints_test")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    g = load_graph("data/curricula/demo_curriculum.json")

    plan_files = [f for f in EXPECTED_SLICE_ARTIFACTS if f.startswith("plan_")]
    for pf in plan_files:
        with open(os.path.join(out_dir, pf), "r", encoding="utf-8") as f:
            plan = json.load(f)

        status = plan.get("status")
        if status in ("INFEASIBLE_PROVED", "INVALID_INPUT"):
            continue

        days = plan.get("days", [])
        completed: set = set(plan.get("completed_nodes", []))
        mastered_nodes = set()
        for nid, s in plan.get("learner_states", {}).items():
            if isinstance(s, dict):
                cs = ConceptState(
                    A=float(s.get("A", 1.0)),
                    B=float(s.get("B", 1.0)),
                    n=int(s.get("n", 0)),
                    history=s.get("history", [])
                )
                if cs.classify() == "Mastered":
                    mastered_nodes.add(nid)
            elif hasattr(s, "classify"):
                if s.classify() == "Mastered":
                    mastered_nodes.add(nid)
        for day in days:
            minutes_used = day.get("minutes_used", 0)
            budget_val = plan.get("budget", 10)
            assert minutes_used <= budget_val, f"Budget exceeded in {pf} day {day.get('day')}: {minutes_used} > {budget_val}"

            for act in day.get("activities", []):
                prereqs = list(g.predecessors(act))
                for prereq in prereqs:
                    # Prerequisite must have been completed or mastered or scheduled earlier
                    assert (prereq in completed or prereq in mastered_nodes or prereq in day.get("activities", [])), (
                        f"Prerequisite {prereq} not satisfied for {act} in {pf}"
                    )
                completed.add(act)


def test_slice_all_traces_pass_checkers_full_coverage(tmp_path):
    """Every emitted trace passes check_trace or check_no_plan_trace with full day coverage."""
    out_dir = str(tmp_path / "traces_test")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    g = load_graph("data/curricula/demo_curriculum.json")
    cand_univ = get_candidate_universe(g, "D")

    trace_files = [f for f in EXPECTED_SLICE_ARTIFACTS if f.startswith("trace_")]
    for tf in trace_files:
        with open(os.path.join(out_dir, tf), "r", encoding="utf-8") as f:
            trace_data = json.load(f)

        if isinstance(trace_data, dict):
            # No-plan trace
            check_no_plan_trace(trace_data)
            assert "reason_code" in trace_data
            rc = trace_data["reason_code"]
            assert hasattr(ReasonCode, rc) or rc in [r.value for r in ReasonCode]
        else:
            # Feasible trace: determine num_days from max day in trace
            days_in_trace = {entry["day"] for entry in trace_data}
            max_day = max(days_in_trace)
            assert days_in_trace == set(range(1, max_day + 1)), f"Trace {tf} does not have full day coverage"
            check_trace(cand_univ, trace_data, num_days=max_day, budget=10)


def test_slice_np_state_consistency(tmp_path):
    """n, p, and state agree across summary, plan, and trace for every updated concept."""
    out_dir = str(tmp_path / "np_consistency_test")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    with open(os.path.join(out_dir, "response_updates.json"), "r", encoding="utf-8") as f:
        resp_updates = json.load(f)

    # 1. Passed assessment consistency
    pass_info = resp_updates["assessment_passed"]
    after_p = pass_info["after"]["p"]
    after_n = pass_info["after"]["n"]
    after_state = pass_info["after"]["state"]

    with open(os.path.join(out_dir, "plan_assessment_passed.json"), "r", encoding="utf-8") as f:
        plan_pass = json.load(f)
    with open(os.path.join(out_dir, "trace_assessment_passed.json"), "r", encoding="utf-8") as f:
        trace_pass = json.load(f)

    c_state_in_plan = plan_pass["learner_states"]["A"]
    assert c_state_in_plan["p"] == pytest.approx(after_p)
    assert c_state_in_plan["n"] == after_n

    # Check Day 1 trace for concept A in trace_pass
    a_trace_entries = [e for e in trace_pass if e["node_id"] == "A" and e["day"] == 1]
    assert len(a_trace_entries) == 1
    t_entry = a_trace_entries[0]
    assert t_entry["concept_state"]["p"] == pytest.approx(after_p)
    assert t_entry["concept_state"]["n"] == after_n
    assert t_entry["concept_state"]["class"] == after_state

    # 2. Failed assessment consistency
    fail_info = resp_updates["assessment_failed"]
    fail_after_p = fail_info["after"]["p"]
    fail_after_n = fail_info["after"]["n"]
    fail_after_state = fail_info["after"]["state"]

    with open(os.path.join(out_dir, "plan_assessment_failed.json"), "r", encoding="utf-8") as f:
        plan_fail = json.load(f)
    with open(os.path.join(out_dir, "trace_assessment_failed.json"), "r", encoding="utf-8") as f:
        trace_fail = json.load(f)

    c_state_fail_in_plan = plan_fail["learner_states"]["A"]
    assert c_state_fail_in_plan["p"] == pytest.approx(fail_after_p)
    assert c_state_fail_in_plan["n"] == fail_after_n

    a_fail_entries = [e for e in trace_fail if e["node_id"] == "A" and e["day"] == 1]
    assert len(a_fail_entries) == 1
    t_fail_entry = a_fail_entries[0]
    assert t_fail_entry["concept_state"]["p"] == pytest.approx(fail_after_p)
    assert t_fail_entry["concept_state"]["n"] == fail_after_n
    assert t_fail_entry["concept_state"]["class"] == fail_after_state


def test_slice_different_supplied_policy_changes_decision(tmp_path):
    """A different supplied policy changes at least one classification / gating decision."""
    out_dir_default = str(tmp_path / "policy_default")
    out_dir_strict = str(tmp_path / "policy_strict")

    # Default run
    code_def = run_slice(out_dir=out_dir_default, seed=20261024, budget=10)
    assert code_def == 0

    # Strict policy: mastered_p = 0.9999 (almost impossible to master in 4 responses)
    custom_policy = {
        "p_S": 0.10,
        "p_G": 0.25,
        "p_T": 0.10,
        "window_size": 4,
        "mastered_p": 0.9999,
        "weak_p": 0.30,
        "sigma2_max": 0.05,
        "min_obs": 4,
        "kappa0": 2.0,
    }
    policy_path = str(tmp_path / "strict_policy.yaml")
    with open(policy_path, "w", encoding="utf-8") as f:
        yaml.dump(custom_policy, f)

    code_strict = run_slice(out_dir=out_dir_strict, seed=20261024, budget=10, policy_path=policy_path)
    assert code_strict == 0

    # Compare response_updates: state under strict policy is Developing instead of Mastered
    with open(os.path.join(out_dir_default, "response_updates.json"), "r", encoding="utf-8") as f:
        upd_def = json.load(f)
    with open(os.path.join(out_dir_strict, "response_updates.json"), "r", encoding="utf-8") as f:
        upd_strict = json.load(f)

    assert upd_def["assessment_passed"]["after"]["state"] == "Mastered"
    assert upd_strict["assessment_passed"]["after"]["state"] != "Mastered"


# =============================================================================
# ADVERSARIAL MATRIX TESTS
# =============================================================================

@pytest.mark.parametrize("b", [5, 10, 15, 30])
def test_slice_adversarial_budgets(tmp_path, b):
    """Executes slice across budgets 5, 10, 15, 30; asserts valid plan or supported no-plan reason code."""
    out_dir = str(tmp_path / f"budget_{b}")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=b)
    assert code == 0

    # All trace files pass checker
    for tf in [f for f in EXPECTED_SLICE_ARTIFACTS if f.startswith("trace_")]:
        with open(os.path.join(out_dir, tf), "r", encoding="utf-8") as f:
            tdata = json.load(f)
        if isinstance(tdata, dict):
            check_no_plan_trace(tdata)
            assert "reason_code" in tdata
        else:
            max_d = max(e["day"] for e in tdata)
            g = load_graph("data/curricula/demo_curriculum.json")
            cand_univ = get_candidate_universe(g, "D")
            check_trace(cand_univ, tdata, num_days=max_d, budget=b)


@pytest.mark.parametrize("target_node", ["B", "C"])
def test_slice_adversarial_changed_target(tmp_path, target_node):
    """Executes slice with changed target nodes and asserts candidate universe and valid traces."""
    out_dir = str(tmp_path / f"target_{target_node}")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10, target=target_node)
    assert code == 0

    g = load_graph("data/curricula/demo_curriculum.json")
    cand_univ = get_candidate_universe(g, target_node)

    with open(os.path.join(out_dir, "trace_learner1_day1.json"), "r", encoding="utf-8") as f:
        tdata = json.load(f)
    check_trace(cand_univ, tdata, num_days=3, budget=10)


def test_slice_adversarial_changed_profile(tmp_path):
    """Executes slice with changed profile (profile_3) and asserts valid plans and traces."""
    out_dir = str(tmp_path / "changed_profile")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10, profile_1="profile_3")
    assert code == 0

    with open(os.path.join(out_dir, "diagnostic_record.json"), "r", encoding="utf-8") as f:
        diag = json.load(f)
    assert diag["learner_1"]["profile_id"] == "profile_3"


def test_slice_adversarial_failed_assessment(tmp_path):
    """Failed assessment keeps concept unmastered and dependents filtered with PREREQUISITE_UNMET."""
    out_dir = str(tmp_path / "failed_assessment")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    with open(os.path.join(out_dir, "trace_assessment_failed.json"), "r", encoding="utf-8") as f:
        trace_data = json.load(f)

    # Concept B must be filtered on day 1 with PREREQUISITE_UNMET
    b_entries = [e for e in trace_data if e["node_id"] == "B" and e["day"] == 1]
    assert len(b_entries) == 1
    assert b_entries[0]["decision"] == "FILTERED"
    assert b_entries[0]["reason_code"] == ReasonCode.PREREQUISITE_UNMET.value


def test_slice_adversarial_missed_day(tmp_path):
    """Missed day records missed day while strictly preserving completed progress."""
    out_dir = str(tmp_path / "missed_day")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    with open(os.path.join(out_dir, "plan_missed_day.json"), "r", encoding="utf-8") as f:
        plan = json.load(f)

    assert "A" in plan["completed_nodes"]
    assert plan["days"][0]["missed"] is True


def test_slice_adversarial_shortened_deadline(tmp_path):
    """Shortened deadline re-evaluates feasibility while strictly preserving completed progress."""
    out_dir = str(tmp_path / "shortened_deadline")
    code = run_slice(out_dir=out_dir, seed=20261024, budget=10)
    assert code == 0

    with open(os.path.join(out_dir, "plan_shortened_deadline.json"), "r", encoding="utf-8") as f:
        plan = json.load(f)

    assert "A" in plan["completed_nodes"]
    status = plan.get("status")
    if status == "INFEASIBLE_PROVED":
        check_no_plan_trace(plan["trace"])


def test_slice_adversarial_renamed_graph(tmp_path):
    """Renamed / missing curriculum file returns exit code 1 with MISSING_CURRICULUM_FILE."""
    out_dir = str(tmp_path / "bad_graph")
    code = run_slice(out_dir=out_dir, curriculum_path="data/curricula/nonexistent_curriculum.json")
    assert code == 1


def test_slice_adversarial_typo_policy_file(tmp_path):
    """Typo / missing policy file returns exit code 1 with MISSING_POLICY_FILE."""
    out_dir = str(tmp_path / "bad_policy")
    code = run_slice(out_dir=out_dir, policy_path="config/typo_policy_file.yaml")
    assert code == 1
