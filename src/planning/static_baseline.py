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

    completed_set = set(mastered_nodes)
    remaining_nodes = list(topo_order)
    days_plan = []

    for day_num in range(1, deadline_days + 1):
        rem_budget = budget
        day_activities = []
        scheduled_today = set()

        # Record entries for nodes already mastered prior to this day
        for node_id in sorted(list(candidate_universe)):
            if node_id in completed_set:
                state = learner_states.get(node_id)
                if state is None or state.classify() != "Mastered":
                    state = ConceptState(A=8.5, B=1.5, n=4, history=[1, 1, 1, 1])
                    learner_states[node_id] = state

                prereqs = set(g.predecessors(node_id)).intersection(candidate_universe)
                prereq_status = {p: True for p in prereqs}
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

        # Evaluate remaining nodes in topological order and record trace entries at moment of decision
        for node_id in list(remaining_nodes):
            state = learner_states.get(node_id, ConceptState.cold_start())
            dur = g.nodes[node_id].get("baseline_duration", 0)
            prereqs = set(g.predecessors(node_id)).intersection(candidate_universe)
            prereq_status = {p: (p in completed_set or p in scheduled_today) for p in prereqs}
            prereqs_met = all(prereq_status.values())

            cur_rem_budget = rem_budget

            if not prereqs_met:
                decision = "FILTERED"
                reason = ReasonCode.PREREQUISITE_UNMET
            elif dur > rem_budget:
                decision = "FILTERED"
                reason = ReasonCode.BUDGET_EXCEEDED
            else:
                decision = "SELECTED"
                reason = ReasonCode.SELECTED
                day_activities.append(node_id)
                scheduled_today.add(node_id)
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
                    "prerequisites": prereq_status
                },
                score_terms={},
                decision=decision,
                reason_code=reason,
                policy_version=policy_version
            )
            trace.append(entry.to_dict())

        for node_id in scheduled_today:
            learner_states[node_id] = ConceptState(A=8.5, B=1.5, n=4, history=[1, 1, 1, 1])
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
