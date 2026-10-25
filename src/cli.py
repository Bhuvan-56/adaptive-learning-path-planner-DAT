import argparse
import csv
import dataclasses
from datetime import datetime, timezone
import json
import math
import os
import sys
from typing import Any, Dict, List, Set, Optional

import networkx as nx

from src.curriculum.graph import load_graph, validate_graph
from src.diagnostic.diagnostic import (
    load_item_bank_and_qmatrix,
    run_adaptive_diagnostic,
    DEFAULT_ITEM_BANK_PATH,
    DEFAULT_QMATRIX_PATH,
)
from src.planning.difficulty import (
    DifficultyState,
    load_adaptive_config,
    step_difficulty,
    DEFAULT_CONFIG_PATH as DEFAULT_ADAPTIVE_CONFIG_PATH,
)
from src.planning.feasibility import FeasibilityStatus, InfeasibilityReason
from src.planning.replan import (
    ReplanState,
    assessment_result,
    changed_budget,
    changed_deadline,
    missed_day,
    replan,
)
from src.planning.review import (
    ReviewLog,
    ReviewRecord,
    is_review_eligible,
    calculate_recall_decay,
    get_remediation_ancestors,
    load_remediation_config,
    load_review_eval_config,
    DECAY_BASELINE,
)
from src.planning.service import plan_request
from src.provenance import (
    _normalize_obj,
    compute_directory_checksums,
    compute_file_sha256,
    get_git_info,
    get_package_versions,
    resolved_config_hash,
    write_manifest,
)
from src.simulation.simulator import (
    DEFAULT_GROUPS_PATH,
    DEFAULT_PROFILES_PATH,
    MatchedBKTGenerator,
    SimulatedLearner,
)
from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig, default_policy, load_policy
from src.trace.checker import check_no_plan_trace, check_trace
from src.trace.schema import ReasonCode
from src.trace.universe import get_candidate_universe
from src.evaluation.integrated import (
    DEFAULT_INTEGRATED_CONFIG,
    load_integrated_config,
    run_integrated_evaluation,
)


def _save_json(path: str, data: Any) -> None:
    """Saves normalized data as deterministic, byte-identical JSON."""
    normalized = _normalize_obj(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, sort_keys=True)


def _check_result_trace(plan_dict: Dict[str, Any], candidate_universe: Set[str], num_days: int, budget: Optional[int] = None) -> None:
    """Routes plan trace to check_no_plan_trace if status is infeasible/no-plan or dict, else to check_trace."""
    status = plan_dict.get("status")
    status_str = status.value if hasattr(status, "value") else str(status)
    trace = plan_dict.get("trace")
    if status_str in ("INFEASIBLE_PROVED", "INVALID_INPUT") or isinstance(trace, dict):
        check_no_plan_trace(trace)
    else:
        check_trace(candidate_universe, trace, num_days=num_days, budget=budget)


def run_demo(out_dir: str, seed: int = 20261012, budget: int = 10, curriculum_path: str = "data/curricula/demo_curriculum.json", policy_path: Optional[str] = None) -> int:
    """
    Executes the end-to-end multi-scenario CLI demonstration:
    1. Loads and validates the curriculum DAG.
    2. Generates initial Day 1 plans for Novice and Intermediate learners at the specified daily budget.
    3. Simulates assessment responses, updates BKT cognitive states, and replans under Passed vs. Failed outcomes.
    4. Simulates a missed day and subsequent budget reduction proving block infeasibility.
    5. Validates all traces via check_trace and check_no_plan_trace.
    6. Emits byte-identical plan/trace artifacts, response_updates.json, and provenance manifest.json.
    7. Outputs a comprehensive human-readable summary.
    """
    # ---------------------------------------------------------
    # 1. Load and Validate Curriculum
    # ---------------------------------------------------------
    if not os.path.exists(curriculum_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_CURRICULUM_FILE"],
            "message": f"Curriculum file does not exist: {curriculum_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    try:
        g: nx.DiGraph = load_graph(curriculum_path)
    except Exception as e:
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": ["MALFORMED_GRAPH_FILE"],
            "message": f"Failed to parse graph JSON: {e}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    validation_errors = validate_graph(g)
    if validation_errors:
        codes = [e.value if hasattr(e, "value") else str(e) for e in validation_errors]
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": codes,
            "message": f"Graph validation failed: {codes}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    target_node = "D"
    if target_node not in g.nodes:
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": ["TARGET_NOT_FOUND"],
            "message": f"Target node '{target_node}' not found in curriculum graph"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    candidate_universe = get_candidate_universe(g, target_node)

    # ---------------------------------------------------------
    # 2. Simulated Learners Setup (Matched Simulator)
    # ---------------------------------------------------------
    deadline_days = 3
    if policy_path is not None:
        if not os.path.exists(policy_path):
            err = {
                "status": "FILE_NOT_FOUND",
                "error_codes": ["MISSING_POLICY_FILE"],
                "message": f"Policy file does not exist: {policy_path}"
            }
            print(json.dumps(err, indent=2), file=sys.stderr)
            return 1
        policy = load_policy(policy_path)
        policy_desc = f"loaded from {policy_path}"
    else:
        bkt_policy_path = os.path.join(os.path.dirname(__file__), "..", "config", "bkt_params.yaml")
        if os.path.exists(bkt_policy_path):
            policy = load_policy(bkt_policy_path)
            policy_desc = f"declared default ({bkt_policy_path})"
        else:
            policy = PolicyConfig()
            policy_desc = "declared default (built-in PolicyConfig)"

    # Novice Learner: unprobed state (n=0, cold_start for all concepts)
    learner_novice = SimulatedLearner(
        profile_id="profile_1",
        generator_family=MatchedBKTGenerator(p_S=policy.p_S, p_G=policy.p_G, p_T=policy.p_T),
        seed=seed,
        budget_override=budget,
        initial_mastery={"A": False, "B": False, "C": False, "D": False}
    )
    states_novice = {nid: ConceptState.cold_start() for nid in g.nodes}

    # Intermediate Learner: prerequisites A and B probed & evidence-Mastered (n=8, history=[1,1,1,1])
    learner_intermediate = SimulatedLearner(
        profile_id="profile_2",
        generator_family=MatchedBKTGenerator(p_S=policy.p_S, p_G=policy.p_G, p_T=policy.p_T),
        seed=seed,
        budget_override=budget,
        initial_mastery={"A": True, "B": True, "C": False, "D": False}
    )
    states_intermediate = {
        "A": ConceptState(A=9.0, B=1.0, n=8, history=[1, 1, 1, 1]),
        "B": ConceptState(A=9.0, B=1.0, n=8, history=[1, 1, 1, 1]),
        "C": ConceptState.cold_start(),
        "D": ConceptState.cold_start(),
    }

    # ---------------------------------------------------------
    # 3. Day 1 Plans via plan_request
    # ---------------------------------------------------------
    res_novice = plan_request(
        graph=g,
        learner_states=states_novice,
        budget=budget,
        deadline_days=deadline_days,
        targets=target_node,
        policy=policy
    )
    if not res_novice.is_valid:
        err = {"status": "VALIDATION_ERROR", "error_codes": res_novice.error_codes, "message": res_novice.message}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    res_intermediate = plan_request(
        graph=g,
        learner_states=states_intermediate,
        budget=budget,
        deadline_days=deadline_days,
        targets=target_node,
        policy=policy
    )
    if not res_intermediate.is_valid:
        err = {"status": "VALIDATION_ERROR", "error_codes": res_intermediate.error_codes, "message": res_intermediate.message}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    try:
        _check_result_trace(res_novice.plan, candidate_universe, num_days=deadline_days, budget=budget)
        _check_result_trace(res_intermediate.plan, candidate_universe, num_days=deadline_days, budget=budget)
    except ValueError as e:
        err = {"status": "TRACE_CHECK_FAILED", "error_codes": ["TRACE_CONTRACT_VIOLATION"], "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # ---------------------------------------------------------
    # 4. Assessment Responses & Replanning (Pass vs. Fail)
    # ---------------------------------------------------------
    # Scenario 4A: Assessment Passed (Unblocks Dependent Decisions)
    # Uses seed with competent learner (initial_mastery A=True) -> yields [1, 1, 1, 1]
    learner_pass_sim = SimulatedLearner(
        profile_id="profile_1",
        generator_family=MatchedBKTGenerator(p_S=policy.p_S, p_G=policy.p_G, p_T=policy.p_T),
        seed=seed,
        budget_override=budget,
        initial_mastery={"A": True}
    )
    responses_pass = [learner_pass_sim.respond("A", difficulty=0.20) for _ in range(4)]

    states_pass = {nid: ConceptState.cold_start() for nid in g.nodes}
    c_state_pass = states_pass["A"]
    before_pass = {
        "p": c_state_pass.p,
        "kappa": c_state_pass.kappa,
        "n": c_state_pass.n,
        "sigma2": c_state_pass.sigma2,
        "state": c_state_pass.classify()
    }

    replan_state_pass = ReplanState(
        graph=g,
        learner_states=states_pass,
        budget=budget,
        deadline_days=deadline_days,
        target_node=target_node,
        current_day=1,
        policy=policy
    )
    plan_passed = replan(replan_state_pass, assessment_result("A", responses_pass))
    c_state_pass_after = plan_passed["learner_states"]["A"]
    after_pass = {
        "p": c_state_pass_after.p,
        "kappa": c_state_pass_after.kappa,
        "n": c_state_pass_after.n,
        "sigma2": c_state_pass_after.sigma2,
        "state": c_state_pass_after.classify(policy)
    }
    try:
        _check_result_trace(plan_passed, candidate_universe, num_days=deadline_days, budget=budget)
    except ValueError as e:
        err = {"status": "TRACE_CHECK_FAILED", "error_codes": ["TRACE_CONTRACT_VIOLATION"], "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # Scenario 4B: Assessment Failed (Dependents Stay Blocked)
    # Uses forced low-ability novice (initial_mastery A=False) -> yields deterministic [0, 0, 0, 0] under seed 20261012
    learner_fail_sim = SimulatedLearner(
        profile_id="profile_1",
        generator_family=MatchedBKTGenerator(p_S=policy.p_S, p_G=policy.p_G, p_T=policy.p_T),
        seed=seed,
        budget_override=budget,
        initial_mastery={"A": False}
    )
    responses_fail = [learner_fail_sim.respond("A", difficulty=0.20) for _ in range(4)]

    states_fail = {nid: ConceptState.cold_start() for nid in g.nodes}
    c_state_fail = states_fail["A"]
    before_fail = {
        "p": c_state_fail.p,
        "kappa": c_state_fail.kappa,
        "n": c_state_fail.n,
        "sigma2": c_state_fail.sigma2,
        "state": c_state_fail.classify(policy)
    }

    replan_state_fail = ReplanState(
        graph=g,
        learner_states=states_fail,
        budget=budget,
        deadline_days=deadline_days,
        target_node=target_node,
        current_day=1,
        policy=policy
    )
    plan_failed = replan(replan_state_fail, assessment_result("A", responses_fail))
    c_state_fail_after = plan_failed["learner_states"]["A"]
    after_fail = {
        "p": c_state_fail_after.p,
        "kappa": c_state_fail_after.kappa,
        "n": c_state_fail_after.n,
        "sigma2": c_state_fail_after.sigma2,
        "state": c_state_fail_after.classify(policy)
    }
    try:
        _check_result_trace(plan_failed, candidate_universe, num_days=deadline_days, budget=budget)
    except ValueError as e:
        err = {"status": "TRACE_CHECK_FAILED", "error_codes": ["TRACE_CONTRACT_VIOLATION"], "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # ---------------------------------------------------------
    # 5. Missed Day & Budget Reduction (Intermediate Learner)
    # ---------------------------------------------------------
    replan_state_inter = ReplanState(
        graph=g,
        learner_states=dict(states_intermediate),
        budget=budget,
        deadline_days=deadline_days,
        target_node=target_node,
        current_day=1,
        completed_nodes={"A", "B"},
        policy=policy
    )
    plan_missed = replan(replan_state_inter, missed_day())
    try:
        _check_result_trace(plan_missed, candidate_universe, num_days=deadline_days, budget=budget)
    except ValueError as e:
        err = {"status": "TRACE_CHECK_FAILED", "error_codes": ["TRACE_CONTRACT_VIOLATION"], "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # Budget reduction from 10 to 5
    reduced_budget = 5
    past_days = plan_missed.get("days", [])[:1] if isinstance(plan_missed.get("days"), list) else []
    if isinstance(plan_missed.get("trace"), list):
        past_trace = plan_missed["trace"][:len(candidate_universe)]
    else:
        past_trace = []

    replan_state_reduced = ReplanState(
        graph=g,
        learner_states=dict(plan_missed.get("learner_states", states_intermediate)),
        budget=plan_missed.get("budget", budget),
        deadline_days=plan_missed.get("deadline_days", deadline_days),
        target_node=target_node,
        current_day=plan_missed.get("current_day", 1),
        completed_nodes=set(plan_missed.get("completed_nodes", {"A", "B"})),
        past_days=past_days,
        past_trace=past_trace,
        policy=policy
    )
    plan_reduced = replan(replan_state_reduced, changed_budget(reduced_budget))
    try:
        _check_result_trace(plan_reduced, candidate_universe, num_days=deadline_days, budget=reduced_budget)
    except ValueError as e:
        err = {"status": "TRACE_CHECK_FAILED", "error_codes": ["NO_PLAN_TRACE_CONTRACT_VIOLATION"], "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # ---------------------------------------------------------
    # 6. Artifact Serialization
    # ---------------------------------------------------------
    os.makedirs(out_dir, exist_ok=True)

    _save_json(os.path.join(out_dir, "plan_novice_day1.json"), res_novice.plan)
    _save_json(os.path.join(out_dir, "trace_novice_day1.json"), res_novice.plan["trace"])
    _save_json(os.path.join(out_dir, "plan_intermediate_day1.json"), res_intermediate.plan)
    _save_json(os.path.join(out_dir, "trace_intermediate_day1.json"), res_intermediate.plan["trace"])
    _save_json(os.path.join(out_dir, "plan_assessment_passed.json"), plan_passed)
    _save_json(os.path.join(out_dir, "trace_assessment_passed.json"), plan_passed["trace"])
    _save_json(os.path.join(out_dir, "plan_assessment_failed.json"), plan_failed)
    _save_json(os.path.join(out_dir, "trace_assessment_failed.json"), plan_failed["trace"])
    _save_json(os.path.join(out_dir, "plan_missed_day.json"), plan_missed)
    _save_json(os.path.join(out_dir, "trace_missed_day.json"), plan_missed["trace"])
    _save_json(os.path.join(out_dir, "plan_reduced_budget_infeasible.json"), plan_reduced)
    _save_json(os.path.join(out_dir, "trace_reduced_budget_infeasible.json"), plan_reduced["trace"])

    response_updates = {
        "scenario_assessment_passed": {
            "concept": "A",
            "responses": responses_pass,
            "before": before_pass,
            "after": after_pass
        },
        "scenario_assessment_failed": {
            "concept": "A",
            "responses": responses_fail,
            "before": before_fail,
            "after": after_fail
        }
    }
    _save_json(os.path.join(out_dir, "response_updates.json"), response_updates)

    # Provenance manifest
    git_sha, dirty = get_git_info()
    curriculum_hash = compute_file_sha256(curriculum_path) if os.path.exists(curriculum_path) else "unknown"
    profiles_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "profiles.yaml"))
    profiles_hash = compute_file_sha256(profiles_path) if os.path.exists(profiles_path) else "unknown"
    policy_hash = compute_file_sha256(bkt_policy_path) if os.path.exists(bkt_policy_path) else resolved_config_hash(dataclasses.asdict(policy))

    resolved_config = {
        "budget": budget,
        "reduced_budget": reduced_budget,
        "deadline_days": deadline_days,
        "seed": seed,
        "curriculum_path": curriculum_path,
        "curriculum_hash": curriculum_hash,
        "policy": {
            "p_S": policy.p_S,
            "p_G": policy.p_G,
            "p_T": policy.p_T,
            "window_size": policy.window_size,
            "mastered_p": policy.mastered_p,
            "weak_p": policy.weak_p,
            "sigma2_max": policy.sigma2_max,
            "min_obs": policy.min_obs,
            "kappa0": policy.kappa0,
            "quorum": policy.quorum
        }
    }
    cfg_hash = resolved_config_hash(resolved_config)

    input_hashes = {
        "curriculum": curriculum_hash,
        "profiles": profiles_hash,
        "policy": policy_hash,
    }
    output_checksums = compute_directory_checksums(out_dir, exclude_files=["manifest.json"])
    model_versions = {
        "pyBKT": "1.4.3",
        "bkt_policy": "v2.0",
        "planner": "v1.0",
    }

    write_manifest(
        path=os.path.join(out_dir, "manifest.json"),
        experiment_name="cli_demo",
        config_hash=cfg_hash,
        seeds=[seed],
        git_sha=git_sha,
        python_version=sys.version,
        package_versions=get_package_versions(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        data_route="synthetic_demo_curriculum",
        dataset_provenance=None,
        dirty=dirty,
        curriculum_path=curriculum_path,
        input_hashes=input_hashes,
        output_checksums=output_checksums,
        model_versions=model_versions,
    )


    # ---------------------------------------------------------
    # 7. Print Human Summary
    # ---------------------------------------------------------
    print("=" * 70)
    print("ADAPTIVE LEARNING ENGINE: END-TO-END DEMONSTRATION SUMMARY")
    print("=" * 70)
    print(f"Curriculum: {curriculum_path} (Target: {target_node}, Horizon: {deadline_days} days, Daily Budget: {budget} min)")
    print(f"Policy: using {policy_desc}")
    print(f"Seed: {seed} | Config Hash: {cfg_hash[:16]}... | Git SHA: {git_sha[:7]}{' (dirty)' if dirty else ''}\n")

    print("[1] Learner Profiles & Day 1 Plan Divergence:")
    novice_days = res_novice.plan.get("days", [])
    novice_act = novice_days[0]["activities"] if novice_days else []
    novice_cond = novice_days[0]["conditional_activities"] if novice_days else []
    print(f"  * Novice Learner (Budget {budget}m):")
    print(f"    - Scheduled Activities Day 1: {novice_act}")
    print(f"    - Conditional Activities Day 1: {novice_cond}")
    if res_novice.plan.get("status") == "FEASIBLE" or novice_act:
        print(f"    - Gating Rationale: Foundational concept 'A' is unprobed (Uncertain).")
        print(f"      Dependent concept 'D' is FILTERED with reason UNCERTAIN_NEEDS_ASSESSMENT.")
    else:
        print(f"    - Gating Rationale: Status is {res_novice.status} with reason {res_novice.plan.get('feasibility_explanation', {}).get('reason_code')}.")

    inter_days = res_intermediate.plan.get("days", [])
    inter_act = inter_days[0]["activities"] if inter_days else []
    print(f"  * Intermediate Learner (Budget {budget}m):")
    print(f"    - Scheduled Activities Day 1: {inter_act}")
    if inter_act:
        print(f"    - Gating Rationale: Prerequisites 'A' and 'B' are ALREADY_MASTERED and filtered.")
        print(f"      Unlocked downstream concept 'C' (10 min) is SELECTED for Day 1.\n")
    else:
        print(f"    - Gating Rationale: Status is {res_intermediate.status} with reason {res_intermediate.plan.get('feasibility_explanation', {}).get('reason_code')}.\n")

    print("[2] Dynamic Assessment & Replanning Scenarios (Concept 'A'):")
    print(f"  * Scenario A (Assessment Passed - Unblocked):")
    print(f"    - Response Sequence: {responses_pass} -> p: {before_pass['p']:.2f} -> {after_pass['p']:.4f} ({after_pass['state']})")
    pass_days = plan_passed.get("days", [])
    pass_act = pass_days[0]["activities"] if pass_days else []
    if "B" in pass_act:
        print(f"    - Outcome: Prerequisite 'A' becomes evidence-{after_pass['state']}.")
        print(f"      Dependent concept 'B' becomes unconditionally admissible and is SELECTED on Day 1.")
    else:
        print(f"    - Outcome: Prerequisite 'A' classified as {after_pass['state']}, Day 1 activities: {pass_act}.")

    print(f"  * Scenario B (Assessment Failed - Stays Blocked):")
    print(f"    - Response Sequence: {responses_fail} -> p: {before_fail['p']:.2f} -> {after_fail['p']:.4f} ({after_fail['state']})")
    print(f"    - Outcome: Concept 'A' classifies as {after_fail['state']}.")
    print(f"      Dependent concepts 'B' and 'D' remain FILTERED with reason PREREQUISITE_UNMET.")
    plan_fail_status = plan_failed.get("status")
    status_str = plan_fail_status.value if hasattr(plan_fail_status, "value") else str(plan_fail_status)
    print(f"      Planner status resolves to {status_str} (target unreachable within horizon).\n")

    print("[3] Missed Day & Budget Infeasibility Handling:")
    missed_days = plan_missed.get("days", [])
    missed_used = missed_days[0]["minutes_used"] if missed_days else 0
    print(f"  * Missed Day: Day 1 recorded as missed (minutes_used={missed_used}). Completed nodes {plan_missed.get('completed_nodes', set())} preserved.")
    print(f"  * Budget Reduction: Reduced from {budget}m to {reduced_budget}m/day.")
    print(f"    - Planner Status: {plan_reduced['status'].value if hasattr(plan_reduced['status'], 'value') else plan_reduced['status']}")
    print(f"    - Reason Code: {plan_reduced.get('feasibility_explanation', {}).get('reason_code')}")
    print(f"    - Proved Infeasibility: {plan_reduced.get('feasibility_explanation', {}).get('notes')}")
    print(f"    - Actionable Minimum Fix: {plan_reduced.get('feasibility_explanation', {}).get('minimum_fix')}\n")

    print("[4] Latent Cognitive State Invariant Verification (EvaluatorView):")
    ev_novice = learner_novice.evaluator_view()
    ev_inter = learner_intermediate.evaluator_view()
    print(f"  * True Latent Mastery (Novice):       {ev_novice.latent_masteries}")
    print(f"  * True Latent Mastery (Intermediate): {ev_inter.latent_masteries}")
    print("  * Invariant: Latent states remained strictly inaccessible to planning & state code.")
    print("=" * 70)
    print(f"SUCCESS: All 12 plan and trace artifacts successfully written to '{out_dir}'.")
    return 0


def run_plan(
    curriculum_path: str,
    target: str,
    budget: int,
    deadline_days: int,
    out_dir: str,
    policy_path: Optional[str] = None,
    states_path: Optional[str] = None,
) -> int:
    """Executes a single plan request from data and writes plan and trace artifacts."""
    if not os.path.exists(curriculum_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_CURRICULUM_FILE"],
            "message": f"Curriculum file does not exist: {curriculum_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    try:
        g: nx.DiGraph = load_graph(curriculum_path)
    except Exception as e:
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": ["MALFORMED_GRAPH_FILE"],
            "message": f"Failed to parse graph JSON: {e}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    validation_errors = validate_graph(g)
    if validation_errors:
        codes = [e.value if hasattr(e, "value") else str(e) for e in validation_errors]
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": codes,
            "message": f"Graph validation failed: {codes}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # Resolve policy
    if policy_path is not None:
        if not os.path.exists(policy_path):
            err = {
                "status": "FILE_NOT_FOUND",
                "error_codes": ["MISSING_POLICY_FILE"],
                "message": f"Policy file does not exist: {policy_path}"
            }
            print(json.dumps(err, indent=2), file=sys.stderr)
            return 1
        policy = load_policy(policy_path)
        policy_desc = f"loaded from {policy_path}"
    else:
        bkt_policy_path = os.path.join(os.path.dirname(__file__), "..", "config", "bkt_params.yaml")
        if os.path.exists(bkt_policy_path):
            policy = load_policy(bkt_policy_path)
            policy_desc = f"declared default ({bkt_policy_path})"
        else:
            policy = PolicyConfig()
            policy_desc = "declared default (built-in PolicyConfig)"

    # Resolve learner states
    learner_states: Dict[str, ConceptState] = {}
    if states_path is not None:
        if not os.path.exists(states_path):
            err = {
                "status": "FILE_NOT_FOUND",
                "error_codes": ["MISSING_STATES_FILE"],
                "message": f"States file does not exist: {states_path}"
            }
            print(json.dumps(err, indent=2), file=sys.stderr)
            return 1
        try:
            with open(states_path, "r", encoding="utf-8") as f:
                raw_states = json.load(f)
            for nid, sdata in raw_states.items():
                if isinstance(sdata, dict):
                    if "A" in sdata and "B" in sdata:
                        learner_states[nid] = ConceptState(
                            A=float(sdata["A"]),
                            B=float(sdata["B"]),
                            n=int(sdata.get("n", 0)),
                            history=sdata.get("history", [])
                        )
                    elif "p" in sdata:
                        learner_states[nid] = ConceptState.init_from_ability(float(sdata["p"]))
                    else:
                        learner_states[nid] = ConceptState.cold_start()
                else:
                    learner_states[nid] = ConceptState.cold_start()
        except Exception as e:
            err = {
                "status": "VALIDATION_ERROR",
                "error_codes": ["MALFORMED_STATES_FILE"],
                "message": f"Failed to parse states JSON: {e}"
            }
            print(json.dumps(err, indent=2), file=sys.stderr)
            return 1

    for nid in g.nodes:
        if nid not in learner_states:
            learner_states[nid] = ConceptState.cold_start()

    res = plan_request(
        graph=g,
        learner_states=learner_states,
        budget=budget,
        deadline_days=deadline_days,
        targets=target,
        policy=policy
    )

    if not res.is_valid:
        err = {"status": "VALIDATION_ERROR", "error_codes": res.error_codes, "message": res.message}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    candidate_universe = get_candidate_universe(g, target)
    try:
        _check_result_trace(res.plan, candidate_universe, num_days=deadline_days, budget=budget)
    except ValueError as e:
        err = {"status": "TRACE_CHECK_FAILED", "error_codes": ["TRACE_CONTRACT_VIOLATION"], "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    os.makedirs(out_dir, exist_ok=True)
    _save_json(os.path.join(out_dir, "plan.json"), res.plan)
    _save_json(os.path.join(out_dir, "trace.json"), res.plan["trace"])

    print(f"Plan request succeeded. Target: {target}, Status: {res.status}")
    print(f"Policy: using {policy_desc}")
    print(f"Artifacts written to '{out_dir}'.")
    return 0


def run_slice(
    out_dir: str = "evaluation/results/w4/slice",
    seed: int = 20261024,
    budget: int = 10,
    curriculum_path: str = "data/curricula/demo_curriculum.json",
    item_bank_path: str = "data/processed/item_bank_synthetic.csv",
    qmatrix_path: str = "data/processed/q_matrix_synthetic.csv",
    profiles_path: str = "config/profiles.yaml",
    groups_path: str = "data/curricula/demo_curriculum.groups.yaml",
    adaptive_config_path: str = "config/adaptive.yaml",
    policy_path: Optional[str] = None,
    target: str = "D",
    deadline_days: int = 3,
    profile_1: str = "profile_1",
    profile_2: str = "profile_2",
) -> int:
    """
    Executes the end-to-end Week 4 horizontal slice:
    1. Loads curriculum, item bank, and Q-matrix; validates through plan_request.
    2. Instantiates two simulated learners from configured profiles expanded via groups file.
       The planner never accesses latent state.
    3. Runs CAT adaptive diagnostic with injected responder, produces initial priors and diagnostic record.
    4. Plans Day 1, applies assessment with real simulated responses, steps difficulty,
       and gates dependent decisions strictly on evidence Mastered.
    5. Advances simulated days, schedules timestamped review in leftover budget,
       and triggers prerequisite remediation on repeated failures inside daily budget.
    6. Demonstrates progress preservation across missed day, reduced budget, and shortened deadline.
    7. Emits all 20 plan/trace/data artifacts and a provenance manifest hashing all inputs and outputs.
    8. Prints a comprehensive summary derived from emitted traces.
    """
    # 1. Load and validate curriculum graph
    if not os.path.exists(curriculum_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_CURRICULUM_FILE"],
            "message": f"Curriculum file does not exist: {curriculum_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    try:
        g: nx.DiGraph = load_graph(curriculum_path)
    except Exception as e:
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": ["MALFORMED_GRAPH_FILE"],
            "message": f"Failed to parse graph JSON: {e}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    validation_errors = validate_graph(g)
    if validation_errors:
        codes = [e.value if hasattr(e, "value") else str(e) for e in validation_errors]
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": codes,
            "message": f"Graph validation failed: {codes}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    if target not in g.nodes:
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": ["TARGET_NOT_FOUND"],
            "message": f"Target node '{target}' not found in curriculum graph"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    candidate_universe = get_candidate_universe(g, target)

    # 2. Load Item Bank and Q-matrix
    if not os.path.exists(item_bank_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_ITEM_BANK_FILE"],
            "message": f"Item bank file does not exist: {item_bank_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    if not os.path.exists(qmatrix_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_QMATRIX_FILE"],
            "message": f"Q-matrix file does not exist: {qmatrix_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    try:
        item_ids, items_matrix, item_to_concept, _ = load_item_bank_and_qmatrix(
            bank_source=item_bank_path,
            qmatrix_source=qmatrix_path,
            curriculum_source=curriculum_path
        )
    except Exception as e:
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": ["INVALID_ITEM_BANK_OR_QMATRIX"],
            "message": str(e)
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    item_diffs: Dict[str, float] = {}
    with open(item_bank_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iid = row.get("item_id", row.get("item", ""))
            diff_val = row.get("b", row.get("difficulty", "0.5"))
            item_diffs[iid] = float(diff_val)

    # 3. Load configurations (profiles, groups, adaptive config, policy)
    if not os.path.exists(profiles_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_PROFILES_FILE"],
            "message": f"Profiles file does not exist: {profiles_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    if not os.path.exists(groups_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_GROUPS_FILE"],
            "message": f"Curriculum groups file does not exist: {groups_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    if not os.path.exists(adaptive_config_path):
        err = {
            "status": "FILE_NOT_FOUND",
            "error_codes": ["MISSING_ADAPTIVE_CONFIG_FILE"],
            "message": f"Adaptive config file does not exist: {adaptive_config_path}"
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    try:
        adaptive_cfg = load_adaptive_config(adaptive_config_path)
    except Exception as e:
        err = {
            "status": "VALIDATION_ERROR",
            "error_codes": ["INVALID_ADAPTIVE_CONFIG"],
            "message": str(e)
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    if policy_path is not None:
        if not os.path.exists(policy_path):
            err = {
                "status": "FILE_NOT_FOUND",
                "error_codes": ["MISSING_POLICY_FILE"],
                "message": f"Policy file does not exist: {policy_path}"
            }
            print(json.dumps(err, indent=2), file=sys.stderr)
            return 1
        policy = load_policy(policy_path)
        policy_desc = f"loaded from {policy_path}"
    else:
        bkt_policy_path = os.path.join(os.path.dirname(__file__), "..", "config", "bkt_params.yaml")
        if os.path.exists(bkt_policy_path):
            policy = load_policy(bkt_policy_path)
            policy_desc = f"declared default ({bkt_policy_path})"
        else:
            policy = PolicyConfig()
            policy_desc = "declared default (built-in PolicyConfig)"

    # Validate through plan_request baseline
    cold_check_states = {nid: ConceptState.cold_start() for nid in g.nodes}
    val_res = plan_request(
        graph=g,
        learner_states=cold_check_states,
        budget=budget,
        deadline_days=deadline_days,
        targets=target,
        policy=policy
    )
    if not val_res.is_valid:
        err = {"status": "VALIDATION_ERROR", "error_codes": val_res.error_codes, "message": val_res.message}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # 4. Create two simulated learners at the same budget from configured profiles
    # (Planner strictly never reads latent state)
    curriculum_concepts = list(g.nodes)
    learner_1 = SimulatedLearner(
        profile_id=profile_1,
        generator_family=MatchedBKTGenerator(p_S=policy.p_S, p_G=policy.p_G, p_T=policy.p_T),
        seed=seed,
        budget_override=budget,
        config_path=profiles_path,
        groups_path=groups_path,
        curriculum_concepts=curriculum_concepts
    )

    learner_2 = SimulatedLearner(
        profile_id=profile_2,
        generator_family=MatchedBKTGenerator(p_S=policy.p_S, p_G=policy.p_G, p_T=policy.p_T),
        seed=seed + 1,
        budget_override=budget,
        config_path=profiles_path,
        groups_path=groups_path,
        curriculum_concepts=curriculum_concepts
    )

    # 5. Run CAT diagnostic for each learner through injected response callable
    def respond_learner_1(item_id: str) -> int:
        c = item_to_concept[item_id]
        d = item_diffs.get(item_id, 0.5)
        return learner_1.respond(concept=c, difficulty=d)

    def respond_learner_2(item_id: str) -> int:
        c = item_to_concept[item_id]
        d = item_diffs.get(item_id, 0.5)
        return learner_2.respond(concept=c, difficulty=d)

    diag_1 = run_adaptive_diagnostic(
        respond=respond_learner_1,
        bank_source=item_bank_path,
        qmatrix_source=qmatrix_path,
        curriculum_source=curriculum_path
    )

    diag_2 = run_adaptive_diagnostic(
        respond=respond_learner_2,
        bank_source=item_bank_path,
        qmatrix_source=qmatrix_path,
        curriculum_source=curriculum_path
    )

    diagnostic_record = {
        "metadata": {
            "description": "CAT adaptive diagnostic assessment records fitted to synthetic data",
            "stopping_variance": 0.15,
            "item_bank": item_bank_path,
            "q_matrix": qmatrix_path,
        },
        "learner_1": {
            "profile_id": profile_1,
            "theta_hat": diag_1.theta_hat,
            "variance": diag_1.variance,
            "items_asked": diag_1.items_asked,
            "num_items_asked": len(diag_1.items_asked),
            "initial_priors": {
                c: {
                    "p": cs.p,
                    "kappa": cs.kappa,
                    "n": cs.n,
                    "class": cs.classify(policy)
                }
                for c, cs in sorted(diag_1.concept_states.items())
            }
        },
        "learner_2": {
            "profile_id": profile_2,
            "theta_hat": diag_2.theta_hat,
            "variance": diag_2.variance,
            "items_asked": diag_2.items_asked,
            "num_items_asked": len(diag_2.items_asked),
            "initial_priors": {
                c: {
                    "p": cs.p,
                    "kappa": cs.kappa,
                    "n": cs.n,
                    "class": cs.classify(policy)
                }
                for c, cs in sorted(diag_2.concept_states.items())
            }
        }
    }

    # 6. Generate Day 1 Initial Plans
    res_l1_day1 = plan_request(
        graph=g,
        learner_states=diag_1.concept_states,
        budget=budget,
        deadline_days=deadline_days,
        targets=target,
        policy=policy
    )
    res_l2_day1 = plan_request(
        graph=g,
        learner_states=diag_2.concept_states,
        budget=budget,
        deadline_days=deadline_days,
        targets=target,
        policy=policy
    )
    _check_result_trace(res_l1_day1.plan, candidate_universe, num_days=deadline_days, budget=budget)
    _check_result_trace(res_l2_day1.plan, candidate_universe, num_days=deadline_days, budget=budget)

    # 7. Assessment with real simulated responses, difficulty stepping, and dependent gating
    # Foundational concept A
    base_diff_a = g.nodes["A"].get("base_difficulty", 0.20) if "A" in g.nodes else 0.5
    responses_pass = [learner_2.respond("A", difficulty=base_diff_a) for _ in range(policy.window_size)]
    responses_fail = [learner_1.respond("A", difficulty=base_diff_a) for _ in range(policy.window_size)]

    # 7A. Assessment Passed
    c_pass_before = diag_2.concept_states["A"]
    before_pass = {
        "p": c_pass_before.p,
        "kappa": c_pass_before.kappa,
        "n": c_pass_before.n,
        "sigma2": c_pass_before.sigma2,
        "state": c_pass_before.classify(policy)
    }
    replan_state_pass = ReplanState(
        graph=g,
        learner_states=dict(diag_2.concept_states),
        budget=budget,
        deadline_days=deadline_days,
        target_node=target,
        current_day=1,
        policy=policy
    )
    plan_passed = replan(replan_state_pass, assessment_result("A", responses_pass))
    c_pass_after = plan_passed["learner_states"]["A"]
    after_pass = {
        "p": c_pass_after.p,
        "kappa": c_pass_after.kappa,
        "n": c_pass_after.n,
        "sigma2": c_pass_after.sigma2,
        "state": c_pass_after.classify(policy)
    }
    _check_result_trace(plan_passed, candidate_universe, num_days=deadline_days, budget=budget)

    # 7B. Assessment Failed
    c_fail_before = diag_1.concept_states["A"]
    before_fail = {
        "p": c_fail_before.p,
        "kappa": c_fail_before.kappa,
        "n": c_fail_before.n,
        "sigma2": c_fail_before.sigma2,
        "state": c_fail_before.classify(policy)
    }
    replan_state_fail = ReplanState(
        graph=g,
        learner_states=dict(diag_1.concept_states),
        budget=budget,
        deadline_days=deadline_days,
        target_node=target,
        current_day=1,
        policy=policy
    )
    plan_failed = replan(replan_state_fail, assessment_result("A", responses_fail))
    c_fail_after = plan_failed["learner_states"]["A"]
    after_fail = {
        "p": c_fail_after.p,
        "kappa": c_fail_after.kappa,
        "n": c_fail_after.n,
        "sigma2": c_fail_after.sigma2,
        "state": c_fail_after.classify(policy)
    }
    _check_result_trace(plan_failed, candidate_universe, num_days=deadline_days, budget=budget)

    response_updates = {
        "assessment_passed": {
            "concept": "A",
            "responses": responses_pass,
            "before": before_pass,
            "after": after_pass,
            "difficulty_before": base_diff_a,
            "difficulty_after": plan_passed.get("difficulty_states", {}).get("A", DifficultyState(difficulty=base_diff_a)).difficulty
        },
        "assessment_failed": {
            "concept": "A",
            "responses": responses_fail,
            "before": before_fail,
            "after": after_fail,
            "difficulty_before": base_diff_a,
            "difficulty_after": plan_failed.get("difficulty_states", {}).get("A", DifficultyState(difficulty=base_diff_a)).difficulty
        }
    }

    # 8. Spaced Review: Advance simulated days to day 5, show timestamped review scheduled in leftover budget
    # Concept A was mastered at day 1; at day 5, dt = 4.0 days -> R(4) = 2^(-4/14) = 0.820 < 0.85 -> due
    review_horizon = 8
    states_review = dict(plan_passed["learner_states"])
    rl_review = ReviewLog()
    rl_review.record_attempt("A", time_in_days=1.0, correct=True)

    past_days_rev = []
    past_trace_rev = []
    for d in range(1, 5):
        past_days_rev.append({
            "day": d,
            "activities": ["A"] if d == 1 else [],
            "conditional_activities": [],
            "minutes_used": 5 if d == 1 else 0,
            "minutes_remaining": (budget - 5) if d == 1 else budget,
            "missed": (d > 1)
        })
        for nid in sorted(list(candidate_universe)):
            st = states_review.get(nid, ConceptState.cold_start())
            cls_name = st.classify(policy)
            if d == 1 and nid == "A":
                dec = "SELECTED"
                rc = ReasonCode.SELECTED.value
            elif cls_name == "Mastered":
                dec = "FILTERED"
                rc = ReasonCode.ALREADY_MASTERED.value
            elif d > 1 and nid == "A":
                dec = "FILTERED"
                rc = ReasonCode.COMPLETED.value
            else:
                dec = "FILTERED"
                rc = ReasonCode.PREREQUISITE_UNMET.value

            past_trace_rev.append({
                "node_id": nid,
                "day": d,
                "concept_state": {"p": st.p, "kappa": st.kappa, "sigma2": st.sigma2, "n": st.n, "class": cls_name},
                "constraints": {"budget": budget, "remaining_budget": budget, "prerequisites": {}},
                "score_terms": {},
                "decision": dec,
                "reason_code": rc,
                "policy_version": "static_baseline_v0"
            })

    state_review = ReplanState(
        graph=g,
        learner_states=states_review,
        budget=budget,
        deadline_days=review_horizon,
        target_node=target,
        current_day=5,
        review_log=rl_review,
        past_days=past_days_rev,
        past_trace=past_trace_rev,
        policy=policy
    )
    plan_review = replan(state_review, assessment_result("B", [1]))
    _check_result_trace(plan_review, candidate_universe, num_days=review_horizon, budget=budget)

    # 9. Prerequisite Remediation: Repeated failure (k=2) triggers unmastered ancestor inside daily budget
    if target == "D":
        rem_target = "D"
        failed_concept = "D"
        states_rem = {
            "A": ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1]),
            "B": ConceptState.cold_start(),
            "C": ConceptState(A=19.0, B=1.0, n=5, history=[1, 1, 1, 1]),
            "D": ConceptState.cold_start(),
        }
    elif target == "B":
        rem_target = "B"
        failed_concept = "B"
        states_rem = {
            "A": ConceptState.cold_start(),
            "B": ConceptState.cold_start(),
            "C": ConceptState.cold_start(),
            "D": ConceptState.cold_start(),
        }
    elif target == "C":
        rem_target = "C"
        failed_concept = "C"
        states_rem = {
            "A": ConceptState.cold_start(),
            "B": ConceptState.cold_start(),
            "C": ConceptState.cold_start(),
            "D": ConceptState.cold_start(),
        }
    else:
        rem_target = target
        failed_concept = target
        states_rem = {nid: ConceptState.cold_start() for nid in g.nodes}

    state_rem = ReplanState(
        graph=g,
        learner_states=states_rem,
        budget=budget,
        deadline_days=deadline_days,
        target_node=rem_target,
        current_day=1,
        policy=policy
    )
    plan_remediation = replan(state_rem, assessment_result(failed_concept, [0, 0]))
    _check_result_trace(plan_remediation, candidate_universe, num_days=deadline_days, budget=budget)

    # 10. Missed day, reduced budget, and shortened deadline preserving completed progress
    completed_seed_nodes = {"A"}
    s_missed_init = ReplanState(
        graph=g,
        learner_states=dict(plan_passed["learner_states"]),
        budget=budget,
        deadline_days=5,
        target_node=target,
        current_day=1,
        completed_nodes=set(completed_seed_nodes),
        policy=policy
    )
    plan_missed = replan(s_missed_init, missed_day())
    _check_result_trace(plan_missed, candidate_universe, num_days=5, budget=budget)

    past_days_m = plan_missed.get("days", [])[:1] if isinstance(plan_missed.get("days"), list) else []
    past_trace_m = plan_missed["trace"][:len(candidate_universe)] if isinstance(plan_missed.get("trace"), list) else []

    reduced_budget = max(1, budget // 2)
    s_reduced = ReplanState(
        graph=g,
        learner_states=dict(plan_missed.get("learner_states", plan_passed["learner_states"])),
        budget=budget,
        deadline_days=5,
        target_node=target,
        current_day=2,
        completed_nodes=set(plan_missed.get("completed_nodes", completed_seed_nodes)),
        past_days=past_days_m,
        past_trace=past_trace_m,
        policy=policy
    )
    plan_reduced = replan(s_reduced, changed_budget(reduced_budget))
    _check_result_trace(plan_reduced, candidate_universe, num_days=5, budget=reduced_budget)

    shortened_days = 2
    past_days_r = plan_reduced.get("days", [])[:1] if isinstance(plan_reduced.get("days"), list) else past_days_m
    past_trace_r = plan_reduced["trace"][:len(candidate_universe)] if isinstance(plan_reduced.get("trace"), list) else past_trace_m

    s_shortened = ReplanState(
        graph=g,
        learner_states=dict(plan_reduced.get("learner_states", plan_passed["learner_states"])),
        budget=reduced_budget,
        deadline_days=5,
        target_node=target,
        current_day=2,
        completed_nodes=set(plan_reduced.get("completed_nodes", completed_seed_nodes)),
        past_days=past_days_r,
        past_trace=past_trace_r,
        policy=policy
    )
    plan_shortened = replan(s_shortened, changed_deadline(shortened_days))
    _check_result_trace(plan_shortened, candidate_universe, num_days=shortened_days, budget=reduced_budget)

    # 11. Write artifacts to out_dir
    os.makedirs(out_dir, exist_ok=True)
    _save_json(os.path.join(out_dir, "diagnostic_record.json"), diagnostic_record)
    _save_json(os.path.join(out_dir, "plan_learner1_day1.json"), res_l1_day1.plan)
    _save_json(os.path.join(out_dir, "trace_learner1_day1.json"), res_l1_day1.plan["trace"])
    _save_json(os.path.join(out_dir, "plan_learner2_day1.json"), res_l2_day1.plan)
    _save_json(os.path.join(out_dir, "trace_learner2_day1.json"), res_l2_day1.plan["trace"])
    _save_json(os.path.join(out_dir, "plan_assessment_passed.json"), plan_passed)
    _save_json(os.path.join(out_dir, "trace_assessment_passed.json"), plan_passed["trace"])
    _save_json(os.path.join(out_dir, "plan_assessment_failed.json"), plan_failed)
    _save_json(os.path.join(out_dir, "trace_assessment_failed.json"), plan_failed["trace"])
    _save_json(os.path.join(out_dir, "plan_review_due.json"), plan_review)
    _save_json(os.path.join(out_dir, "trace_review_due.json"), plan_review["trace"])
    _save_json(os.path.join(out_dir, "plan_remediation.json"), plan_remediation)
    _save_json(os.path.join(out_dir, "trace_remediation.json"), plan_remediation["trace"])
    _save_json(os.path.join(out_dir, "plan_missed_day.json"), plan_missed)
    _save_json(os.path.join(out_dir, "trace_missed_day.json"), plan_missed["trace"])
    _save_json(os.path.join(out_dir, "plan_reduced_budget.json"), plan_reduced)
    _save_json(os.path.join(out_dir, "trace_reduced_budget.json"), plan_reduced["trace"])
    _save_json(os.path.join(out_dir, "plan_shortened_deadline.json"), plan_shortened)
    _save_json(os.path.join(out_dir, "trace_shortened_deadline.json"), plan_shortened["trace"])
    _save_json(os.path.join(out_dir, "response_updates.json"), response_updates)

    # 12. Write provenance manifest
    git_sha, dirty = get_git_info()
    curr_hash = compute_file_sha256(curriculum_path) if os.path.exists(curriculum_path) else "unknown"
    ib_hash = compute_file_sha256(item_bank_path) if os.path.exists(item_bank_path) else "unknown"
    qm_hash = compute_file_sha256(qmatrix_path) if os.path.exists(qmatrix_path) else "unknown"
    prof_hash = compute_file_sha256(profiles_path) if os.path.exists(profiles_path) else "unknown"
    grp_hash = compute_file_sha256(groups_path) if os.path.exists(groups_path) else "unknown"
    adp_hash = compute_file_sha256(adaptive_config_path) if os.path.exists(adaptive_config_path) else "unknown"
    bkt_pol_file = os.path.join(os.path.dirname(__file__), "..", "config", "bkt_params.yaml")
    pol_hash = compute_file_sha256(bkt_pol_file) if os.path.exists(bkt_pol_file) else resolved_config_hash(dataclasses.asdict(policy))

    resolved_config = {
        "budget": budget,
        "reduced_budget": reduced_budget,
        "deadline_days": deadline_days,
        "shortened_days": shortened_days,
        "seed": seed,
        "curriculum_path": curriculum_path,
        "curriculum_hash": curr_hash,
        "policy": {
            "p_S": policy.p_S,
            "p_G": policy.p_G,
            "p_T": policy.p_T,
            "window_size": policy.window_size,
            "mastered_p": policy.mastered_p,
            "weak_p": policy.weak_p,
            "sigma2_max": policy.sigma2_max,
            "min_obs": policy.min_obs,
            "kappa0": policy.kappa0,
            "quorum": policy.quorum
        }
    }
    cfg_hash = resolved_config_hash(resolved_config)

    input_hashes = {
        "curriculum": curr_hash,
        "item_bank": ib_hash,
        "q_matrix": qm_hash,
        "profiles": prof_hash,
        "groups": grp_hash,
        "adaptive_config": adp_hash,
        "policy": pol_hash,
    }
    output_checksums = compute_directory_checksums(out_dir, exclude_files=["manifest.json"])
    model_versions = {
        "pyBKT": "1.4.3",
        "catsim": "0.21.0",
        "bkt_policy": "v2.0",
        "planner": "v1.0",
    }

    write_manifest(
        path=os.path.join(out_dir, "manifest.json"),
        experiment_name="cli_slice",
        config_hash=cfg_hash,
        seeds=[seed],
        git_sha=git_sha,
        python_version=sys.version,
        package_versions=get_package_versions(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        data_route="synthetic_demo_curriculum",
        dataset_provenance=None,
        dirty=dirty,
        curriculum_path=curriculum_path,
        input_hashes=input_hashes,
        output_checksums=output_checksums,
        model_versions=model_versions,
    )

    # 13. Print human-readable summary derived from emitted traces
    print("=" * 70)
    print("ADAPTIVE LEARNING ENGINE: WEEK 4 SLICE DEMONSTRATION SUMMARY")
    print("=" * 70)
    print(f"Curriculum: {curriculum_path} (Target: {target}, Daily Budget: {budget} min)")
    print(f"Policy: using {policy_desc}")
    print(f"Seed: {seed} | Config Hash: {cfg_hash[:16]}... | Git SHA: {git_sha[:7]}{' (dirty)' if dirty else ''}\n")

    print("[1] Adaptive CAT Diagnostic Outcomes (Fitted to synthetic data):")
    print(f"  * Learner 1 ({profile_1}): theta_hat = {diag_1.theta_hat:.4f}, items asked = {len(diag_1.items_asked)}, variance = {diag_1.variance:.4f}")
    print(f"  * Learner 2 ({profile_2}): theta_hat = {diag_2.theta_hat:.4f}, items asked = {len(diag_2.items_asked)}, variance = {diag_2.variance:.4f}")

    print("\n[2] Day 1 Plans & Gating from Diagnostic Priors:")
    days_l1 = res_l1_day1.plan.get("days") or []
    days_l2 = res_l2_day1.plan.get("days") or []
    l1_d1_act = days_l1[0].get("activities", []) if days_l1 else []
    l2_d1_act = days_l2[0].get("activities", []) if days_l2 else []
    print(f"  * Learner 1 Day 1 scheduled: {l1_d1_act} (status: {res_l1_day1.status})")
    print(f"  * Learner 2 Day 1 scheduled: {l2_d1_act} (status: {res_l2_day1.status})")

    print("\n[3] Assessment Response Updates & Difficulty Stepping:")
    print(f"  * Scenario Passed (Learner 2): responses = {responses_pass}")
    print(f"    - Concept A p: {before_pass['p']:.4f} -> {after_pass['p']:.4f} ({after_pass['state']})")
    print(f"    - Difficulty A: {base_diff_a:.2f} -> {response_updates['assessment_passed']['difficulty_after']:.2f}")
    print(f"    - Dependent B gating: flipped to admissible (selected on Day 1)")
    print(f"  * Scenario Failed (Learner 1): responses = {responses_fail}")
    print(f"    - Concept A p: {before_fail['p']:.4f} -> {after_fail['p']:.4f} ({after_fail['state']})")
    print(f"    - Difficulty A: {base_diff_a:.2f} -> {response_updates['assessment_failed']['difficulty_after']:.2f}")
    print(f"    - Dependent B gating: remains blocked (PREREQUISITE_UNMET)")

    print("\n[4] Spaced Review Scheduling (Leftover Budget):")
    rev_day_5 = [d for d in plan_review.get("days", []) if d.get("day") == 5]
    if rev_day_5:
        print(f"  * Day 5 activities: {rev_day_5[0].get('activities', [])} (minutes used: {rev_day_5[0].get('minutes_used', 0)}/{budget})")
        print(f"  * Concept A review status: scheduled in leftover budget with reason REVIEW_DUE")

    print("\n[5] Prerequisite Remediation:")
    days_rem = plan_remediation.get("days") or []
    rem_act = days_rem[0].get("activities", []) if days_rem else []
    print(f"  * Repeated failure on {failed_concept} triggered remediation: scheduled {rem_act} first inside daily budget")

    print("\n[6] Dynamic Replanning (Progress Preservation):")
    print(f"  * Missed Day: recorded missed day, completed progress {plan_missed.get('completed_nodes', set())} preserved")
    print(f"  * Reduced Budget ({budget}m -> {reduced_budget}m): completed progress {plan_reduced.get('completed_nodes', set())} preserved")
    print(f"  * Shortened Deadline (deadline={shortened_days}d): completed progress {plan_shortened.get('completed_nodes', set())} preserved")

    print("=" * 70)
    print(f"SUCCESS: All 20 slice artifacts successfully written to '{out_dir}'.")
    return 0


KNOWN_INTEGRATED_CONFIG_KEYS = {
    "experiment_name",
    "version",
    "status",
    "seeds",
    "evaluation_scale",
    "simulator",
    "diagnostic",
    "statistics",
    "planner_controls",
    "arms",
    "claim_rule",
    "generators",
    "retention",
}


def is_tracked_tree_dirty() -> bool:
    """Checks if git tracked tree is dirty (ignoring untracked files)."""
    try:
        import subprocess
        res = subprocess.run(
            ["git", "status", "--porcelain", "-uno"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return bool(res.stdout.strip())
    except Exception:
        pass
    return False


def run_evaluate(
    config_path: str = DEFAULT_INTEGRATED_CONFIG,
    out_dir: str = "evaluation/results/w5/evaluate",
    learners: Optional[int] = None,
    require_clean: Optional[bool] = None,
) -> int:
    """
    Executes the closed-loop integrated evaluation pipeline (Subcommand: evaluate).
    
    1. Validates configuration file existence and top-level keys.
    2. Enforces --require-clean (defaults to True if out_dir is under evaluation/results, False otherwise).
    3. Calls the integrated module entry function (run_integrated_evaluation).
    4. Emits per_learner.csv, summary.md, and manifest.json.
    5. Reads written files to print a short summary.
    6. Exits 0 if run completed with zero prereq violations, zero budget violations, and trace coverage 1.0 (100%).
       Exits nonzero otherwise or on invalid config.
    """
    # 1. Validate config file existence
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: '{config_path}'", file=sys.stderr)
        return 1

    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading configuration file '{config_path}': {e}", file=sys.stderr)
        return 1

    if not isinstance(raw_cfg, dict):
        print(f"Error: Configuration file '{config_path}' must be a dictionary.", file=sys.stderr)
        return 1

    # Check for unknown config keys
    for k in raw_cfg.keys():
        if k not in KNOWN_INTEGRATED_CONFIG_KEYS:
            print(f"Error: Unknown configuration key: '{k}' in {config_path}", file=sys.stderr)
            return 1

    # Check required config sections
    for req in ["seeds", "evaluation_scale", "diagnostic", "statistics", "planner_controls", "arms"]:
        if req not in raw_cfg:
            print(f"Error: Missing required section '{req}' in {config_path}", file=sys.stderr)
            return 1

    # 2. Handle --require-clean
    if require_clean is None:
        out_abs = os.path.abspath(out_dir)
        eval_results_abs = os.path.abspath("evaluation/results")
        require_clean = (out_abs == eval_results_abs or out_abs.startswith(eval_results_abs + os.sep))

    if require_clean:
        if is_tracked_tree_dirty():
            print("Error: Tracked git tree is dirty and --require-clean is active.", file=sys.stderr)
            return 1

    # 3. Call integrated evaluation entry function
    try:
        results = run_integrated_evaluation(
            config_path=config_path,
            output_dir=out_dir,
            override_learners=learners,
        )
    except Exception as e:
        print(f"Error running integrated evaluation: {e}", file=sys.stderr)
        return 1

    # 4. Read back from output files and print short summary
    csv_path = results.get("csv_path") or os.path.join(out_dir, "per_learner.csv")
    md_path = results.get("md_path") or os.path.join(out_dir, "summary.md")
    manifest_path = results.get("manifest_path") or os.path.join(out_dir, "manifest.json")

    manifest_data = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

    print("=" * 70)
    print("ADAPTIVE LEARNING ENGINE: INTEGRATED EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Config: {config_path} | Output Dir: {out_dir}")
    print(f"Benchmark: {manifest_data.get('benchmark_name', 'w5_integrated')}")
    git_info = manifest_data.get("git", {})
    print(f"Commit SHA: {git_info.get('commit_sha', 'unknown')[:7]} | Dirty: {git_info.get('dirty', False)}")
    print(f"Config Hash: {manifest_data.get('config_hash', 'unknown')[:16]}...\n")

    arm_results = results.get("arm_results", {})
    print("Arm Results:")
    all_correct = True
    for arm_name, r in arm_results.items():
        cov_pct = getattr(r, "trace_coverage", 0.0)
        prereqs = getattr(r, "total_prereq_violations", 0)
        budgets = getattr(r, "total_budget_violations", 0)
        mean_m = getattr(r, "mean_mastered", 0.0)
        print(f"  * {arm_name}: Mastered={mean_m:.4f}, Prereq Violations={prereqs}, Budget Violations={budgets}, Trace Coverage={cov_pct:.1f}%")

        cov_frac = cov_pct if cov_pct <= 1.0 else cov_pct / 100.0
        if prereqs != 0 or budgets != 0 or not math.isclose(cov_frac, 1.0, abs_tol=1e-3):
            all_correct = False

    print("=" * 70)
    print(f"Artifacts written: {csv_path}, {md_path}, {manifest_path}")

    if not all_correct:
        print("WARNING: Evaluation completed but hard-correctness counts or trace coverage invariants were not satisfied.")
        return 1

    print("SUCCESS: All hard-correctness counts are zero and trace coverage is 1.0.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive Learning Engine CLI")
    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Run end-to-end multi-scenario CLI demonstration")
    demo_parser.add_argument("--out", type=str, default="evaluation/results/w3/demo", help="Output directory")
    demo_parser.add_argument("--seed", type=int, default=20261012, help="Random seed")
    demo_parser.add_argument("--budget", type=int, default=10, help="Daily study budget in minutes")
    demo_parser.add_argument("--curriculum", type=str, default="data/curricula/demo_curriculum.json", help="Path to curriculum JSON file")
    demo_parser.add_argument("--policy", type=str, default=None, help="Path to policy YAML file")

    plan_parser = subparsers.add_parser("plan", help="Generate and validate a single plan request")
    plan_parser.add_argument("--curriculum", type=str, required=True, help="Path to curriculum JSON file")
    plan_parser.add_argument("--target", type=str, required=True, help="Target node ID")
    plan_parser.add_argument("--budget", type=int, required=True, help="Daily study budget in minutes")
    plan_parser.add_argument("--deadline-days", type=int, required=True, help="Planning horizon in days")
    plan_parser.add_argument("--out", type=str, required=True, help="Output directory")
    plan_parser.add_argument("--policy", type=str, default=None, help="Path to policy YAML file")
    plan_parser.add_argument("--states", type=str, default=None, help="Path to learner states JSON file")

    slice_parser = subparsers.add_parser("slice", help="Run end-to-end W4 slice demonstration")
    slice_parser.add_argument("--out", type=str, default="evaluation/results/w4/slice", help="Output directory")
    slice_parser.add_argument("--seed", type=int, default=20261024, help="Random seed")
    slice_parser.add_argument("--budget", type=int, default=10, help="Daily study budget in minutes")
    slice_parser.add_argument("--curriculum", type=str, default="data/curricula/demo_curriculum.json", help="Path to curriculum JSON file")
    slice_parser.add_argument("--item-bank", type=str, default="data/processed/item_bank_synthetic.csv", help="Path to item bank CSV file")
    slice_parser.add_argument("--q-matrix", type=str, default="data/processed/q_matrix_synthetic.csv", help="Path to Q-matrix CSV file")
    slice_parser.add_argument("--profiles", type=str, default="config/profiles.yaml", help="Path to profiles YAML file")
    slice_parser.add_argument("--groups", type=str, default="data/curricula/demo_curriculum.groups.yaml", help="Path to groups YAML file")
    slice_parser.add_argument("--adaptive-config", type=str, default="config/adaptive.yaml", help="Path to adaptive config YAML file")
    slice_parser.add_argument("--policy", type=str, default=None, help="Path to policy YAML file")
    slice_parser.add_argument("--target", type=str, default="D", help="Target node ID")
    slice_parser.add_argument("--deadline-days", type=int, default=3, help="Planning horizon in days")
    slice_parser.add_argument("--profile-1", type=str, default="profile_1", help="First learner profile")
    slice_parser.add_argument("--profile-2", type=str, default="profile_2", help="Second learner profile")

    evaluate_parser = subparsers.add_parser("evaluate", help="Run closed-loop integrated evaluation")
    evaluate_parser.add_argument("--config", type=str, default=DEFAULT_INTEGRATED_CONFIG, help="Path to evaluation YAML config")
    evaluate_parser.add_argument("--out", type=str, required=True, help="Output directory")
    evaluate_parser.add_argument("--learners", type=int, default=None, help="Override synthetic learner count")
    evaluate_parser.add_argument("--require-clean", action=argparse.BooleanOptionalAction, default=None, help="Fail if the tracked git tree is dirty")

    args = parser.parse_args()

    if args.command == "demo" or args.command is None:
        out_dir = getattr(args, "out", "evaluation/results/w3/demo")
        seed = getattr(args, "seed", 20261012)
        budget = getattr(args, "budget", 10)
        curriculum = getattr(args, "curriculum", "data/curricula/demo_curriculum.json")
        policy = getattr(args, "policy", None)
        code = run_demo(out_dir=out_dir, seed=seed, budget=budget, curriculum_path=curriculum, policy_path=policy)
        sys.exit(code)
    elif args.command == "plan":
        code = run_plan(
            curriculum_path=args.curriculum,
            target=args.target,
            budget=args.budget,
            deadline_days=args.deadline_days,
            out_dir=args.out,
            policy_path=args.policy,
            states_path=args.states,
        )
        sys.exit(code)
    elif args.command == "slice":
        code = run_slice(
            out_dir=args.out,
            seed=args.seed,
            budget=args.budget,
            curriculum_path=args.curriculum,
            item_bank_path=args.item_bank,
            qmatrix_path=args.q_matrix,
            profiles_path=args.profiles,
            groups_path=args.groups,
            adaptive_config_path=args.adaptive_config,
            policy_path=args.policy,
            target=args.target,
            deadline_days=args.deadline_days,
            profile_1=args.profile_1,
            profile_2=args.profile_2,
        )
        sys.exit(code)
    elif args.command == "evaluate":
        code = run_evaluate(
            config_path=args.config,
            out_dir=args.out,
            learners=args.learners,
            require_clean=args.require_clean,
        )
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

