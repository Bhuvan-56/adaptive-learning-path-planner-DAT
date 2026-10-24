from dataclasses import dataclass, field
from typing import Dict, List, Any, Set, Optional, Union
import networkx as nx

from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig, default_policy
from src.planning.feasibility import check_feasibility, FeasibilityStatus, InfeasibilityReason
from src.trace.schema import TraceEntry, ReasonCode
from src.trace.universe import get_candidate_universe
from src.planning.difficulty import DifficultyState, step_difficulty


@dataclass
class AssessmentResultEvent:
    node: str
    correct_flags: List[Union[bool, int]]
    type: str = "assessment_result"


@dataclass
class MissedDayEvent:
    type: str = "missed_day"


@dataclass
class ChangedBudgetEvent:
    new_budget: int
    type: str = "changed_budget"


@dataclass
class ChangedDeadlineEvent:
    new_days: int
    type: str = "changed_deadline"


def assessment_result(node: str, correct_flags: List[Union[bool, int]]) -> AssessmentResultEvent:
    """Factory creating an assessment result event."""
    return AssessmentResultEvent(node=node, correct_flags=correct_flags)


def missed_day() -> MissedDayEvent:
    """Factory creating a missed day event."""
    return MissedDayEvent()


def changed_budget(new_budget: int) -> ChangedBudgetEvent:
    """Factory creating a changed daily budget event."""
    return ChangedBudgetEvent(new_budget=new_budget)


def changed_deadline(new_days: int) -> ChangedDeadlineEvent:
    """Factory creating a changed deadline event."""
    return ChangedDeadlineEvent(new_days=new_days)


@dataclass
class ReplanState:
    graph: nx.DiGraph
    learner_states: Dict[str, ConceptState]
    budget: int
    deadline_days: int
    target_node: str
    current_day: int = 1
    completed_nodes: Set[str] = field(default_factory=set)
    past_days: List[Dict[str, Any]] = field(default_factory=list)
    past_trace: List[Dict[str, Any]] = field(default_factory=list)
    policy_version: str = "static_baseline_v0"
    policy: Optional[PolicyConfig] = None
    difficulty_states: Dict[str, DifficultyState] = field(default_factory=dict)


def _extract_state(state: Any) -> Dict[str, Any]:
    if isinstance(state, dict):
        g = state.get("graph") or state.get("g")
        l_states = dict(state.get("learner_states") or state.get("states", {}))
        return {
            "graph": g,
            "learner_states": l_states,
            "budget": int(state.get("budget", 10)),
            "deadline_days": int(state.get("deadline_days", 1)),
            "target_node": state.get("target_node") or state.get("target"),
            "current_day": int(state.get("current_day", 1)),
            "completed_nodes": set(state.get("completed_nodes", set())),
            "past_days": [dict(d) for d in state.get("past_days", [])],
            "past_trace": [dict(t) for t in state.get("past_trace", [])],
            "policy_version": state.get("policy_version", "static_baseline_v0"),
            "policy": state.get("policy"),
            "difficulty_states": dict(state.get("difficulty_states") or {})
        }
    else:
        g = getattr(state, "graph", getattr(state, "g", None))
        l_states = dict(getattr(state, "learner_states", getattr(state, "states", {})))
        return {
            "graph": g,
            "learner_states": l_states,
            "budget": int(getattr(state, "budget", 10)),
            "deadline_days": int(getattr(state, "deadline_days", 1)),
            "target_node": getattr(state, "target_node", getattr(state, "target", None)),
            "current_day": int(getattr(state, "current_day", 1)),
            "completed_nodes": set(getattr(state, "completed_nodes", set())),
            "past_days": [dict(d) for d in getattr(state, "past_days", [])],
            "past_trace": [dict(t) for t in getattr(state, "past_trace", [])],
            "policy_version": getattr(state, "policy_version", "static_baseline_v0"),
            "policy": getattr(state, "policy", None),
            "difficulty_states": dict(getattr(state, "difficulty_states", {}) or {})
        }


def replan(state: Union[ReplanState, Dict[str, Any]], event: Any) -> Dict[str, Any]:
    """
    Executes dynamic replanning for a single event:
    1. assessment_result(node, correct_flags): updates BKT learner state;
       dependents become admissible only after positive assessment.
    2. missed_day: records missed day without deleting or overwriting completed work.
    3. changed_budget(new_budget): updates daily budget and rechecks feasibility.
    4. changed_deadline(new_days): updates deadline days and rechecks feasibility.

    Replay rule: an event is applied once per call, and passing the same event twice applies it twice.

    Returns plan dictionary with days, trace (passing check_trace), and feasibility explanation.
    """
    ctx = _extract_state(state)
    g: nx.DiGraph = ctx["graph"]
    learner_states: Dict[str, ConceptState] = ctx["learner_states"]
    budget: int = ctx["budget"]
    deadline_days: int = ctx["deadline_days"]
    target_node: str = ctx["target_node"]
    current_day: int = ctx["current_day"]
    completed_nodes: Set[str] = ctx["completed_nodes"]
    past_days: List[Dict[str, Any]] = ctx["past_days"]
    past_trace: List[Dict[str, Any]] = ctx["past_trace"]
    policy_version: str = ctx["policy_version"]
    raw_policy = ctx.get("policy")
    difficulty_states: Dict[str, DifficultyState] = ctx["difficulty_states"]

    active_policy: PolicyConfig
    if raw_policy is None:
        active_policy, _ = default_policy()
    elif isinstance(raw_policy, tuple) and hasattr(raw_policy, "policy"):
        active_policy = raw_policy.policy
    else:
        active_policy = raw_policy

    candidate_universe = get_candidate_universe(g, target_node)

    # 1. Process Event
    if isinstance(event, AssessmentResultEvent) or (isinstance(event, dict) and event.get("type") == "assessment_result") or hasattr(event, "correct_flags"):
        node = event.node if hasattr(event, "node") else event["node"]
        flags = event.correct_flags if hasattr(event, "correct_flags") else event["correct_flags"]

        if node not in learner_states:
            learner_states[node] = ConceptState.cold_start()
        c_state = learner_states[node]
        for f in flags:
            c_state.update(f, policy=active_policy)

        if node not in difficulty_states:
            base_diff = g.nodes[node].get("base_difficulty", 0.5) if (g is not None and node in g) else 0.5
            difficulty_states[node] = DifficultyState(difficulty=base_diff)
        d_state = difficulty_states[node]
        for f in flags:
            d_state = step_difficulty(d_state, f)
        difficulty_states[node] = d_state

    elif isinstance(event, MissedDayEvent) or event == "missed_day" or (isinstance(event, dict) and event.get("type") == "missed_day"):
        # Record current day as missed
        missed_entry = {
            "day": current_day,
            "activities": [],
            "conditional_activities": [],
            "minutes_used": 0,
            "minutes_remaining": budget,
            "missed": True
        }
        past_days.append(missed_entry)

        # Trace candidate entries for the missed day
        for nid in sorted(list(candidate_universe)):
            st = learner_states.get(nid, ConceptState.cold_start())
            prereqs = set(g.predecessors(nid)).intersection(candidate_universe)
            prereq_status = {p: (p in completed_nodes or learner_states.get(p, ConceptState.cold_start()).classify(active_policy) == "Mastered") for p in prereqs}
            if learner_states.get(nid, ConceptState.cold_start()).classify(active_policy) == "Mastered":
                rc = ReasonCode.ALREADY_MASTERED
            elif nid in completed_nodes:
                rc = ReasonCode.COMPLETED
            elif not all(prereq_status.values()):
                rc = ReasonCode.PREREQUISITE_UNMET
            else:
                rc = ReasonCode.BUDGET_EXCEEDED

            t_entry = TraceEntry(
                node_id=nid,
                day=current_day,
                concept_state={
                    "p": st.p,
                    "kappa": st.kappa,
                    "sigma2": st.sigma2,
                    "n": st.n,
                    "class": st.classify(active_policy)
                },
                constraints={
                    "budget": budget,
                    "remaining_budget": 0,
                    "prerequisites": prereq_status
                },
                score_terms={"exercise_difficulty": difficulty_states[nid].difficulty} if nid in difficulty_states else {},
                decision="FILTERED",
                reason_code=rc,
                policy_version=policy_version
            )
            past_trace.append(t_entry.to_dict())

        current_day += 1

    elif isinstance(event, ChangedBudgetEvent) or hasattr(event, "new_budget") or (isinstance(event, dict) and "new_budget" in event):
        budget = int(event.new_budget if hasattr(event, "new_budget") else event["new_budget"])

    elif isinstance(event, ChangedDeadlineEvent) or hasattr(event, "new_days") or (isinstance(event, dict) and "new_days" in event):
        deadline_days = int(event.new_days if hasattr(event, "new_days") else event["new_days"])

    else:
        raise ValueError(f"Unknown event type: {event}")

    # 2. Recompute only future plan from current_day to deadline_days
    evidence_mastered = {
        nid for nid in candidate_universe
        if learner_states.get(nid, ConceptState.cold_start()).classify(active_policy) == "Mastered"
    }

    # Required remaining nodes (excluding already completed progress and evidence-Mastered nodes)
    required_nodes = {
        nid for nid in candidate_universe
        if nid not in evidence_mastered and nid not in completed_nodes
    }

    remaining_days = max(0, deadline_days - (current_day - 1))

    # Feasibility check for remaining future window
    status, feasibility_info = check_feasibility(g, required_nodes, budget, remaining_days)

    if status == FeasibilityStatus.INFEASIBLE_PROVED:
        reason_val = feasibility_info.get("reason_code")
        reason_str = reason_val.value if hasattr(reason_val, "value") else str(reason_val)

        no_plan_trace = {
            "status": status.value,
            "reason_code": reason_str,
            "constraints": {
                "budget": budget,
                "deadline_days": deadline_days
            }
        }
        return {
            "status": FeasibilityStatus.INFEASIBLE_PROVED,
            "feasibility_explanation": feasibility_info,
            "days": past_days,
            "trace": no_plan_trace,
            "completed_nodes": completed_nodes,
            "learner_states": learner_states,
            "difficulty_states": difficulty_states,
            "policy": active_policy,
            "target_node": target_node
        }

    # Deterministic topological sort of remaining required nodes
    subgraph = g.subgraph(required_nodes)
    try:
        topo_order = list(nx.lexicographical_topological_sort(subgraph))
    except nx.NetworkXUnfeasible as e:
        raise ValueError("Cyclic graph detected; cannot produce fallback plan.") from e

    planned: Dict[str, int] = {}
    remaining_nodes = list(topo_order)
    future_days = []
    future_trace = []
    assessment_candidates = set()

    for day_num in range(current_day, deadline_days + 1):
        rem_budget = budget
        day_activities = []
        conditional_activities = []
        scheduled_today = set()

        # Prior entries for nodes already mastered, completed, or scheduled on prior days
        for node_id in sorted(list(candidate_universe)):
            st = learner_states.get(node_id, ConceptState.cold_start())
            prereqs = set(g.predecessors(node_id)).intersection(candidate_universe)
            prereq_status = {p: True for p in prereqs}

            if node_id in evidence_mastered:
                t_entry = TraceEntry(
                    node_id=node_id,
                    day=day_num,
                    concept_state={
                        "p": st.p,
                        "kappa": st.kappa,
                        "sigma2": st.sigma2,
                        "n": st.n,
                        "class": st.classify(active_policy)
                    },
                    constraints={
                        "budget": budget,
                        "remaining_budget": rem_budget,
                        "prerequisites": prereq_status
                    },
                    score_terms={"exercise_difficulty": difficulty_states[node_id].difficulty} if node_id in difficulty_states else {},
                    decision="FILTERED",
                    reason_code=ReasonCode.ALREADY_MASTERED,
                    policy_version=policy_version
                )
                future_trace.append(t_entry.to_dict())
            elif node_id in completed_nodes:
                t_entry = TraceEntry(
                    node_id=node_id,
                    day=day_num,
                    concept_state={
                        "p": st.p,
                        "kappa": st.kappa,
                        "sigma2": st.sigma2,
                        "n": st.n,
                        "class": st.classify(active_policy)
                    },
                    constraints={
                        "budget": budget,
                        "remaining_budget": rem_budget,
                        "prerequisites": prereq_status
                    },
                    score_terms={"exercise_difficulty": difficulty_states[node_id].difficulty} if node_id in difficulty_states else {},
                    decision="FILTERED",
                    reason_code=ReasonCode.COMPLETED,
                    policy_version=policy_version
                )
                future_trace.append(t_entry.to_dict())
            elif node_id in planned and planned[node_id] < day_num:
                t_entry = TraceEntry(
                    node_id=node_id,
                    day=day_num,
                    concept_state={
                        "p": st.p,
                        "kappa": st.kappa,
                        "sigma2": st.sigma2,
                        "n": st.n,
                        "class": st.classify(active_policy)
                    },
                    constraints={
                        "budget": budget,
                        "remaining_budget": rem_budget,
                        "prerequisites": prereq_status
                    },
                    score_terms={"exercise_difficulty": difficulty_states[node_id].difficulty} if node_id in difficulty_states else {},
                    decision="FILTERED",
                    reason_code=ReasonCode.ALREADY_SCHEDULED,
                    policy_version=policy_version
                )
                future_trace.append(t_entry.to_dict())

        # Evaluate remaining nodes in topological order
        for node_id in list(remaining_nodes):
            st = learner_states.get(node_id, ConceptState.cold_start())
            dur = g.nodes[node_id].get("baseline_duration", 0)
            prereqs = set(g.predecessors(node_id)).intersection(candidate_universe)

            prereq_status = {}
            prereqs_met = True
            has_conditional_prereq = False
            uncertain_prereqs = []
            failed_prereqs = []

            for p in prereqs:
                p_st = learner_states.get(p, ConceptState.cold_start())
                p_class = p_st.classify(active_policy)

                if p in evidence_mastered:
                    prereq_status[p] = True
                elif p_class == "Weak":
                    prereq_status[p] = False
                    prereqs_met = False
                    failed_prereqs.append(p)
                elif p in planned and planned[p] < day_num:
                    prereq_status[p] = True
                    has_conditional_prereq = True
                elif p in scheduled_today:
                    prereq_status[p] = True
                    has_conditional_prereq = True
                elif p in completed_nodes and p_class not in ("Weak", "Uncertain"):
                    prereq_status[p] = True
                    has_conditional_prereq = True
                else:
                    prereq_status[p] = False
                    prereqs_met = False
                    if p_class == "Uncertain":
                        uncertain_prereqs.append(p)
                        assessment_candidates.add(p)
                    else:
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

            t_entry = TraceEntry(
                node_id=node_id,
                day=day_num,
                concept_state={
                    "p": st.p,
                    "kappa": st.kappa,
                    "sigma2": st.sigma2,
                    "n": st.n,
                    "class": st.classify(active_policy)
                },
                constraints={
                    "budget": budget,
                    "remaining_budget": cur_rem_budget,
                    "prerequisites": prereq_status,
                    "conditional": is_conditional,
                    "revalidate_before_execution": is_conditional
                },
                score_terms={"exercise_difficulty": difficulty_states[node_id].difficulty} if node_id in difficulty_states else {},
                decision=decision,
                reason_code=reason,
                policy_version=policy_version
            )
            future_trace.append(t_entry.to_dict())

        future_days.append({
            "day": day_num,
            "activities": day_activities,
            "conditional_activities": conditional_activities,
            "minutes_used": budget - rem_budget,
            "minutes_remaining": rem_budget
        })

    # Combine past progress with future plan
    all_days = past_days + future_days
    all_trace = past_trace + future_trace

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
        "days": all_days,
        "trace": all_trace,
        "completed_nodes": completed_nodes,
        "learner_states": learner_states,
        "difficulty_states": difficulty_states,
        "assessment_candidates": sorted(list(assessment_candidates)),
        "current_day": current_day,
        "budget": budget,
        "deadline_days": deadline_days,
        "policy": active_policy,
        "target_node": target_node
    }
