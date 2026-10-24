"""
Tests for Module WP9: Execution Gate and Conditional Plan Execution.

Verifies that is_admissible correctly enforces the execution gate when walking
a conditional plan day by day with a test-side executor, without creating any second
admissibility rule.
"""

from typing import Set, Dict, Any, Optional
import networkx as nx
import pytest

from src.planning.admissibility import is_admissible
from src.state.learner_state import ConceptState
from src.planning.static_baseline import generate_static_plan
from src.planning.replan import replan, assessment_result, missed_day


class PlanExecutorHarness:
    """
    Test-side execution harness walking a multi-day plan.
    Strictly uses is_admissible(allow_conditional=False) to gate execution of activities.
    """
    def __init__(
        self,
        graph: nx.DiGraph,
        budget: int,
        deadline_days: int,
        target_node: str,
        initial_states: Optional[Dict[str, ConceptState]] = None
    ):
        self.g = graph
        self.budget = budget
        self.deadline_days = deadline_days
        self.target_node = target_node
        self.learner_states = initial_states or {n: ConceptState.cold_start() for n in graph.nodes}
        self.completed_nodes: Set[str] = set()
        self.mastered_set: Set[str] = set()
        self.current_day: int = 1

    def check_admissible_for_execution(self, node_id: str, rem_budget: Optional[int] = None) -> bool:
        """Evaluates whether an activity is allowed to execute today via is_admissible."""
        dur = self.g.nodes[node_id].get("baseline_duration", 0)
        rem = rem_budget if rem_budget is not None else self.budget
        act = {
            "node_id": node_id,
            "duration": dur,
            "prerequisites": list(self.g.predecessors(node_id))
        }
        return is_admissible(
            activity=act,
            selected_set=set(),
            mastered_set=self.mastered_set,
            remaining_budget=rem,
            g=self.g,
            planned_set=None,
            allow_conditional=False,
            learner_states=self.learner_states
        )


def build_prereq_graph():
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5, base_difficulty=0.50)
    g.add_node("B", baseline_duration=5, base_difficulty=0.50)
    g.add_edge("A", "B")
    return g


def test_gate_case_1_scheduled_only_prerequisite_keeps_dependent_blocked():
    """
    Case 1: Prerequisite A is scheduled on Day 1, but has not reached evidence-Mastered.
    Dependent B on Day 2 remains blocked at execution time.
    """
    g = build_prereq_graph()
    executor = PlanExecutorHarness(g, budget=5, deadline_days=2, target_node="B")

    # On Day 1: A is admissible to schedule/execute
    assert executor.check_admissible_for_execution("A") is True

    # "Execute" A on Day 1 without scored assessment evidence (still Uncertain)
    executor.completed_nodes.add("A")
    assert executor.learner_states["A"].classify() == "Uncertain"
    # A was scheduled and completed, but NOT evidence-mastered (not in mastered_set)

    # On Day 2: B is evaluated for execution. Because allow_conditional=False and A not in mastered_set,
    # is_admissible blocks B.
    assert executor.check_admissible_for_execution("B") is False


def test_gate_case_2_failed_assessment_keeps_dependent_blocked():
    """
    Case 2: Prerequisite A completes with failed assessment evidence (Weak state).
    Dependent B remains blocked.
    """
    g = build_prereq_graph()
    executor = PlanExecutorHarness(g, budget=5, deadline_days=2, target_node="B")

    # Assessment on A fails
    for _ in range(4):
        executor.learner_states["A"].update(0)
    assert executor.learner_states["A"].classify() == "Weak"
    executor.completed_nodes.add("A")

    # Day 2: B is evaluated. Weak prerequisite blocks B.
    assert executor.check_admissible_for_execution("B") is False


def test_gate_case_3_missed_day_keeps_dependent_blocked_and_preserves_work():
    """
    Case 3: A day is missed. Dependent B remains blocked, but previously completed work is preserved.
    """
    g = nx.DiGraph()
    g.add_node("P", baseline_duration=5, base_difficulty=0.50)
    g.add_node("A", baseline_duration=5, base_difficulty=0.50)
    g.add_node("B", baseline_duration=5, base_difficulty=0.50)
    g.add_edge("P", "A")
    g.add_edge("A", "B")

    executor = PlanExecutorHarness(g, budget=5, deadline_days=4, target_node="B")

    # Day 1: P completes and reaches Mastered
    for _ in range(4):
        executor.learner_states["P"].update(1)
    executor.mastered_set.add("P")
    executor.completed_nodes.add("P")
    assert executor.learner_states["P"].classify() == "Mastered"

    # Day 2 is missed!
    plan_state = {
        "graph": g,
        "learner_states": executor.learner_states,
        "budget": 5,
        "deadline_days": 4,
        "target_node": "B",
        "current_day": 2,
        "completed_nodes": executor.completed_nodes
    }
    replan_result = replan(plan_state, missed_day())
    assert replan_result["days"][0]["missed"] is True
    # Completed work is preserved
    assert "P" in replan_result["completed_nodes"]

    # Day 3: A has not been executed or mastered yet. B must remain blocked!
    assert executor.check_admissible_for_execution("B") is False
    # P is still Mastered and preserved
    assert "P" in executor.mastered_set


def test_gate_case_4_passed_assessment_releases_dependent():
    """
    Case 4: Prerequisite A receives enough passed evidence to classify Mastered.
    Dependent B is released for execution.
    """
    g = build_prereq_graph()
    executor = PlanExecutorHarness(g, budget=5, deadline_days=2, target_node="B")

    # Day 1: A passes assessment with quorum
    for _ in range(4):
        executor.learner_states["A"].update(1)
    assert executor.learner_states["A"].classify() == "Mastered"
    executor.mastered_set.add("A")
    executor.completed_nodes.add("A")

    # Day 2: B is evaluated for execution. Prerequisite A is Mastered in mastered_set.
    # is_admissible allows B to execute!
    assert executor.check_admissible_for_execution("B") is True
