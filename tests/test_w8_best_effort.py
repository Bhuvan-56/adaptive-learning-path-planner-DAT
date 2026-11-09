"""W8 fix 2: best-effort work on deadline-infeasible days (docs/w8/preregistration.md).

When the remaining work no longer fits before the deadline (CAPACITY_EXCEEDED),
replan keeps the INFEASIBLE_PROVED result and its necessary fixes, and also
returns best_effort_days / best_effort_trace: what fits, under the same
prerequisite gate and daily budget. The adaptive loop runs that work instead of
idling.
"""
import pytest
import yaml

from src.curriculum.graph import load_graph
from src.evaluation import integrated
from src.planning.feasibility import FeasibilityStatus, InfeasibilityReason
from src.planning.replan import ReplanState, assessment_result, changed_budget, replan
from src.planning.review import ReviewLog
from src.state.learner_state import ConceptState
from src.state.policy import default_policy
from src.trace.checker import check_no_plan_trace, check_trace
from src.trace.universe import get_candidate_universe

CURRICULUM = "data/curricula/demo_curriculum.json"
W8_FINAL = "experiments/w8_final.yaml"
POLICY, _ = default_policy()


def _state(answers):
    st = ConceptState.cold_start()
    for a in answers:
        st.update(int(a), policy=POLICY)
    return st


def _infeasible_state(g, deadline_days=2):
    # A is mastered and completed; B (5) + C (10) + D (10) = 25 minutes > 2 x 10.
    states = {n: _state("") for n in g.nodes}
    states["A"] = _state("1111")
    return ReplanState(graph=g, learner_states=states, budget=10, deadline_days=deadline_days,
                       target_node="D", completed_nodes={"A"}, current_day=1,
                       review_log=ReviewLog(), policy=POLICY)


@pytest.mark.xfail(strict=True, reason="W8: replan returns no work on deadline-infeasible days")
def test_capacity_infeasible_replan_returns_best_effort_days():
    g = load_graph(CURRICULUM)
    plan = replan(_infeasible_state(g), assessment_result("A", [1]))

    # The infeasibility report is unchanged.
    assert plan["status"] == FeasibilityStatus.INFEASIBLE_PROVED
    assert plan["feasibility_explanation"]["reason_code"] == InfeasibilityReason.CAPACITY_EXCEEDED
    assert "necessary_not_sufficient_fixes" in plan["feasibility_explanation"]
    assert isinstance(plan["trace"], dict) and check_no_plan_trace(plan["trace"])

    # And the work that fits is planned.
    days = {d["day"]: d for d in plan["best_effort_days"]}
    assert days[1]["activities"] == ["B"]
    assert days[2]["activities"] == ["C"]
    assert all(d["minutes_used"] <= 10 for d in plan["best_effort_days"])
    assert check_trace(get_candidate_universe(g, "D"), plan["best_effort_trace"], num_days=2, budget=10)


@pytest.mark.xfail(strict=True, reason="W8: replan returns no work on deadline-infeasible days")
def test_best_effort_never_breaks_prerequisites():
    g = load_graph(CURRICULUM)
    plan = replan(_infeasible_state(g, deadline_days=1), changed_budget(10))
    done = {"A"}
    for d in sorted(plan["best_effort_days"], key=lambda e: e["day"]):
        for nid in d["activities"]:
            assert all(p in done for p in g.predecessors(nid)), (nid, d)
        done |= set(d["activities"])
    assert plan["best_effort_days"][0]["activities"] == ["B"]


def test_block_exceeds_budget_has_no_best_effort_plan():
    # An activity longer than the daily budget can never run: no partial plan.
    g = load_graph(CURRICULUM)
    st = _infeasible_state(g, deadline_days=5)
    plan = replan(st, changed_budget(8))
    assert plan["status"] == FeasibilityStatus.INFEASIBLE_PROVED
    assert plan["feasibility_explanation"]["reason_code"] == InfeasibilityReason.BLOCK_EXCEEDS_DAILY_BUDGET
    assert not plan.get("best_effort_days")


@pytest.mark.xfail(strict=True, reason="W8: adaptive loop idles when the first plan is infeasible")
def test_integrated_adaptive_arm_works_on_infeasible_horizon(tmp_path, monkeypatch):
    with open(W8_FINAL, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["seeds"] = [42]
    cfg["planner_controls"]["horizon_days"] = 2  # 20 minutes of capacity, up to 30 of work
    cfg["arms"]["primary"] = ["adaptive_full", "static_prerequisite_order", "non_adaptive_greedy"]
    cfg["arms"]["ablations"]["enabled"] = False
    cfg_path = tmp_path / "w8_infeasible.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    seen = []
    original = integrated.recount_plan_violations

    def spy(executed_days, g, daily_budget):
        seen.append([list(d["activities"]) for d in executed_days])
        return original(executed_days, g, daily_budget)

    monkeypatch.setattr(integrated, "recount_plan_violations", spy)
    n = 6
    res = integrated.run_integrated_evaluation(config_path=str(cfg_path), output_dir=str(tmp_path / "out"),
                                               override_learners=n, override_resamples=50)

    adaptive = seen[:n]  # arms run in config order, adaptive_full first
    assert any(acts for days in adaptive for acts in days), adaptive
    r = res["arm_results"]["adaptive_full"]
    assert r.total_prereq_violations == 0 and r.total_budget_violations == 0
    assert r.trace_coverage == 100.0
