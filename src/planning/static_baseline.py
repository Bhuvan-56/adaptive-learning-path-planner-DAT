from typing import Dict, List, Any, Set, Optional
import networkx as nx

from src.state.learner_state import ConceptState
from src.planning.feasibility import check_feasibility, FeasibilityStatus, InfeasibilityReason
from src.trace.schema import TraceEntry, ReasonCode
from src.trace.universe import get_candidate_universe


def generate_static_plan(
    g: nx.DiGraph,
    learner_states: Dict[str, ConceptState],
    budget: int,
    deadline_days: int,
    target_node: str,
    policy_version: str = "static_baseline_v0",
    completed_nodes: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Generates a daily study schedule using a deterministic static baseline topological sort planner.
    Performs block indivisibility feasibility checking and emits a candidate decision trace.

    Maintains three separate planner states:
    - planned: placed on a future day
    - completed: the learner actually did it; supplied as input
    - evidence_mastered: learner-state classifier returns Mastered
    """
    candidate_universe = get_candidate_universe(g, target_node)

    completed_set = set(completed_nodes or set())
    evidence_mastered = set()
    required_nodes = set()

    for node_id in candidate_universe:
        state = learner_states.get(node_id, ConceptState.cold_start())
        if state.classify() == "Mastered":
            evidence_mastered.add(node_id)
        elif node_id not in completed_set:
            required_nodes.add(node_id)

    status, feasibility_info = check_feasibility(g, required_nodes, budget, deadline_days)

    if status == FeasibilityStatus.INFEASIBLE_PROVED:
        reason_val = feasibility_info.get("reason_code")
        if hasattr(reason_val, "value"):
            reason_str = reason_val.value
        else:
            reason_str = str(reason_val) if reason_val else "BLOCK_EXCEEDS_DAILY_BUDGET"

        status_str = status.value if hasattr(status, "value") else str(status)

        no_plan_trace = {
            "status": status_str,
            "reason_code": reason_str,
            "constraints": {
                "budget": budget,
                "deadline_days": deadline_days
            }
        }
        return {
            "status": FeasibilityStatus.INFEASIBLE_PROVED,
            "feasibility_explanation": feasibility_info,
            "days": [],
            "trace": no_plan_trace
        }

    # Deterministic topological ordering of required nodes
    subgraph = g.subgraph(required_nodes)
    try:
        topo_order = list(nx.lexicographical_topological_sort(subgraph))
    except nx.NetworkXUnfeasible as e:
        raise ValueError("Cyclic graph detected; cannot produce fallback plan.") from e

    planned: Dict[str, int] = {}
    remaining_nodes = list(topo_order)
    days_plan = []
    trace: List[Dict[str, Any]] = []
    assessment_candidates: Set[str] = set()

    for day_num in range(1, deadline_days + 1):
        rem_budget = budget
        day_activities = []
        conditional_activities = []
        scheduled_today = set()

        # Record entries for nodes already mastered, completed, or scheduled on prior days
        for node_id in sorted(list(candidate_universe)):
            state = learner_states.get(node_id, ConceptState.cold_start())
            prereqs = set(g.predecessors(node_id)).intersection(candidate_universe)
            prereq_status = {p: True for p in prereqs}

            if node_id in evidence_mastered:
                entry = TraceEntry(
                    node_id=node_id,
                    day=day_num,
                    concept_state={
                        "p": state.p,
                        "kappa": state.kappa,
                        "sigma2": state.sigma2,
                        "n": state.n,
                        "class": state.classify()
                    },
                    constraints={
                        "budget": budget,
                        "remaining_budget": rem_budget,
                        "prerequisites": prereq_status
                    },
                    score_terms={},
                    decision="FILTERED",
                    reason_code=ReasonCode.ALREADY_MASTERED,
                    policy_version=policy_version
                )
                trace.append(entry.to_dict())
            elif node_id in completed_set:
                entry = TraceEntry(
                    node_id=node_id,
                    day=day_num,
                    concept_state={
                        "p": state.p,
                        "kappa": state.kappa,
                        "sigma2": state.sigma2,
                        "n": state.n,
                        "class": state.classify()
                    },
                    constraints={
                        "budget": budget,
                        "remaining_budget": rem_budget,
                        "prerequisites": prereq_status
                    },
                    score_terms={},
                    decision="FILTERED",
                    reason_code=ReasonCode.COMPLETED,
                    policy_version=policy_version
                )
                trace.append(entry.to_dict())
            elif node_id in planned and planned[node_id] < day_num:
                entry = TraceEntry(
                    node_id=node_id,
                    day=day_num,
                    concept_state={
                        "p": state.p,
                        "kappa": state.kappa,
                        "sigma2": state.sigma2,
                        "n": state.n,
                        "class": state.classify()
                    },
                    constraints={
                        "budget": budget,
                        "remaining_budget": rem_budget,
                        "prerequisites": prereq_status
                    },
                    score_terms={},
                    decision="FILTERED",
                    reason_code=ReasonCode.ALREADY_SCHEDULED,
                    policy_version=policy_version
                )
                trace.append(entry.to_dict())

        # Evaluate remaining nodes in topological order and record trace entries at moment of decision
        for node_id in list(remaining_nodes):
            state = learner_states.get(node_id, ConceptState.cold_start())
            dur = g.nodes[node_id].get("baseline_duration", 0)
            prereqs = set(g.predecessors(node_id)).intersection(candidate_universe)

            prereq_status = {}
            prereqs_met = True
            has_conditional_prereq = False
            uncertain_prereqs = []
            failed_prereqs = []

            for p in prereqs:
                p_state = learner_states.get(p, ConceptState.cold_start())
                p_class = p_state.classify()

                if p in evidence_mastered:
                    prereq_status[p] = True
                elif p in planned and planned[p] < day_num:
                    prereq_status[p] = True
                    has_conditional_prereq = True
                elif p in scheduled_today:
                    prereq_status[p] = True
                    has_conditional_prereq = True
                else:
                    prereq_status[p] = False
                    prereqs_met = False
                    if p_class == "Uncertain":
                        uncertain_prereqs.append(p)
                        assessment_candidates.add(p)
                    elif p_class == "Weak":
                        failed_prereqs.append(p)

            is_conditional = has_conditional_prereq
            cur_rem_budget = rem_budget

            if not prereqs_met:
                decision = "FILTERED"
                if uncertain_prereqs:
                    reason = ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT
                else:
                    reason = ReasonCode.PREREQUISITE_UNMET
                is_conditional = False
            elif dur > rem_budget:
                decision = "FILTERED"
                if dur > budget:
                    reason = ReasonCode.BLOCK_EXCEEDS_DAILY_BUDGET
                else:
                    reason = ReasonCode.BUDGET_EXCEEDED
                is_conditional = False
            else:
                decision = "SELECTED"
                reason = ReasonCode.SELECTED
                day_activities.append(node_id)
                if is_conditional:
                    conditional_activities.append(node_id)
                scheduled_today.add(node_id)
                planned[node_id] = day_num
                rem_budget -= dur
                remaining_nodes.remove(node_id)

            entry = TraceEntry(
                node_id=node_id,
                day=day_num,
                concept_state={
                    "p": state.p,
                    "kappa": state.kappa,
                    "sigma2": state.sigma2,
                    "n": state.n,
                    "class": state.classify()
                },
                constraints={
                    "budget": budget,
                    "remaining_budget": cur_rem_budget,
                    "prerequisites": prereq_status,
                    "conditional": is_conditional,
                    "revalidate_before_execution": is_conditional
                },
                score_terms={},
                decision=decision,
                reason_code=reason,
                policy_version=policy_version
            )
            trace.append(entry.to_dict())

        days_plan.append({
            "day": day_num,
            "activities": day_activities,
            "conditional_activities": conditional_activities,
            "minutes_used": budget - rem_budget,
            "minutes_remaining": rem_budget
        })

    if remaining_nodes:
        final_status = FeasibilityStatus.HEURISTIC_NO_PLAN
        feasibility_info["status"] = FeasibilityStatus.HEURISTIC_NO_PLAN
        feasibility_info["reason_code"] = InfeasibilityReason.SCHEDULING_CONSTRAINTS_UNMET
    else:
        final_status = FeasibilityStatus.FEASIBLE
        feasibility_info["status"] = FeasibilityStatus.FEASIBLE

    return {
        "status": final_status,
        "feasibility_explanation": feasibility_info,
        "days": days_plan,
        "trace": trace,
        "assessment_candidates": sorted(list(assessment_candidates))
    }


generate_static_baseline = generate_static_plan

