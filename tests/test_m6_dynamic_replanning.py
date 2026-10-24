import networkx as nx

from src.planning.service import plan_request
from src.state.policy import PolicyConfig
from tests.test_m6_replanning_events import (
    ConceptState,
    FeasibilityStatus,
    InfeasibilityReason,
    ReplanState,
    changed_budget,
    check_no_plan_trace,
    check_trace,
    missed_day,
    replan,
)


def test_tc_6_1_missed_day_triggers_dynamic_replanning_without_overwriting_progress():
    """
    TC-6.1: Missed day keeps completed work and recomputes future plan under supplied non-default policy.
    Runs through plan_request and replan with non-default policy.
    """
    g = nx.DiGraph()
    g.add_node("A", baseline_duration=5, base_difficulty=0.2)
    g.add_node("B", baseline_duration=5, base_difficulty=0.2)
    g.add_edge("A", "B")

    policy = PolicyConfig(mastered_p=0.90, window_size=4, p_T=0.15)
    states = {
        "A": ConceptState.cold_start(),
        "B": ConceptState.cold_start(),
    }

    # Step 1: Initial Day 1 planning through plan_request
    init_res = plan_request(g, states, budget=5, deadline_days=3, targets="B", policy=policy)
    assert init_res.is_valid
    assert init_res.plan["days"][0]["activities"] == ["A"]

    # Step 2: Day 1 completed; learner mastered concept A under non-default policy (p=0.92 >= 0.90)
    states["A"] = ConceptState(A=9.2, B=0.8, n=4, history=[1, 1, 1, 1])
    assert states["A"].classify(policy) == "Mastered"

    past_days = [dict(init_res.plan["days"][0])]
    past_trace = [dict(e) for e in init_res.plan["trace"] if e["day"] == 1]

    state = ReplanState(
        graph=g,
        learner_states=states,
        budget=5,
        deadline_days=3,
        target_node="B",
        current_day=2,
        completed_nodes={"A"},
        past_days=past_days,
        past_trace=past_trace,
        policy=policy,
    )

    # Step 3: Event - missed day on Day 2
    evt = missed_day()
    result = replan(state, evt)

    # Assertions:
    # 1. Completed work A is not deleted or overwritten
    assert "A" in result["completed_nodes"]
    assert result["days"][0]["activities"] == ["A"]

    # 2. Day 2 is recorded as missed
    assert result["days"][1]["missed"] is True
    assert result["days"][1]["activities"] == []

    # 3. Day 3 recomputes and schedules B
    assert "B" in result["days"][2]["activities"]

    # 4. Entire trace passes check_trace for all 3 days
    universe = {"A", "B"}
    assert check_trace(universe, result["trace"], num_days=3)


def test_tc_6_2_reduced_budget_outputs_valid_plan_or_infeasibility_trace_with_alternatives():
    """
    TC-6.2: Reduced budget gives either a valid plan or a structured infeasibility trace with alternatives.
    Runs through plan_request and replan with supplied non-default policy.
    """
    policy = PolicyConfig(mastered_p=0.90, p_T=0.15)

    # Subtest A: Feasible case (activities fit reduced budget 5)
    g_fea = nx.DiGraph()
    g_fea.add_node("A", baseline_duration=4, base_difficulty=0.2)
    g_fea.add_node("B", baseline_duration=4, base_difficulty=0.2)
    g_fea.add_edge("A", "B")

    states_fea = {"A": ConceptState.cold_start(), "B": ConceptState.cold_start()}
    init_res_fea = plan_request(g_fea, states_fea, budget=10, deadline_days=2, targets="B", policy=policy)
    assert init_res_fea.is_valid

    state_fea = ReplanState(
        graph=g_fea,
        learner_states=states_fea,
        budget=10,
        deadline_days=2,
        target_node="B",
        current_day=1,
        policy=policy,
    )
    res_fea = replan(state_fea, changed_budget(5))
    assert res_fea["status"] == FeasibilityStatus.FEASIBLE
    assert len(res_fea["days"]) == 2
    assert "A" in res_fea["days"][0]["activities"]
    assert "B" in res_fea["days"][1]["activities"]
    assert check_trace({"A", "B"}, res_fea["trace"], num_days=2)

    # Subtest B: Infeasible case (task duration 6 exceeds reduced budget 5)
    g_inf = nx.DiGraph()
    g_inf.add_node("A", baseline_duration=6, base_difficulty=0.2)

    states_inf = {"A": ConceptState.cold_start()}
    init_res_inf = plan_request(g_inf, states_inf, budget=10, deadline_days=2, targets="A", policy=policy)
    assert init_res_inf.is_valid

    state_inf = ReplanState(
        graph=g_inf,
        learner_states=states_inf,
        budget=10,
        deadline_days=2,
        target_node="A",
        current_day=1,
        policy=policy,
    )
    res_inf = replan(state_inf, changed_budget(5))
    assert res_inf["status"] == FeasibilityStatus.INFEASIBLE_PROVED
    expl = res_inf["feasibility_explanation"]
    assert expl["reason_code"] == InfeasibilityReason.BLOCK_EXCEEDS_DAILY_BUDGET
    assert "minimum_fix" in expl
    assert "at least 6 minutes" in expl["minimum_fix"]
    assert check_no_plan_trace(res_inf["trace"])
