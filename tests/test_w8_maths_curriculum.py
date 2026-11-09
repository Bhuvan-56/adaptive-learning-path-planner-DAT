"""W8 website demo curriculum (data/curricula/maths_curriculum.json).

Used only by the live demos and the curriculum page; every evaluation result
uses demo_curriculum.json. These checks keep the demo curriculum valid and
plannable.
"""
from src.curriculum.graph import load_graph, validate_graph
from src.planning.service import plan_request
from src.state.learner_state import ConceptState
from src.state.policy import default_policy
from src.trace.checker import check_trace
from src.trace.universe import get_candidate_universe

MATHS = "data/curricula/maths_curriculum.json"
POLICY, _ = default_policy()


def test_maths_curriculum_is_valid_dag():
    g = load_graph(MATHS)
    assert validate_graph(g) == []
    assert g.number_of_nodes() == 16 and g.number_of_edges() == 20


def test_cold_start_plan_to_integrals_respects_prerequisites_and_budget():
    g = load_graph(MATHS)
    states = {n: ConceptState.cold_start() for n in g.nodes}
    res = plan_request(graph=g, learner_states=states, budget=30, deadline_days=10, targets="INT", policy=POLICY)
    assert res.status == "FEASIBLE"
    universe = get_candidate_universe(g, "INT")
    assert check_trace(universe, res.plan["trace"], num_days=10, budget=30)
    done = set()
    for day in res.plan["days"]:
        assert sum(g.nodes[n]["baseline_duration"] for n in day["activities"]) <= 30
        for n in day["activities"]:
            assert set(g.predecessors(n)) <= done | set(day["activities"]), n
        done |= set(day["activities"])
    assert done == universe


def test_twenty_minute_budget_cannot_fit_calculus():
    g = load_graph(MATHS)
    states = {n: ConceptState.cold_start() for n in g.nodes}
    res = plan_request(graph=g, learner_states=states, budget=20, deadline_days=10, targets="INT", policy=POLICY)
    assert res.status == "INFEASIBLE_PROVED"
