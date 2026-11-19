"""Live demo session: a person answers real questions and the engine diagnoses, plans and replans.

Runs natively (site/serve_live.py, the project .venv); it needs catsim for the diagnostic.
Nothing here re-implements engine logic. The session replays the closed loop that
src/evaluation/integrated.py runs for adaptive_full (one answer per scheduled activity,
step_difficulty, assessment_result -> replan, best-effort plan on an infeasible start),
with the person in place of the simulated learner:

  diagnostic        src/diagnostic/diagnostic.py   AdaptiveDiagnostic.run (CAT, catsim)
  first plan        src/planning/static_baseline.py generate_static_plan
  replanning        src/planning/replan.py          replan + assessment_result / missed_day /
                                                    changed_deadline
  difficulty        src/planning/difficulty.py      step_difficulty
  states, classes   src/state/learner_state.py      ConceptState

Stateless: the page sends the whole answer log and the session is replayed from the start
on every request. Replay is deterministic (CAT selection and estimation, planner, question
choice), so the result equals one uninterrupted run. AdaptiveDiagnostic.run asks for all
its answers through one callback; replay lets a person answer one question at a time
without changing it: the callback raises _NeedAnswer when the log runs out.

Log format: {"diag": [choice, ...], "events": [{"type": "answer", "choice": i} |
                                              {"type": "skip_days", "n": k}, ...]}
choice is the option index the person picked; correctness is decided here.
"""
import json
import os
from typing import Any, Dict, List, Optional

from src.curriculum.graph import load_graph
from src.diagnostic.diagnostic import AdaptiveDiagnostic
from src.planning.difficulty import DifficultyState, step_difficulty
from src.planning.replan import ReplanState, assessment_result, changed_deadline, missed_day, replan
from src.planning.review import ReviewLog, calculate_recall_decay
from src.planning.static_baseline import generate_static_plan
from src.state.policy import default_policy

CURRICULUM = "data/curricula/maths_curriculum.json"
ITEM_BANK = "data/processed/item_bank_synthetic.csv"
QMATRIX = "data/processed/q_matrix_maths.csv"
QUESTIONS = "data/demo/questions_maths.json"
# Defaults (site/live.html); the page may send {"config": {"target", "budget", "horizon"}}.
DEFAULT_TARGET = "LINF"
DEFAULT_BUDGET = 30
DEFAULT_HORIZON = 10


class _NeedAnswer(Exception):
    def __init__(self, item_id: str):
        super().__init__(item_id)
        self.item_id = item_id


def _plain(o: Any) -> Any:
    if hasattr(o, "value") and not isinstance(o, (str, int, float)):
        return o.value
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_plain(v) for v in o]
    return o


def _status(plan: Dict[str, Any]) -> str:
    s = plan.get("status")
    return s.value if hasattr(s, "value") else str(s)


_QCACHE: Dict[str, Any] = {}


def questions() -> Dict[str, Any]:
    if "q" not in _QCACHE:
        with open(QUESTIONS, encoding="utf-8") as f:
            _QCACHE["q"] = json.load(f)
    return _QCACHE["q"]


def _public(q: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Question as shown to the person: no answer key."""
    return {"key": key, "concept": q["concept"], "stem": q["stem"], "options": q["options"]}


def _feedback(q: Dict[str, Any], choice: int) -> Dict[str, Any]:
    ok = int(choice) == int(q["answer"])
    return {"correct": ok, "answer": q["answer"],
            "why": None if ok else q.get("misconceptions", {}).get(str(choice))}


def _practice_question(concept: str, difficulty: float, used: Dict[str, List[str]]) -> Dict[str, Any]:
    """Unused practice question of this concept closest to the current difficulty
    (ties: lower id). When all are used, the cycle starts again."""
    pool = questions()["practice"][concept]
    seen = used.setdefault(concept, [])
    fresh = [q for q in pool if q["id"] not in seen] or pool
    if len(fresh) == len(pool):
        seen.clear()
    q = min(fresh, key=lambda q: (abs(q["difficulty"] - difficulty), q["id"]))
    seen.append(q["id"])
    return q


def _state_view(states, policy) -> Dict[str, Any]:
    return {c: {"p": round(s.p, 4), "n": s.n, "sigma2": round(s.sigma2, 4),
                "class": s.classify(policy), "history": list(s.history)} for c, s in states.items()}


def _trace_view(trace) -> List[Dict[str, Any]]:
    if not isinstance(trace, list):
        return []
    out = []
    for t in trace:
        out.append({"day": t["day"], "node_id": t["node_id"], "decision": _plain(t["decision"]),
                    "reason_code": _plain(t["reason_code"]),
                    "class": t.get("concept_state", {}).get("class"),
                    "p": round(float(t.get("concept_state", {}).get("p", 0.0)), 4),
                    "score_terms": _plain(t.get("score_terms", {}))})
    return out


def _work(plan: Dict[str, Any]):
    """Days and trace that are executed, as in integrated.py (best-effort plan when infeasible)."""
    if "best_effort_days" in plan:
        return plan["best_effort_days"], plan.get("best_effort_trace") or []
    return plan.get("days", []), plan.get("trace")


def _future(plan: Dict[str, Any], after_day: int) -> Dict[int, List[str]]:
    """Activities planned for the days after `after_day` (what a replan can change)."""
    return {d["day"]: list(d.get("activities", [])) for d in _work(plan)[0]
            if d.get("day", 0) > after_day and not d.get("missed")}


def _recalls(answered: List[Dict[str, Any]], day: int) -> Dict[str, float]:
    """Recall R(dt) = 2^(-dt/14) (src/planning/review.py) per concept, from the answers the
    person actually gave. replan() also logs reviews it *plans* as done (review.py,
    "record review attempt so it won't be immediately due"), so the engine's ReviewLog can
    show a planned-but-skipped review as fresh; the page shows real practice only.
    An answer on day d is logged by the engine at time d + 1 (current_day after the answer)."""
    last: Dict[str, float] = {}
    for a in answered:
        last[a["concept"]] = float(a["day"] + 1)
    return {c: round(calculate_recall_decay(float(day) - t), 4) for c, t in last.items()}


def run(log: Dict[str, Any]) -> Dict[str, Any]:
    policy, _ = default_policy()
    g = load_graph(CURRICULUM)
    names = {n: a.get("concept_name", n) for n, a in g.nodes(data=True)}
    qs = questions()
    feed: List[Dict[str, Any]] = []
    cfg = log.get("config") or {}
    TARGET = str(cfg.get("target", DEFAULT_TARGET))
    BUDGET = int(cfg.get("budget", DEFAULT_BUDGET))
    HORIZON = int(cfg.get("horizon", DEFAULT_HORIZON))
    if TARGET not in g or not (10 <= BUDGET <= 120) or not (1 <= HORIZON <= 20):
        raise ValueError(f"bad config {cfg!r}: target must be a curriculum node, budget 10-120, horizon 1-20")
    diag_choices = list(log.get("diag", []))
    events = list(log.get("events", []))

    base = {"target": TARGET, "target_name": names[TARGET], "budget": BUDGET, "horizon": HORIZON,
            "names": names, "edges": [[u, v] for u, v in g.edges()]}

    # ---- 1. Diagnostic (CAT), replayed answer by answer ----------------------------
    asked: List[Dict[str, Any]] = []
    pos = {"i": 0}

    def respond(item_id: str) -> int:
        i = pos["i"]
        if i >= len(diag_choices):
            raise _NeedAnswer(item_id)
        q = qs["diagnostic"][item_id]
        fb = _feedback(q, diag_choices[i])
        asked.append({"item_id": item_id, "concept": q["concept"], "choice": diag_choices[i], **fb})
        pos["i"] += 1
        return 1 if fb["correct"] else 0

    diag = AdaptiveDiagnostic(bank_source=ITEM_BANK, qmatrix_source=QMATRIX, curriculum_source=CURRICULUM)
    try:
        res = diag.run(respond)
    except _NeedAnswer as need:
        return {**base, "phase": "diagnostic", "asked": asked,
                "max_questions": diag.max_questions,
                "question": _public(qs["diagnostic"][need.item_id], need.item_id)}

    states = dict(res.concept_states)
    diag_view = {"theta_hat": round(res.theta_hat, 4), "variance": round(res.variance, 4),
                 "items": asked, "item_counts": res.concept_item_counts,
                 "states": _state_view(states, policy)}

    # ---- 2. First plan (as integrated.py, adaptive arms) -----------------------------
    diff_states = {c: DifficultyState(difficulty=float(g.nodes[c].get("base_difficulty", 0.5))) for c in g.nodes}
    review_log = ReviewLog()
    plan = generate_static_plan(g=g, learner_states=states, budget=BUDGET, deadline_days=HORIZON,
                                target_node=TARGET, policy=policy)
    cur = ReplanState(graph=g, learner_states=dict(states), budget=BUDGET, deadline_days=HORIZON,
                      target_node=TARGET, difficulty_states=dict(diff_states), review_log=review_log,
                      policy=policy)
    if _status(plan) == "INFEASIBLE_PROVED":
        plan = replan(cur, changed_deadline(HORIZON))
        cur.learner_states = plan["learner_states"]
        cur.difficulty_states = plan.get("difficulty_states", diff_states)
        cur.review_log = plan.get("review_log", review_log)
    first_plan = {"status": _status(plan), "days": _plain(_work(plan)[0])}
    feed.append({"kind": "plan", "day": 1, "text": f"First plan built from the diagnostic ({_status(plan)})."})

    # ---- 3. Study days ---------------------------------------------------------------
    completed: set = set()
    past_days: List[Dict[str, Any]] = []
    past_trace: List[Dict[str, Any]] = []
    used: Dict[str, List[str]] = {}
    answered: List[Dict[str, Any]] = []
    ei = 0
    day = 1
    while day <= HORIZON:
        # A skip_days event is honoured only at the start of a day.
        if ei < len(events) and events[ei].get("type") == "skip_days":
            n = max(1, min(int(events[ei].get("n", 1)), HORIZON - day + 1))
            ei += 1
            for _ in range(n):
                cur.current_day = day
                cur.completed_nodes = set(completed)
                cur.difficulty_states = dict(diff_states)
                plan = replan(cur, missed_day())
                cur.learner_states = plan["learner_states"]
                cur.difficulty_states = plan.get("difficulty_states", cur.difficulty_states)
                cur.review_log = plan.get("review_log", cur.review_log)
                _, wt = _work(plan)
                if isinstance(wt, list):
                    past_trace.extend(dict(t) for t in wt if t.get("day") == day)
                past_days.append({"day": day, "activities": [], "missed": True})
                cur.past_days, cur.past_trace = list(past_days), list(past_trace)
                day += 1
            # Re-plan from the first day after the skip, so the plan shown starts there.
            cur.current_day = day
            cur.difficulty_states = dict(diff_states)
            plan = replan(cur, changed_deadline(HORIZON))
            cur.learner_states = plan["learner_states"]
            cur.difficulty_states = plan.get("difficulty_states", cur.difficulty_states)
            cur.review_log = plan.get("review_log", cur.review_log)
            feed.append({"kind": "skip", "day": day, "text": f"Skipped {n} day(s); recall decays and due reviews are re-planned."})
            continue

        work_days, work_trace = _work(plan)
        acts: List[str] = []
        for d in work_days:
            if d.get("day") == day and not d.get("missed"):
                acts = list(d.get("activities", []))
                break
        if isinstance(work_trace, list):
            past_trace.extend(dict(t) for t in work_trace if t.get("day") == day)
        cur.past_trace = list(past_trace)
        today_trace = _trace_view([t for t in work_trace if t.get("day") == day]) if isinstance(work_trace, list) else []

        for k, act in enumerate(acts):
            q = _practice_question(act, diff_states[act].difficulty, used)
            if ei >= len(events) or events[ei].get("type") != "answer":
                return {**base, "phase": "study", "day": day, "activity_index": k, "today": acts,
                        "today_trace": today_trace, "question": _public(q, q["id"]),
                        "difficulty": round(diff_states[act].difficulty, 3),
                        "states": _state_view(cur.learner_states, policy),
                        "plan": {"status": _status(plan), "days": _plain(work_days)},
                        "recall": _recalls(answered, day), "diagnostic": diag_view,
                        "first_plan": first_plan, "answered": answered, "feed": feed,
                        "can_skip": k == 0, "past_days": _plain(past_days),
                        "done_today": acts[:k]}
            choice = events[ei]["choice"]
            ei += 1
            fb = _feedback(q, choice)
            score = 1 if fb["correct"] else 0
            before = cur.learner_states[act].p if act in cur.learner_states else 0.5
            cls_before = cur.learner_states[act].classify(policy) if act in cur.learner_states else "Uncertain"
            old_future = _future(plan, day)
            # As integrated.py: the harness steps its own difficulty state once and hands
            # a copy to replan (which steps its copy again; that copy is not used for items).
            diff_states[act] = step_difficulty(diff_states[act], score)
            completed.add(act)
            cur.completed_nodes = set(completed)
            cur.current_day = day + 1
            cur.difficulty_states = dict(diff_states)
            plan = replan(cur, assessment_result(act, [score]))
            cur.learner_states = plan["learner_states"]
            cur.difficulty_states = plan.get("difficulty_states", cur.difficulty_states)
            cur.review_log = plan.get("review_log", cur.review_log)
            after = cur.learner_states[act]
            answered.append({"day": day, "concept": act, "question": q["id"], "choice": choice, **fb,
                             "p_before": round(before, 4), "p_after": round(after.p, 4),
                             "class_before": cls_before, "class_after": after.classify(policy)})
            changed = _future(plan, day) != old_future
            feed.append({"kind": "answer", "day": day,
                         "text": f"{names[act]}: {'right' if score else 'wrong'}; p {before:.2f} → {after.p:.2f} "
                                 f"({after.classify(policy)}); {'later days re-planned' if changed else 'later days unchanged'} "
                                 f"({_status(plan)})."})
        past_days.append({"day": day, "activities": acts})
        cur.past_days = list(past_days)
        day += 1

    final = {c: s.classify(policy) for c, s in cur.learner_states.items()}
    return {**base, "phase": "done", "states": _state_view(cur.learner_states, policy),
            "diagnostic": diag_view, "first_plan": first_plan, "answered": answered, "feed": feed,
            "days": _plain(past_days), "target_class": final.get(TARGET),
            "trace": _trace_view(past_trace)}


# ---------------------------------------------------------------------------------------
# Automatic simulation (site/sim.html): the same session, answered by the project's
# simulated learner instead of a person. Ground truth follows the evaluation harness:
# latent mastery of concept c is theta* >= b_c (experiments/w8_maths_s0.yaml), diagnostic
# items are answered with the 2PL/4PL probability of the item bank, practice with
# SimulatedLearner + MatchedBKTGenerator (p_S 0.10, p_G 0.25, p_T 0.10), as in S0.
# ---------------------------------------------------------------------------------------
CONCEPT_B = {"ARITH": -0.375, "EXPO": -0.125, "VARS": -0.25, "LIN": 0.0, "INEQ": 0.125, "SYS": 0.375,
             "FUNC": 0.125, "LINF": 0.25, "QUAD": 0.5, "POLY": 0.5, "EXPF": 0.625, "LOG": 0.75,
             "TRIG": 0.625, "LIM": 1.0, "DER": 1.125, "INT": 1.375}  # experiments/w8_maths_s0.yaml


def _slim(st: Dict[str, Any]) -> Dict[str, Any]:
    keep = ("phase", "day", "activity_index", "today", "today_trace", "question", "difficulty", "states",
            "plan", "recall", "feed", "asked", "max_questions", "target_class", "days", "past_days",
            "done_today")
    out = {k: st[k] for k in keep if k in st}
    if "diagnostic" in st:
        d = st["diagnostic"]
        out["diagnostic"] = {"theta_hat": d["theta_hat"], "variance": d["variance"], "n_items": len(d["items"]),
                             "states": d["states"]}
    if "answered" in st:
        out["n_answered"] = len(st["answered"])
    return out


def simulate(theta: float, seed: int = 1, skip_at_day: Optional[int] = None, skip_n: int = 4,
             target: str = DEFAULT_TARGET, budget: int = DEFAULT_BUDGET, horizon: int = DEFAULT_HORIZON,
             max_steps: int = 200) -> Dict[str, Any]:
    import math
    import numpy as np
    import pandas as pd
    from src.simulation.simulator import MatchedBKTGenerator, SimulatedLearner

    g = load_graph(CURRICULUM)
    concepts = list(g.nodes)
    truth0 = {c: bool(theta >= CONCEPT_B[c]) for c in concepts}
    sim = SimulatedLearner(profile_id="profile_1", initial_mastery=truth0, seed=seed, budget_override=budget,
                           curriculum_concepts=concepts,
                           generator_family=MatchedBKTGenerator(p_S=0.10, p_G=0.25, p_T=0.10, p_F=0.0, k=0.0))
    bank = pd.read_csv(ITEM_BANK).set_index("item_id")
    diag_rng = np.random.default_rng([int(seed), 1])
    pick_rng = np.random.default_rng([int(seed), 2])
    qs = questions()

    def choose(q: Dict[str, Any], correct: bool) -> int:
        if correct:
            return int(q["answer"])
        wrong = [i for i in range(len(q["options"])) if i != int(q["answer"])]
        return int(wrong[int(pick_rng.integers(len(wrong)))])

    log: Dict[str, Any] = {"diag": [], "events": [],
                           "config": {"target": target, "budget": budget, "horizon": horizon}}
    frames: List[Dict[str, Any]] = []
    skipped = False
    last_day = 1
    for _ in range(max_steps):
        st = run(log)
        ev = sim.evaluator_view()  # evaluator-only latent truth, shown beside the engine's estimate
        frame = {"state": _slim(st), "truth": {c: ev.get_latent_mastery(c) for c in concepts}}
        if st["phase"] == "done":
            frames.append(frame)
            break
        q = st["question"]
        if st["phase"] == "diagnostic":
            row = bank.loc[q["key"]]
            c_, d_ = float(row.get("c", 0.0)), float(row.get("d", 1.0))
            p = c_ + (d_ - c_) / (1.0 + math.exp(-float(row["a"]) * (theta - float(row["b"]))))
            ok = bool(diag_rng.random() < p)
            ch = choose(qs["diagnostic"][q["key"]], ok)
            log["diag"].append(ch)
            frame["action"] = {"type": "answer", "choice": ch, "correct": ok}
        else:
            if st["day"] > last_day:
                sim.advance_day(st["day"] - last_day)  # p_F = 0: no change, kept for fidelity
                last_day = st["day"]
            if skip_at_day and not skipped and st["day"] >= skip_at_day and st.get("can_skip"):
                skipped = True
                log["events"].append({"type": "skip_days", "n": int(skip_n)})
                frame["action"] = {"type": "skip_days", "n": int(skip_n)}
                frames.append(frame)
                continue
            pq = next(x for x in qs["practice"][q["concept"]] if x["id"] == q["key"])
            ok = bool(sim.respond(concept=q["concept"], difficulty=float(st["difficulty"])))
            ch = choose(pq, ok)
            log["events"].append({"type": "answer", "choice": ch})
            frame["action"] = {"type": "answer", "choice": ch, "correct": ok}
        frames.append(frame)
    return {"learner": {"theta": theta, "seed": seed, "skip_at_day": skip_at_day, "skip_n": skip_n,
                        "truth_rule": "concept known at start iff theta* >= b_c"},
            "target": target, "budget": budget, "horizon": horizon,
            "names": {n: a.get("concept_name", n) for n, a in g.nodes(data=True)},
            "edges": [[u, v] for u, v in g.edges()], "frames": frames}
