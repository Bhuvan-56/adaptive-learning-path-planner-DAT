from dataclasses import dataclass, field
from typing import Dict, List, Any, Set, Optional, Union
import networkx as nx

from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig, default_policy
from src.planning.feasibility import check_feasibility, FeasibilityStatus, InfeasibilityReason
from src.trace.schema import TraceEntry, ReasonCode
from src.trace.universe import get_candidate_universe
from src.planning.difficulty import DifficultyState, step_difficulty
from src.planning.review import (
    ReviewLog,
    ReviewRecord,
    is_review_eligible,
    calculate_recall_decay,
    get_remediation_ancestors,
    load_review_eval_config,
    load_remediation_config,
    DECAY_BASELINE,
)


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
    review_log: Optional[ReviewLog] = None


def _extract_state(state: Any) -> Dict[str, Any]:
    if isinstance(state, dict):
        g = state.get("graph") or state.get("g")
        l_states = dict(state.get("learner_states") or state.get("states", {}))
        raw_rl = state.get("review_log")
        if raw_rl is None:
            review_log = ReviewLog()
        elif isinstance(raw_rl, ReviewLog):
            review_log = raw_rl
        elif isinstance(raw_rl, dict):
            review_log = ReviewLog(records=dict(raw_rl))
        else:
            review_log = raw_rl

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
            "difficulty_states": dict(state.get("difficulty_states") or {}),
            "review_log": review_log,
        }
    else:
        g = getattr(state, "graph", getattr(state, "g", None))
        l_states = dict(getattr(state, "learner_states", getattr(state, "states", {})))
        raw_rl = getattr(state, "review_log", None)
        if raw_rl is None:
            review_log = ReviewLog()
        elif isinstance(raw_rl, ReviewLog):
            review_log = raw_rl
        elif isinstance(raw_rl, dict):
            review_log = ReviewLog(records=dict(raw_rl))
        else:
            review_log = raw_rl

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
            "difficulty_states": dict(getattr(state, "difficulty_states", {}) or {}),
            "review_log": review_log,
        }


def replan(state: Union[ReplanState, Dict[str, Any]], event: Any) -> Dict[str, Any]:
    """
    Executes dynamic replanning for a single event:
    1. assessment_result(node, correct_flags): updates BKT learner state;
       records attempts in review_log; steps exercise difficulty;
       if k consecutive failures occur, triggers prerequisite remediation.
    2. missed_day: records missed day without deleting or overwriting completed work.
    3. changed_budget(new_budget): updates daily budget and rechecks feasibility.
    4. changed_deadline(new_days): updates deadline days and rechecks feasibility.

    Daily Budget Rule (PROPOSED):
    Remediation first, then planned work toward the target, then due reviews
    fill the leftover budget, lowest recall first. A review that does not fit
    is traced with the existing BUDGET_EXCEEDED code. Reviews never displace required work.

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
    review_log: ReviewLog = ctx["review_log"]

    try:
        remediation_k = load_remediation_config()
    except Exception:
        remediation_k = 2

    try:
        eval_cfg = load_review_eval_config()
        h_days = eval_cfg["half_life_prior_days"]
        review_thresh = eval_cfg["review_eligibility_recall_threshold"]
    except Exception:
        h_days = 14.0
        review_thresh = 0.85

    active_policy: PolicyConfig
    if raw_policy is None:
        active_policy, _ = default_policy()
    elif isinstance(raw_policy, tuple) and hasattr(raw_policy, "policy"):
        active_policy = raw_policy.policy
    else:
        active_policy = raw_policy

    candidate_universe = get_candidate_universe(g, target_node)

    # 1. Process Event
    remediation_ancestors: List[str] = []
    if isinstance(event, AssessmentResultEvent) or (isinstance(event, dict) and event.get("type") == "assessment_result") or hasattr(event, "correct_flags"):
        node = event.node if hasattr(event, "node") else event["node"]
        flags = event.correct_flags if hasattr(event, "correct_flags") else event["correct_flags"]

        if node not in learner_states:
            learner_states[node] = ConceptState.cold_start()
        c_state = learner_states[node]
        for f in flags:
            c_state.update(f, policy=active_policy)
            review_log.record_attempt(node, time_in_days=float(current_day), correct=bool(f))

        if node not in difficulty_states:
            base_diff = g.nodes[node].get("base_difficulty", 0.5) if (g is not None and node in g) else 0.5
            difficulty_states[node] = DifficultyState(difficulty=base_diff)
        d_state = difficulty_states[node]
        for f in flags:
            d_state = step_difficulty(d_state, f)
        difficulty_states[node] = d_state

        # Check prerequisite remediation trigger on k consecutive failures
        if review_log.get_consecutive_failures(node) >= remediation_k:
            remediation_ancestors = get_remediation_ancestors(
                g, node, learner_states, policy=active_policy, completed_nodes=completed_nodes
            )

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

    # Check if any remediation ancestor fundamentally cannot fit into any day's budget
    for r_anc in remediation_ancestors:
        dur = g.nodes[r_anc].get("baseline_duration", 0)
        if dur > budget:
            reason_str = ReasonCode.BLOCK_EXCEEDS_DAILY_BUDGET.value
            no_plan_trace = {
                "status": FeasibilityStatus.INFEASIBLE_PROVED.value,
                "reason_code": reason_str,
                "constraints": {
                    "budget": budget,
                    "deadline_days": deadline_days
                }
            }
            return {
                "status": FeasibilityStatus.INFEASIBLE_PROVED,
                "feasibility_explanation": {
                    "status": FeasibilityStatus.INFEASIBLE_PROVED.value,
                    "reason_code": reason_str,
                    "blocking_node": r_anc,
                    "node_duration": dur,
                    "budget": budget
                },
                "days": past_days,
                "trace": no_plan_trace,
                "completed_nodes": completed_nodes,
                "learner_states": learner_states,
                "difficulty_states": difficulty_states,
                "review_log": review_log,
                "policy": active_policy,
                "target_node": target_node
            }

    # 2. Recompute only future plan from current_day to deadline_days
    evidence_mastered = {
        nid for nid in candidate_universe
        if learner_states.get(nid, ConceptState.cold_start()).classify(active_policy) == "Mastered"
    }

    # Required remaining nodes (excluding already completed progress and evidence-Mastered nodes)
    # plus any triggered remediation ancestors
    required_nodes = {
        nid for nid in candidate_universe
        if nid not in evidence_mastered and nid not in completed_nodes
    } | set(remediation_ancestors)

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
            "review_log": review_log,
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
    remaining_nodes = [nid for nid in topo_order if nid not in remediation_ancestors]
    remed_queue = list(remediation_ancestors)
    future_days = []
    future_trace = []
    assessment_candidates = set()

    for day_num in range(current_day, deadline_days + 1):
        rem_budget = budget
        day_activities = []
        conditional_activities = []
        scheduled_today = set()
        day_trace_map: Dict[str, Dict[str, Any]] = {}

        # -------------------------------------------------------------
        # Part 1: Remediation first inside the daily budget
        # -------------------------------------------------------------
        for r_node in list(remed_queue):
            if r_node in scheduled_today or r_node in completed_nodes:
                continue

            dur = g.nodes[r_node].get("baseline_duration", 0)
            prereqs = set(g.predecessors(r_node)).intersection(candidate_universe)
            prereq_status = {
                p: (p in evidence_mastered or p in completed_nodes or p in scheduled_today or (p in planned and planned[p] < day_num))
                for p in prereqs
            }
            prereqs_met = all(prereq_status.values())
            cur_rem = rem_budget
            st = learner_states.get(r_node, ConceptState.cold_start())

            if not prereqs_met:
                decision = "FILTERED"
                reason = ReasonCode.PREREQUISITE_UNMET
                day_trace_map[r_node] = TraceEntry(
                    node_id=r_node,
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
                        "remaining_budget": cur_rem,
                        "prerequisites": prereq_status
                    },
                    score_terms={"exercise_difficulty": difficulty_states[r_node].difficulty} if r_node in difficulty_states else {},
                    decision=decision,
                    reason_code=reason,
                    policy_version=policy_version
                ).to_dict()
            elif dur > rem_budget:
                decision = "FILTERED"
                reason = ReasonCode.BLOCK_EXCEEDS_DAILY_BUDGET if dur > budget else ReasonCode.BUDGET_EXCEEDED
                day_trace_map[r_node] = TraceEntry(
                    node_id=r_node,
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
                        "remaining_budget": cur_rem,
                        "prerequisites": prereq_status
                    },
                    score_terms={"exercise_difficulty": difficulty_states[r_node].difficulty} if r_node in difficulty_states else {},
                    decision=decision,
                    reason_code=reason,
                    policy_version=policy_version
                ).to_dict()
                break
            else:
                decision = "SELECTED"
                reason = ReasonCode.REMEDIATION_TRIGGERED
                day_activities.append(r_node)
                scheduled_today.add(r_node)
                planned[r_node] = day_num
                rem_budget -= dur
                remed_queue.remove(r_node)
                if r_node in remaining_nodes:
                    remaining_nodes.remove(r_node)

                day_trace_map[r_node] = TraceEntry(
                    node_id=r_node,
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
                        "remaining_budget": cur_rem,
                        "prerequisites": prereq_status
                    },
                    score_terms={"exercise_difficulty": difficulty_states[r_node].difficulty} if r_node in difficulty_states else {},
                    decision=decision,
                    reason_code=reason,
                    policy_version=policy_version
                ).to_dict()

        # -------------------------------------------------------------
        # Part 2: Planned work toward the target
        # -------------------------------------------------------------
        for node_id in list(remaining_nodes):
            if node_id in day_trace_map:
                continue

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

            day_trace_map[node_id] = TraceEntry(
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
            ).to_dict()

        # -------------------------------------------------------------
        # Part 3: Due reviews fill leftover budget, lowest recall first
        # -------------------------------------------------------------
        due_candidates: List[Tuple[float, str]] = []
        for nid in candidate_universe:
            if nid not in evidence_mastered or nid in scheduled_today or nid in day_trace_map:
                continue
            is_elig, recall_val = is_review_eligible(
                nid,
                learner_states.get(nid, ConceptState.cold_start()),
                review_log,
                current_day=float(day_num),
                policy=active_policy,
                half_life_days=h_days,
                threshold=review_thresh
            )
            if is_elig:
                due_candidates.append((recall_val, nid))

        # Lowest recall first, tie-break by node_id alphabetically
        due_candidates.sort(key=lambda x: (x[0], x[1]))

        for recall_val, r_nid in due_candidates:
            st = learner_states.get(r_nid, ConceptState.cold_start())
            dur = g.nodes[r_nid].get("baseline_duration", 0)
            prereqs = set(g.predecessors(r_nid)).intersection(candidate_universe)
            prereq_status = {p: True for p in prereqs}
            cur_rem = rem_budget

            if dur <= rem_budget:
                decision = "SELECTED"
                reason = ReasonCode.REVIEW_DUE
                day_activities.append(r_nid)
                scheduled_today.add(r_nid)
                rem_budget -= dur
                # In simulation, record review attempt so it won't be immediately due next day
                review_log.record_attempt(r_nid, time_in_days=float(day_num), correct=True)
            else:
                decision = "FILTERED"
                reason = ReasonCode.BUDGET_EXCEEDED

            day_trace_map[r_nid] = TraceEntry(
                node_id=r_nid,
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
                    "remaining_budget": cur_rem,
                    "prerequisites": prereq_status
                },
                score_terms={"exercise_difficulty": difficulty_states[r_nid].difficulty} if r_nid in difficulty_states else {},
                decision=decision,
                reason_code=reason,
                policy_version=policy_version
            ).to_dict()

        # -------------------------------------------------------------
        # Part 4: Remaining candidate universe nodes for today
        # -------------------------------------------------------------
        for nid in sorted(list(candidate_universe)):
            if nid in day_trace_map:
                continue

            st = learner_states.get(nid, ConceptState.cold_start())
            prereqs = set(g.predecessors(nid)).intersection(candidate_universe)
            prereq_status = {p: True for p in prereqs}

            if nid in evidence_mastered:
                rc = ReasonCode.ALREADY_MASTERED
            elif nid in completed_nodes:
                rc = ReasonCode.COMPLETED
            elif nid in planned and planned[nid] < day_num:
                rc = ReasonCode.ALREADY_SCHEDULED
            else:
                rc = ReasonCode.PREREQUISITE_UNMET

            day_trace_map[nid] = TraceEntry(
                node_id=nid,
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
                score_terms={"exercise_difficulty": difficulty_states[nid].difficulty} if nid in difficulty_states else {},
                decision="FILTERED",
                reason_code=rc,
                policy_version=policy_version
            ).to_dict()

        # Append all entries in sorted candidate universe order for this day
        for nid in sorted(list(candidate_universe)):
            future_trace.append(day_trace_map[nid])

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

    if remaining_nodes or remed_queue:
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
        "review_log": review_log,
        "assessment_candidates": sorted(list(assessment_candidates)),
        "current_day": current_day,
        "budget": budget,
        "deadline_days": deadline_days,
        "policy": active_policy,
        "target_node": target_node
    }
