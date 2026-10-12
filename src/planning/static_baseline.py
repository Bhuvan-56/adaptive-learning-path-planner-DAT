from typing import Dict, List, Any, Set
import networkx as nx

from src.state.learner_state import ConceptState
from src.planning.feasibility import check_feasibility, FeasibilityStatus
from src.trace.schema import TraceEntry, ReasonCode
from src.trace.universe import get_candidate_universe


def generate_static_plan(
    g: nx.DiGraph,
    learner_states: Dict[str, ConceptState],
    budget: int,
    deadline_days: int,
    target_node: str,
    policy_version: str = "static_baseline_v0"
) -> Dict[str, Any]:
    """
    Generates a daily study schedule using a deterministic static baseline topological sort planner.
    Performs block indivisibility feasibility checking and emits a candidate decision trace.
    """
    candidate_universe = get_candidate_universe(g, target_node)

    # Required nodes: candidates not currently Mastered
    required_nodes = set()
    mastered_nodes = set()

    for node_id in candidate_universe:
        state = learner_states.get(node_id, ConceptState.cold_start())
        if state.classify() == "Mastered":
            mastered_nodes.add(node_id)
        else:
            required_nodes.add(node_id)

    status, feasibility_info = check_feasibility(g, required_nodes, budget, deadline_days)

    trace: List[Dict[str, Any]] = []

    if status == FeasibilityStatus.INFEASIBLE_PROVED:
        # Build trace entries for infeasibility failure
        for node_id in candidate_universe:
            state = learner_states.get(node_id, ConceptState.cold_start())
            dur = g.nodes[node_id].get("baseline_duration", 0)
            if node_id in mastered_nodes:
                reason = ReasonCode.ALREADY_MASTERED
            elif dur > budget:
                reason = ReasonCode.BLOCK_EXCEEDS_DAILY_BUDGET
            else:
                reason = ReasonCode.BUDGET_EXCEEDED

            entry = TraceEntry(
                node_id=node_id,
                day=1,
                concept_state={
                    "p": state.p,
                    "kappa": state.kappa,
                    "sigma2": state.sigma2,
                    "n": state.n,
                    "class": state.classify()
                },
                constraints={
                    "budget": budget,
                    "remaining_budget": budget,
                    "prerequisites": {}
                },
                score_terms={},
                decision="FILTERED",
                reason_code=reason,
                policy_version=policy_version
            )
            trace.append(entry.to_dict())

        return {
            "status": FeasibilityStatus.INFEASIBLE_PROVED,
            "feasibility_explanation": feasibility_info,
            "days": [],
            "trace": trace
        }

    # Deterministic topological ordering of required nodes
    subgraph = g.subgraph(required_nodes)
    try:
        topo_order = list(nx.lexicographical_topological_sort(subgraph))
    except nx.NetworkXUnfeasible as e:
        raise ValueError("Cyclic graph detected; cannot produce fallback plan.") from e

    completed_set = set(mastered_nodes)
    remaining_nodes = list(topo_order)
    days_plan = []

    for day_num in range(1, deadline_days + 1):
        rem_budget = budget
        day_activities = []
        scheduled_today = set()
        day_decisions = {}

        for node_id in list(remaining_nodes):
            dur = g.nodes[node_id].get("baseline_duration", 0)
            prereqs = set(g.predecessors(node_id))
            prereqs_in_universe = prereqs.intersection(candidate_universe)
            prereqs_met = prereqs_in_universe.issubset(completed_set.union(scheduled_today))

            if not prereqs_met:
                day_decisions[node_id] = ("FILTERED", ReasonCode.PREREQUISITE_UNMET, dur)
            elif dur > rem_budget:
                day_decisions[node_id] = ("FILTERED", ReasonCode.BUDGET_EXCEEDED, dur)
            else:
                day_decisions[node_id] = ("SELECTED", ReasonCode.SELECTED, dur)
                day_activities.append(node_id)
                scheduled_today.add(node_id)
                rem_budget -= dur
                remaining_nodes.remove(node_id)

        # Record trace entries for ALL nodes in candidate_universe for this day
        for node_id in sorted(list(candidate_universe)):
            state = learner_states.get(node_id, ConceptState.cold_start())
            prereqs = set(g.predecessors(node_id)).intersection(candidate_universe)
            prereq_status = {p: (p in completed_set or p in scheduled_today) for p in prereqs}

            if node_id in completed_set:
                decision = "FILTERED"
                reason = ReasonCode.ALREADY_MASTERED
                dur = g.nodes[node_id].get("baseline_duration", 0)
            elif node_id in day_decisions:
                decision, reason, dur = day_decisions[node_id]
            else:
                decision = "FILTERED"
                reason = ReasonCode.BUDGET_EXCEEDED
                dur = g.nodes[node_id].get("baseline_duration", 0)

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
                    "remaining_budget": rem_budget + (dur if decision == "SELECTED" else 0),
                    "prerequisites": prereq_status
                },
                score_terms={},
                decision=decision,
                reason_code=reason,
                policy_version=policy_version
            )
            trace.append(entry.to_dict())

        completed_set.update(scheduled_today)

        days_plan.append({
            "day": day_num,
            "activities": day_activities,
            "minutes_used": budget - rem_budget,
            "minutes_remaining": rem_budget
        })


    final_status = FeasibilityStatus.FEASIBLE
    if remaining_nodes:
        final_status = FeasibilityStatus.HEURISTIC_NO_PLAN

    return {
        "status": final_status,
        "feasibility_explanation": feasibility_info,
        "days": days_plan,
        "trace": trace
    }
