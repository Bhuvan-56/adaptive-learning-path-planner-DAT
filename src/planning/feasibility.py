import math
from enum import Enum
from typing import Dict, List, Any, Set, Tuple
import networkx as nx


class FeasibilityStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE_PROVED = "INFEASIBLE_PROVED"
    HEURISTIC_NO_PLAN = "HEURISTIC_NO_PLAN"
    CAPACITY_CHECK_PASSED = "CAPACITY_CHECK_PASSED"


class InfeasibilityReason(str, Enum):
    BLOCK_EXCEEDS_DAILY_BUDGET = "BLOCK_EXCEEDS_DAILY_BUDGET"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    SCHEDULING_CONSTRAINTS_UNMET = "SCHEDULING_CONSTRAINTS_UNMET"


def check_feasibility(
    g: nx.DiGraph,
    required_nodes: Set[str],
    budget: int,
    deadline_days: int
) -> Tuple[FeasibilityStatus, Dict[str, Any]]:
    """
    Evaluates path feasibility using strict mathematical checks:
    1. Per-activity check: if any required activity duration > budget, returns INFEASIBLE_PROVED
       with BLOCK_EXCEEDS_DAILY_BUDGET and minimum budget fix.
    2. Aggregate capacity check: if total work W_req > deadline_days * budget, returns INFEASIBLE_PROVED
       with CAPACITY_EXCEEDED and necessary (not sufficient) fixes.
    3. Otherwise returns CAPACITY_CHECK_PASSED pending solver execution.
    """
    if not required_nodes:
        return FeasibilityStatus.CAPACITY_CHECK_PASSED, {"status": FeasibilityStatus.CAPACITY_CHECK_PASSED, "message": "No required activities."}

    # 1. Per-activity check
    offending_nodes = []
    max_duration = 0
    for node_id in required_nodes:
        dur = g.nodes[node_id].get("baseline_duration", 0)
        if dur > budget:
            offending_nodes.append(node_id)
            if dur > max_duration:
                max_duration = dur

    if offending_nodes:
        return FeasibilityStatus.INFEASIBLE_PROVED, {
            "status": FeasibilityStatus.INFEASIBLE_PROVED,
            "reason_code": InfeasibilityReason.BLOCK_EXCEEDS_DAILY_BUDGET,
            "offending_nodes": offending_nodes,
            "minimum_fix": f"raise daily budget to at least {max_duration} minutes",
            "notes": "Adding extra days will not resolve an indivisible activity duration constraint."
        }

    # 2. Aggregate check
    if deadline_days <= 0:
        return FeasibilityStatus.INFEASIBLE_PROVED, {
            "status": FeasibilityStatus.INFEASIBLE_PROVED,
            "reason_code": InfeasibilityReason.CAPACITY_EXCEEDED,
            "message": "deadline_days must be greater than zero.",
            "necessary_not_sufficient_fixes": {
                "extend_deadline_by_days": 1,
                "increase_daily_budget_by_minutes": 0
            }
        }

    w_req = sum(g.nodes[node_id].get("baseline_duration", 0) for node_id in required_nodes)
    total_capacity = deadline_days * budget

    if w_req > total_capacity:
        x_days = max(0, math.ceil(w_req / budget) - deadline_days) if budget > 0 else 0
        y_minutes = max(0, math.ceil(w_req / deadline_days) - budget) if deadline_days > 0 else 0
        return FeasibilityStatus.INFEASIBLE_PROVED, {
            "status": FeasibilityStatus.INFEASIBLE_PROVED,
            "reason_code": InfeasibilityReason.CAPACITY_EXCEEDED,
            "w_req": w_req,
            "total_capacity": total_capacity,
            "necessary_not_sufficient_fixes": {
                "extend_deadline_by_days": x_days,
                "increase_daily_budget_by_minutes": y_minutes
            },
            "notes": "Calculated fixes are necessary lower bounds, but not guaranteed sufficient due to block indivisibility."
        }

    return FeasibilityStatus.CAPACITY_CHECK_PASSED, {
        "status": FeasibilityStatus.CAPACITY_CHECK_PASSED,
        "w_req": w_req,
        "total_capacity": total_capacity
    }
