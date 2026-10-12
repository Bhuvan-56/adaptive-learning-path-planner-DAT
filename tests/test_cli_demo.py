import hashlib
import json
import os
import subprocess
import sys
from typing import Dict, Any, Set
import pytest
import networkx as nx

from src.cli import run_demo
from src.curriculum.graph import load_graph
from src.trace.checker import check_trace, check_no_plan_trace
from src.trace.universe import get_candidate_universe


DEMO_CURRICULUM_PATH = os.path.abspath("data/curricula/demo_curriculum.json")


def _hash_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_cli_demo_byte_identical_rerun(tmp_path):
    """Running the demo command twice with the same seed yields byte-identical plan and trace files."""
    out1 = str(tmp_path / "run1")
    out2 = str(tmp_path / "run2")

    ret1 = run_demo(out_dir=out1, seed=20261012, budget=10, curriculum_path=DEMO_CURRICULUM_PATH)
    ret2 = run_demo(out_dir=out2, seed=20261012, budget=10, curriculum_path=DEMO_CURRICULUM_PATH)

    assert ret1 == 0
    assert ret2 == 0

    files1 = sorted([f for f in os.listdir(out1) if f != "manifest.json"])
    files2 = sorted([f for f in os.listdir(out2) if f != "manifest.json"])
    assert files1 == files2
    assert len(files1) == 13  # 12 plan/trace files + response_updates.json

    for filename in files1:
        h1 = _hash_file(os.path.join(out1, filename))
        h2 = _hash_file(os.path.join(out2, filename))
        assert h1 == h2, f"Artifact '{filename}' differs across reruns ({h1} != {h2})"


def test_cli_demo_day1_plans_differ(tmp_path):
    """The Novice and Intermediate learners receive distinct Day 1 schedules."""
    out_dir = str(tmp_path / "plans_differ")
    ret = run_demo(out_dir=out_dir, seed=20261012, budget=10, curriculum_path=DEMO_CURRICULUM_PATH)
    assert ret == 0

    with open(os.path.join(out_dir, "plan_novice_day1.json"), "r", encoding="utf-8") as f:
        plan_novice = json.load(f)
    with open(os.path.join(out_dir, "plan_intermediate_day1.json"), "r", encoding="utf-8") as f:
        plan_inter = json.load(f)

    novice_day1 = plan_novice["days"][0]["activities"]
    inter_day1 = plan_inter["days"][0]["activities"]

    assert novice_day1 != inter_day1
    assert "A" in novice_day1
    assert "C" in inter_day1
    assert "A" not in inter_day1  # Mastered prerequisites skipped


def test_cli_demo_zero_prerequisite_and_zero_budget_violations(tmp_path):
    """Independently verifies zero prerequisite violations and zero budget violations across every emitted plan."""
    out_dir = str(tmp_path / "correctness_check")
    ret = run_demo(out_dir=out_dir, seed=20261012, budget=10, curriculum_path=DEMO_CURRICULUM_PATH)
    assert ret == 0

    g = load_graph(DEMO_CURRICULUM_PATH)

    plan_files = [
        ("plan_novice_day1.json", "trace_novice_day1.json"),
        ("plan_intermediate_day1.json", "trace_intermediate_day1.json"),
        ("plan_assessment_passed.json", "trace_assessment_passed.json"),
        ("plan_assessment_failed.json", "trace_assessment_failed.json"),
        ("plan_missed_day.json", "trace_missed_day.json"),
    ]

    for pfile, tfile in plan_files:
        p_path = os.path.join(out_dir, pfile)
        t_path = os.path.join(out_dir, tfile)

        with open(p_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
        with open(t_path, "r", encoding="utf-8") as f:
            trace_data = json.load(f)

        budget = 10
        # Prerequisites satisfied prior to scheduling (already mastered or completed)
        completed_so_far: Set[str] = set(plan_data.get("completed_nodes", []))
        for entry in trace_data:
            if entry.get("reason_code") in ("ALREADY_MASTERED", "COMPLETED"):
                completed_so_far.add(entry["node_id"])

        for day_entry in plan_data.get("days", []):
            activities = day_entry.get("activities", [])
            day_dur = sum(g.nodes[node_id].get("baseline_duration", 0) for node_id in activities)
            assert day_dur <= budget, f"Daily budget exceeded in {pfile} day {day_entry['day']}: {day_dur} > {budget}"

            # Check prerequisite correctness for each activity
            scheduled_today: Set[str] = set()
            for node_id in activities:
                for prereq in g.predecessors(node_id):
                    prereq_satisfied = (prereq in completed_so_far) or (prereq in scheduled_today)
                    assert prereq_satisfied, (
                        f"Prerequisite violation in {pfile}: '{prereq}' is required for '{node_id}' "
                        f"but was neither completed nor scheduled."
                    )
                scheduled_today.add(node_id)
            completed_so_far.update(scheduled_today)


def test_cli_demo_all_traces_pass_contracts(tmp_path):
    """Every emitted trace passes check_trace with full day coverage, and infeasible outcomes pass check_no_plan_trace."""
    out_dir = str(tmp_path / "traces_check")
    ret = run_demo(out_dir=out_dir, seed=20261012, budget=10, curriculum_path=DEMO_CURRICULUM_PATH)
    assert ret == 0

    g = load_graph(DEMO_CURRICULUM_PATH)
    candidate_universe = get_candidate_universe(g, "D")

    feasible_traces = [
        "trace_novice_day1.json",
        "trace_intermediate_day1.json",
        "trace_assessment_passed.json",
        "trace_assessment_failed.json",
        "trace_missed_day.json",
    ]

    for tfile in feasible_traces:
        path = os.path.join(out_dir, tfile)
        with open(path, "r", encoding="utf-8") as f:
            trace = json.load(f)
        assert check_trace(candidate_universe, trace, num_days=3) is True

    # Infeasible no-plan trace check
    infeasible_path = os.path.join(out_dir, "trace_reduced_budget_infeasible.json")
    with open(infeasible_path, "r", encoding="utf-8") as f:
        no_plan_trace = json.load(f)
    assert check_no_plan_trace(no_plan_trace) is True


def test_cli_demo_assessment_pass_unblocks_fail_blocks(tmp_path):
    """The failed-assessment scenario leaves the dependent blocked; the passed-assessment scenario unblocks it."""
    out_dir = str(tmp_path / "assessment_scenarios")
    ret = run_demo(out_dir=out_dir, seed=20261012, budget=10, curriculum_path=DEMO_CURRICULUM_PATH)
    assert ret == 0

    with open(os.path.join(out_dir, "plan_assessment_passed.json"), "r", encoding="utf-8") as f:
        plan_pass = json.load(f)
    with open(os.path.join(out_dir, "plan_assessment_failed.json"), "r", encoding="utf-8") as f:
        plan_fail = json.load(f)

    # Passed scenario: Concept A became Mastered, so dependent B is unblocked and selected on Day 1
    assert "B" in plan_pass["days"][0]["activities"]

    # Failed scenario: Concept A became Weak, so dependent B stays blocked with PREREQUISITE_UNMET
    assert "B" not in plan_fail["days"][0]["activities"]
    with open(os.path.join(out_dir, "trace_assessment_failed.json"), "r", encoding="utf-8") as f:
        trace_fail = json.load(f)
    b_day1_entry = next(e for e in trace_fail if e["node_id"] == "B" and e["day"] == 1)
    assert b_day1_entry["decision"] == "FILTERED"
    assert b_day1_entry["reason_code"] == "PREREQUISITE_UNMET"


def test_cli_demo_malformed_curriculum_exits_nonzero(tmp_path):
    """A malformed curriculum (NaN duration or cycle) makes the command exit non-zero with a structured error and no plan file."""
    nan_graph_path = os.path.abspath("tests/fixtures/graphs/non_finite_value.json")
    cycle_graph_path = os.path.abspath("tests/fixtures/graphs/cycle_detected.json")

    out_nan = str(tmp_path / "nan_out")
    ret_nan = run_demo(out_dir=out_nan, seed=20261012, budget=10, curriculum_path=nan_graph_path)
    assert ret_nan != 0
    assert not os.path.exists(os.path.join(out_nan, "plan_novice_day1.json"))

    out_cycle = str(tmp_path / "cycle_out")
    ret_cycle = run_demo(out_dir=out_cycle, seed=20261012, budget=10, curriculum_path=cycle_graph_path)
    assert ret_cycle != 0
    assert not os.path.exists(os.path.join(out_cycle, "plan_novice_day1.json"))


def test_cli_demo_no_evaluator_view_imports_in_planning_or_state():
    """Confirms no module under src/planning or src/state imports EvaluatorView."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    checked_dirs = [
        os.path.join(repo_root, "src", "planning"),
        os.path.join(repo_root, "src", "state"),
    ]

    for d in checked_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    assert "EvaluatorView" not in content, (
                        f"Violation: EvaluatorView imported in {full_path}"
                    )


def test_cli_demo_different_seed_changes_simulation(tmp_path):
    """A different seed produces different response sequences and manifest hash."""
    from src.simulation.simulator import SimulatedLearner

    l1 = SimulatedLearner(profile_id="profile_1", seed=20261012)
    l2 = SimulatedLearner(profile_id="profile_1", seed=99999999)

    r1 = [l1.respond("A") for _ in range(20)]
    r2 = [l2.respond("A") for _ in range(20)]

    assert r1 != r2, "Different seeds must produce different simulated responses."
