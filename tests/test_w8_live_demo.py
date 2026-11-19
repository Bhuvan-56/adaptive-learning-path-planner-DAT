"""W8 demo pages: site/py/live_session.py (site/live.html, site/sim.html) and the demo questions.

The live session replays the adaptive_full loop of src/evaluation/integrated.py with a person
(or the S0 simulated learner) answering. These checks keep the demo from breaking silently:
replay is deterministic, the CAT diagnostic hands over to planning, every scheduled day keeps
the daily budget, skipped days are recorded, and the simulation runs end to end.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site", "py"))

import live_session  # noqa: E402
from src.curriculum.graph import load_graph  # noqa: E402

QUESTIONS = os.path.join(ROOT, "data", "demo", "questions_maths.json")


@pytest.fixture(autouse=True)
def _repo_root(monkeypatch):
    monkeypatch.chdir(ROOT)  # live_session reads repository-relative paths


def _answer_key(st, correct=True):
    qs = live_session.questions()
    key = st["question"]["key"]
    if st["phase"] == "diagnostic":
        q = qs["diagnostic"][key]
    else:
        q = next(x for x in qs["practice"][st["question"]["concept"]] if x["id"] == key)
    return q["answer"] if correct else (q["answer"] + 1) % len(q["options"])


def _play(log, steps, pattern=(True, True, False)):
    """Answer `steps` questions (cycling `pattern` for correctness); returns the last state."""
    st = live_session.run(log)
    for k in range(steps):
        if st["phase"] == "done":
            break
        ch = _answer_key(st, pattern[k % len(pattern)])
        if st["phase"] == "diagnostic":
            log["diag"].append(ch)
        else:
            log["events"].append({"type": "answer", "choice": ch})
        st = live_session.run(log)
    return st


def test_questions_cover_bank_and_curriculum():
    with open(QUESTIONS, encoding="utf-8") as f:
        q = json.load(f)
    qmatrix = {}
    with open("data/processed/q_matrix_maths.csv", encoding="utf-8") as f:
        next(f)
        for line in f:
            item, concept = line.strip().split(",")
            qmatrix[item] = concept
    assert {k: v["concept"] for k, v in q["diagnostic"].items()} == qmatrix
    g = load_graph(live_session.CURRICULUM)
    assert set(q["practice"]) == set(g.nodes)
    for item in list(q["diagnostic"].values()) + [x for lst in q["practice"].values() for x in lst]:
        assert len(item["options"]) == 4 and len(set(item["options"])) == 4
        assert 0 <= item["answer"] < 4
        assert str(item["answer"]) not in item["misconceptions"]
        assert set(item["misconceptions"]) == {str(i) for i in range(4) if i != item["answer"]}


def test_diagnostic_hands_over_to_plan():
    st = live_session.run({"diag": [], "events": []})
    assert st["phase"] == "diagnostic" and st["question"]["key"] in live_session.questions()["diagnostic"]
    assert "answer" not in st["question"]  # the page never sees the key
    st = _play({"diag": [], "events": []}, 12)
    assert st["phase"] == "study"
    assert st["diagnostic"]["items"] and len(st["diagnostic"]["items"]) <= st["diagnostic"].get("max_questions", 10)


def test_replay_is_deterministic():
    log = {"diag": [], "events": []}
    a = _play(log, 18)
    b = live_session.run(json.loads(json.dumps(log)))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_every_planned_day_keeps_the_budget():
    st = _play({"diag": [], "events": []}, 16)
    g = load_graph(live_session.CURRICULUM)
    dur = {n: a["baseline_duration"] for n, a in g.nodes(data=True)}
    days = st.get("plan", {}).get("days", []) + st.get("past_days", st.get("days", []))
    assert days
    for day in days:
        assert sum(dur[c] for c in day.get("activities", [])) <= st["budget"]


def test_skip_days_marks_missed_days():
    log = {"diag": [], "events": []}
    st = live_session.run(log)
    while st["phase"] == "diagnostic":  # answer the diagnostic; the first study day then starts
        log["diag"].append(_answer_key(st))
        st = live_session.run(log)
    assert st["phase"] == "study" and st["activity_index"] == 0 and st["can_skip"]
    day = st["day"]
    log["events"].append({"type": "skip_days", "n": 2})
    st2 = live_session.run(log)
    assert st2["day"] == day + 2
    missed = [d["day"] for d in st2["past_days"] if d.get("missed")]
    assert missed == [day, day + 1]


def test_simulation_runs_end_to_end_and_is_deterministic():
    a = live_session.simulate(0.3, seed=3, skip_at_day=3, target="LINF", budget=30, horizon=10)
    b = live_session.simulate(0.3, seed=3, skip_at_day=3, target="LINF", budget=30, horizon=10)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    frames = a["frames"]
    assert frames[-1]["state"]["phase"] == "done"
    assert any(f.get("action", {}).get("type") == "skip_days" for f in frames)
    assert sum(1 for f in frames if f["state"]["phase"] == "diagnostic") <= 10
    # Truth follows the harness rule theta* >= b_c at the start.
    assert frames[0]["truth"] == {c: 0.3 >= b for c, b in live_session.CONCEPT_B.items()}
