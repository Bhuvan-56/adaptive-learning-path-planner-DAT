"""Thin JSON adapter between the website demos and the project code.

Runs unchanged in two places:
  * in the browser under Pyodide (site/assets/pyrunner.js copies src/ into the
    Pyodide file system and imports this module), and
  * natively, from site/build_data.py, to save the static fallback outputs.

Nothing here re-implements planning logic. Every score, pick, plan, trace
entry and reason code comes from functions in src/:
  run_greedy_scheduler        src/planning/greedy.py
  run_greedy_best_singleton   src/planning/greedy_fallback.py
  best_singleton_fallback     src/planning/greedy_fallback.py
  run_exhaustive_oracle       src/planning/oracle.py
  plan_request                src/planning/service.py (-> generate_static_plan)
  replan + event factories    src/planning/replan.py
  ConceptState                src/state/learner_state.py
"""
import json
from enum import Enum
from typing import Any, Dict, List

import networkx as nx

import src.planning.greedy as greedy_mod
from src.curriculum.graph import load_graph
from src.planning.greedy import run_greedy_scheduler
from src.planning.greedy_fallback import best_singleton_fallback, run_greedy_best_singleton
from src.planning.oracle import run_exhaustive_oracle
from src.planning.replan import (
    ReplanState,
    assessment_result,
    changed_budget,
    changed_deadline,
    missed_day,
    replan,
)
from src.planning.service import plan_request
from src.state.learner_state import ConceptState
from src.state.policy import default_policy

CURRICULUM_PATH = "data/curricula/demo_curriculum.json"  # the 4-concept toy curriculum used by every evaluation
# Demo B can plan on either curriculum; "maths" is the 16-concept website demo curriculum (Week 8).
CURRICULA = {
    "toy": CURRICULUM_PATH,
    "maths": "data/curricula/maths_curriculum.json",
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _plain(obj: Any) -> Any:
    """Make planner output JSON-safe (enums -> value, sets -> sorted lists)."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(_plain(v) for v in obj)
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


def _clean_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for it in items:
        out.append({
            "node_id": str(it["node_id"]),
            "duration": int(it["duration"]),
            "score": float(it["score"]),
            "prerequisites": [str(p) for p in it.get("prerequisites", []) if str(p)],
        })
    return out


# --------------------------------------------------------------------------
# Demo A: greedy vs greedy + best-singleton vs exact oracle
# --------------------------------------------------------------------------
def _greedy_picks(items: List[Dict[str, Any]], budget: int) -> List[str]:
    """Pick order of run_greedy_scheduler, observed (not recomputed).

    run_greedy_scheduler only returns a score. To show which items it took, we
    wrap the is_admissible it calls and record the selected_set it passes in;
    each time the set grows, the new member is greedy's next pick. The wrapper
    returns is_admissible's own answer, so greedy's behaviour is unchanged.
    """
    real = greedy_mod.is_admissible
    order: List[str] = []

    def spy(activity, selected_set, *args, **kwargs):
        for nid in sorted(selected_set):
            if nid not in order:
                order.append(nid)
        return real(activity, selected_set, *args, **kwargs)

    greedy_mod.is_admissible = spy
    try:
        score = run_greedy_scheduler(items, budget)
    finally:
        greedy_mod.is_admissible = real
    # After each pick greedy re-checks every unselected item, so the pick shows
    # up in the next call. The one exception: greedy took every item, so no
    # call follows the last pick. Then the single unseen item is still
    # admissible after the recorded picks (greedy stops only when none is).
    by_id = {it["node_id"]: it["score"] for it in items}
    rest = [it for it in items if it["node_id"] not in order]
    used = sum(it["duration"] for it in items if it["node_id"] in order)
    if len(rest) == 1 and real(rest[0], set(order), set(), budget - used):
        order.append(rest[0]["node_id"])
    assert round(sum(by_id[n] for n in order)) == score, "greedy pick trace disagrees with greedy score"
    return order


def _oracle_picks(items: List[Dict[str, Any]], budget: int, best: int) -> List[str]:
    """One optimal selection, found only by calling run_exhaustive_oracle.

    Self-reduction: drop each item in turn and keep it dropped if the oracle
    optimum on the remaining items is unchanged. Every item that survives is
    needed by every optimal selection of the survivors, so the survivors are an
    optimal selection. (Dropping an item also blocks items that need it as a
    prerequisite, exactly as in the oracle.)
    """
    keep = list(items)
    for it in list(items):
        trial = [x for x in keep if x["node_id"] != it["node_id"]]
        if run_exhaustive_oracle(trial, budget) == best:
            keep = trial
    return [x["node_id"] for x in keep]


def scheduler_compare(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = _clean_items(payload["items"])
    budget = int(payload["budget"])
    ids = [it["node_id"] for it in items]
    if len(set(ids)) != len(ids):
        return {"ok": False, "error": "Item ids must be unique."}
    unknown = sorted({p for it in items for p in it["prerequisites"] if p not in ids})
    if unknown:
        return {"ok": False, "error": f"Unknown prerequisite id(s): {', '.join(unknown)}"}
    if budget < 0:
        return {"ok": False, "error": "Budget must be zero or more."}

    g_score = run_greedy_scheduler(items, budget)
    g_picks = _greedy_picks(items, budget)
    bs_score = run_greedy_best_singleton(items, budget)
    bs_picks = best_singleton_fallback(g_picks, items, budget)

    result: Dict[str, Any] = {
        "ok": True,
        "budget": budget,
        "greedy": {"score": g_score, "picks": g_picks},
        "best_singleton": {"score": int(round(bs_score)), "picks": bs_picks},
    }
    try:
        o_score = run_exhaustive_oracle(items, budget)
        result["oracle"] = {"score": o_score, "picks": _oracle_picks(items, budget, o_score)}
    except (ValueError, TimeoutError) as exc:
        result["oracle"] = {"error": str(exc)}
    dur = {it["node_id"]: it["duration"] for it in items}
    for key in ("greedy", "best_singleton", "oracle"):
        r = result[key]
        if "picks" in r:
            r["minutes"] = sum(dur[n] for n in r["picks"])
    return result


# --------------------------------------------------------------------------
# Demo B: plan builder (plan_request) and one replan event (replan)
# --------------------------------------------------------------------------
def _graph(key: str = "toy") -> nx.DiGraph:
    if key not in CURRICULA:
        raise ValueError(f"Unknown curriculum {key!r}; expected one of {sorted(CURRICULA)}")
    return load_graph(CURRICULA[key])


def curriculum(key: str = "toy") -> Dict[str, Any]:
    g = _graph(key)
    return {
        "key": key,
        "path": CURRICULA[key],
        "nodes": [
            {"id": n, "name": a.get("concept_name"), "minutes": a.get("baseline_duration")}
            for n, a in g.nodes(data=True)
        ],
        "edges": [[u, v] for u, v in g.edges()],
    }


def _state_from_answers(answers: str) -> ConceptState:
    """Cold start, then one ConceptState.update per answer ('1' right, '0' wrong)."""
    policy, _ = default_policy()
    st = ConceptState.cold_start()
    for ch in answers:
        if ch in "01":
            st.update(int(ch), policy=policy)
    return st


def _state_view(st: ConceptState) -> Dict[str, Any]:
    policy, _ = default_policy()
    return {
        "p": round(st.p, 4),
        "n": st.n,
        "sigma2": round(st.sigma2, 4),
        "class": st.classify(policy),
        "history": list(st.history),
    }


def concept_state(answers: str) -> Dict[str, Any]:
    return _state_view(_state_from_answers(answers))


def _trace_view(trace: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "day": t["day"],
            "node_id": t["node_id"],
            "decision": t["decision"],
            "reason_code": _plain(t["reason_code"]),
            "class": t["concept_state"].get("class"),
            "remaining_budget": t["constraints"].get("remaining_budget"),
        }
        for t in trace
    ]


def _plan_view(raw: Dict[str, Any]) -> Dict[str, Any]:
    trace = raw.get("trace")
    view = {
        "status": _plain(raw.get("status")),
        "feasibility": _plain(raw.get("feasibility_explanation", {})),
        "days": _plain(raw.get("days", [])),
        "assessment_candidates": _plain(raw.get("assessment_candidates", [])),
    }
    if isinstance(trace, list):
        view["trace"] = _trace_view(trace)
    else:
        view["no_plan_trace"] = _plain(trace)
    # Week 8: a capacity-infeasible replan also carries the work that still fits.
    if "best_effort_days" in raw:
        view["best_effort_days"] = _plain(raw["best_effort_days"])
        view["best_effort_trace"] = _trace_view(raw.get("best_effort_trace") or [])
    return view


def build_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    g = _graph(payload.get("curriculum", "toy"))
    answers = payload.get("answers", {})
    states = {n: _state_from_answers(answers.get(n, "")) for n in g.nodes}
    policy, _ = default_policy()
    res = plan_request(
        graph=g,
        learner_states=states,
        budget=int(payload["budget"]),
        deadline_days=int(payload["deadline_days"]),
        targets=payload["target"],
        policy=policy,
    )
    out: Dict[str, Any] = {
        "is_valid": res.is_valid,
        "status": res.status,
        "error_codes": list(res.error_codes),
        "message": res.message,
        "states": {n: _state_view(s) for n, s in states.items()},
    }
    if res.plan is not None:
        out["plan"] = _plan_view(res.plan)
    event = payload.get("event")
    if event and res.is_valid:
        out["replan"] = _replan(g, states, payload, policy, event)
    return out


def _replan(g, states, payload, policy, event) -> Dict[str, Any]:
    kind = event.get("type")
    if kind == "assessment_result":
        ev = assessment_result(event["node"], [int(c) for c in str(event.get("answers", "")) if c in "01"])
    elif kind == "missed_day":
        ev = missed_day()
    elif kind == "changed_budget":
        ev = changed_budget(int(event["value"]))
    elif kind == "changed_deadline":
        ev = changed_deadline(int(event["value"]))
    else:
        return {"error": f"Unknown event {kind}"}
    state = ReplanState(
        graph=g,
        learner_states={n: _state_from_answers(payload.get("answers", {}).get(n, "")) for n in g.nodes},
        budget=int(payload["budget"]),
        deadline_days=int(payload["deadline_days"]),
        target_node=payload["target"],
        completed_nodes=set(payload.get("studied", [])),
        policy=policy,
    )
    raw = replan(state, ev)
    view = _plan_view(raw)
    view["event"] = event
    view["states"] = {n: _state_view(s) for n, s in raw.get("learner_states", {}).items()}
    return view


# --------------------------------------------------------------------------
# JSON entry point used from JavaScript
# --------------------------------------------------------------------------
def call(name: str, payload_json: str) -> str:
    payload = json.loads(payload_json) if payload_json else {}
    fn = {
        "scheduler_compare": scheduler_compare,
        "build_plan": build_plan,
        "concept_state": lambda p: concept_state(p.get("answers", "")),
        "curriculum": lambda p: curriculum(p.get("curriculum", "toy")),
    }[name]
    try:
        return json.dumps(fn(payload))
    except Exception as exc:  # surfaced in the page instead of a silent failure
        return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
