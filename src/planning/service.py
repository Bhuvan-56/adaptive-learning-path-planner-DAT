from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
import math
import networkx as nx

from src.curriculum.graph import validate_graph
from src.curriculum.errors import GraphErrorCode
from src.state.learner_state import ConceptState
from src.state.policy import PolicyConfig, default_policy
from src.planning.static_baseline import generate_static_plan


@dataclass
class PlanResult:
    """Structured result returned by plan_request."""
    is_valid: bool
    status: str
    error_codes: List[str] = field(default_factory=list)
    message: str = ""
    plan: Optional[Dict[str, Any]] = None

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        if self.plan and item in self.plan:
            return self.plan[item]
        raise KeyError(item)

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default


def plan_request(
    graph: nx.DiGraph,
    learner_states: Dict[str, ConceptState],
    budget: int,
    deadline_days: int,
    targets: Union[str, List[str]],
    policy: Optional[PolicyConfig] = None
) -> PlanResult:
    """
    Validates all request inputs before generating a learning plan:
    1. Graph integrity (including cycles and non-finite values) via validate_graph.
    2. Budget is a positive finite integer.
    3. Deadline_days is a positive integer.
    4. Targets exist in the graph.

    Returns structured PlanResult with is_valid=False and error_codes if invalid.
    If valid, returns PlanResult with plan payload.
    """
    # 1. Graph validation
    graph_errors = validate_graph(graph)
    if graph_errors:
        codes = [e.value if hasattr(e, "value") else str(e) for e in graph_errors]
        return PlanResult(
            is_valid=False,
            status="INVALID_INPUT",
            error_codes=codes,
            message=f"Graph validation failed: {codes}"
        )

    # 2. Budget validation
    if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0 or not math.isfinite(budget):
        return PlanResult(
            is_valid=False,
            status="INVALID_INPUT",
            error_codes=["INVALID_BUDGET"],
            message=f"Budget must be a positive integer, got {budget}"
        )

    # 3. Deadline validation
    if not isinstance(deadline_days, int) or isinstance(deadline_days, bool) or deadline_days <= 0:
        return PlanResult(
            is_valid=False,
            status="INVALID_INPUT",
            error_codes=["INVALID_DEADLINE"],
            message=f"Deadline days must be a positive integer, got {deadline_days}"
        )

    # 4. Target validation
    if targets is None:
        target_list = []
    elif isinstance(targets, str):
        target_list = [targets]
    elif isinstance(targets, (list, tuple, set)):
        target_list = list(targets)
    else:
        target_list = []

    if not target_list:
        return PlanResult(
            is_valid=False,
            status="INVALID_INPUT",
            error_codes=["TARGET_NOT_FOUND"],
            message="Targets list cannot be empty"
        )

    missing = [t for t in target_list if t not in graph.nodes]
    if missing:
        return PlanResult(
            is_valid=False,
            status="INVALID_INPUT",
            error_codes=["TARGET_NOT_FOUND"],
            message=f"Target node(s) not found in graph: {missing}"
        )

    # 5. Policy resolution
    active_policy: PolicyConfig
    if policy is None:
        active_policy, _ = default_policy()
    elif isinstance(policy, tuple) and hasattr(policy, "policy"):
        active_policy = policy.policy
    else:
        active_policy = policy

    # Generate plan
    primary_target = target_list[0]
    plan = generate_static_plan(
        g=graph,
        learner_states=learner_states,
        budget=budget,
        deadline_days=deadline_days,
        target_node=primary_target
    )

    plan_status = plan.get("status")
    status_str = plan_status.value if hasattr(plan_status, "value") else str(plan_status)

    return PlanResult(
        is_valid=True,
        status=status_str,
        error_codes=[],
        message="Plan generated successfully",
        plan=plan
    )
