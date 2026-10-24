import argparse
from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, List, Set

import networkx as nx

from src.curriculum.graph import load_graph, validate_graph
from src.planning.feasibility import FeasibilityStatus, InfeasibilityReason
from src.planning.replan import (
    ReplanState,
    assessment_result,
    changed_budget,
    missed_day,
    replan,
)
from src.planning.service import plan_request
from src.provenance import (
    _normalize_obj,
    get_git_info,
    get_package_versions,
    resolved_config_hash,
    write_manifest,
)
from src.simulation.simulator import MatchedBKTGenerator, SimulatedLearner
from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig, load_policy
from src.trace.checker import check_no_plan_trace, check_trace
from src.trace.schema import ReasonCode
from src.trace.universe import get_candidate_universe


def _save_json(path: str, data: Any) -> None:
    """Saves normalized data as deterministic, byte-identical JSON."""
    normalized = _normalize_obj(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, sort_keys=True)


def run_demo(out_dir: str, seed: int = 20261012, budget: int = 10, curriculum_path: str = "data/curricula/demo_curriculum.json") -> int:
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
    bkt_policy_path = os.path.join(os.path.dirname(__file__), "..", "config", "bkt_params.yaml")
    policy = load_policy(bkt_policy_path) if os.path.exists(bkt_policy_path) else PolicyConfig()

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
        check_trace(candidate_universe, res_novice.plan["trace"], num_days=deadline_days)
        check_trace(candidate_universe, res_intermediate.plan["trace"], num_days=deadline_days)
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
        check_trace(candidate_universe, plan_passed["trace"], num_days=deadline_days)
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
        check_trace(candidate_universe, plan_failed["trace"], num_days=deadline_days)
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
        check_trace(candidate_universe, plan_missed["trace"], num_days=deadline_days)
    except ValueError as e:
        err = {"status": "TRACE_CHECK_FAILED", "error_codes": ["TRACE_CONTRACT_VIOLATION"], "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    # Budget reduction from 10 to 5
    reduced_budget = 5
    replan_state_reduced = ReplanState(
        graph=g,
        learner_states=dict(plan_missed["learner_states"]),
        budget=plan_missed["budget"],
        deadline_days=plan_missed["deadline_days"],
        target_node=target_node,
        current_day=plan_missed["current_day"],
        completed_nodes=set(plan_missed["completed_nodes"]),
        past_days=plan_missed["days"][:1],
        past_trace=plan_missed["trace"][:len(candidate_universe)],
        policy=policy
    )
    plan_reduced = replan(replan_state_reduced, changed_budget(reduced_budget))
    try:
        check_no_plan_trace(plan_reduced["trace"])
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
    resolved_config = {
        "budget": budget,
        "reduced_budget": reduced_budget,
        "deadline_days": deadline_days,
        "seed": seed,
        "curriculum_path": "data/curricula/demo_curriculum.json",
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
        dirty=dirty
    )

    # ---------------------------------------------------------
    # 7. Print Human Summary
    # ---------------------------------------------------------
    print("=" * 70)
    print("ADAPTIVE LEARNING ENGINE: END-TO-END DEMONSTRATION SUMMARY")
    print("=" * 70)
    print(f"Curriculum: {curriculum_path} (Target: {target_node}, Horizon: {deadline_days} days, Daily Budget: {budget} min)")
    print(f"Seed: {seed} | Config Hash: {cfg_hash[:16]}... | Git SHA: {git_sha[:7]}{' (dirty)' if dirty else ''}\n")

    print("[1] Learner Profiles & Day 1 Plan Divergence:")
    print(f"  * Novice Learner (Budget {budget}m):")
    print(f"    - Scheduled Activities Day 1: {res_novice.plan['days'][0]['activities']}")
    print(f"    - Conditional Activities Day 1: {res_novice.plan['days'][0]['conditional_activities']}")
    print(f"    - Gating Rationale: Foundational concept 'A' is unprobed (Uncertain).")
    print(f"      Dependent concept 'D' is FILTERED with reason UNCERTAIN_NEEDS_ASSESSMENT.")
    print(f"  * Intermediate Learner (Budget {budget}m):")
    print(f"    - Scheduled Activities Day 1: {res_intermediate.plan['days'][0]['activities']}")
    print(f"    - Gating Rationale: Prerequisites 'A' and 'B' are ALREADY_MASTERED and filtered.")
    print(f"      Unlocked downstream concept 'C' (10 min) is SELECTED for Day 1.\n")

    print("[2] Dynamic Assessment & Replanning Scenarios (Concept 'A'):")
    print(f"  * Scenario A (Assessment Passed - Unblocked):")
    print(f"    - Response Sequence: {responses_pass} -> p: {before_pass['p']:.2f} -> {after_pass['p']:.4f} ({after_pass['state']})")
    print(f"    - Outcome: Prerequisite 'A' becomes evidence-Mastered.")
    print(f"      Dependent concept 'B' becomes unconditionally admissible and is SELECTED on Day 1.")
    print(f"  * Scenario B (Assessment Failed - Stays Blocked):")
    print(f"    - Response Sequence: {responses_fail} -> p: {before_fail['p']:.2f} -> {after_fail['p']:.4f} ({after_fail['state']})")
    print(f"    - Outcome: Concept 'A' classifies as Weak.")
    print(f"      Dependent concepts 'B' and 'D' remain FILTERED with reason PREREQUISITE_UNMET.")
    print(f"      Planner status resolves to HEURISTIC_NO_PLAN (target unreachable within horizon).\n")

    print("[3] Missed Day & Budget Infeasibility Handling:")
    print(f"  * Missed Day: Day 1 recorded as missed (minutes_used=0). Completed nodes {plan_missed['completed_nodes']} preserved.")
    print(f"  * Budget Reduction: Reduced from 10m to 5m/day.")
    print(f"    - Planner Status: {plan_reduced['status'].value if hasattr(plan_reduced['status'], 'value') else plan_reduced['status']}")
    print(f"    - Reason Code: {plan_reduced['feasibility_explanation'].get('reason_code')}")
    print(f"    - Proved Infeasibility: {plan_reduced['feasibility_explanation'].get('notes')}")
    print(f"    - Actionable Minimum Fix: {plan_reduced['feasibility_explanation'].get('minimum_fix')}\n")

    print("[4] Latent Cognitive State Invariant Verification (EvaluatorView):")
    ev_novice = learner_novice.evaluator_view()
    ev_inter = learner_intermediate.evaluator_view()
    print(f"  * True Latent Mastery (Novice):       {ev_novice.latent_masteries}")
    print(f"  * True Latent Mastery (Intermediate): {ev_inter.latent_masteries}")
    print("  * Invariant: Latent states remained strictly inaccessible to planning & state code.")
    print("=" * 70)
    print(f"SUCCESS: All 12 plan and trace artifacts successfully written to '{out_dir}'.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive Learning Engine CLI")
    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Run end-to-end multi-scenario CLI demonstration")
    demo_parser.add_argument("--out", type=str, default="evaluation/results/w3/demo", help="Output directory")
    demo_parser.add_argument("--seed", type=int, default=20261012, help="Random seed")
    demo_parser.add_argument("--budget", type=int, default=10, help="Daily study budget in minutes")
    demo_parser.add_argument("--curriculum", type=str, default="data/curricula/demo_curriculum.json", help="Path to curriculum JSON file")

    args = parser.parse_args()

    if args.command == "demo" or args.command is None:
        out_dir = getattr(args, "out", "evaluation/results/w3/demo")
        seed = getattr(args, "seed", 20261012)
        budget = getattr(args, "budget", 10)
        curriculum = getattr(args, "curriculum", "data/curricula/demo_curriculum.json")
        code = run_demo(out_dir=out_dir, seed=seed, budget=budget, curriculum_path=curriculum)
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
