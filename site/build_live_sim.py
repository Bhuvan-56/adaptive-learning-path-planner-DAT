"""Records simulated learner sessions for site/sim.html into site/data/live_sim.json.

Each run is site/py/live_session.simulate(): the real engine (CAT diagnostic with catsim,
generate_static_plan, replan, step_difficulty) answered by the project's simulated learner.
Needs the project .venv (catsim).   Usage:  python site/build_live_sim.py
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "site", "py"))

import live_session  # noqa: E402

PRESETS = [  # label, theta*, seed, skip_at_day, target, budget (min/day), horizon (days)
    ("Integrals · strong learner (θ* = 1.2) · 14 days × 45 min", 1.2, 11, None, "INT", 45, 14),
    ("Integrals · average learner, skips 4 days (θ* = 0.3) · 14 days × 45 min", 0.3, 3, 5, "INT", 45, 14),
    ("Integrals · struggling learner (θ* = −0.4) · 14 days × 45 min", -0.4, 5, None, "INT", 45, 14),
    ("Linear functions · average learner (θ* = 0.2) · short, 10 days × 30 min", 0.2, 3, None, "LINF", 30, 10),
]


def main():
    runs = []
    for label, theta, seed, skip, target, budget, horizon in PRESETS:
        out = live_session.simulate(theta, seed=seed, skip_at_day=skip, target=target, budget=budget,
                                    horizon=horizon)
        out["label"] = label
        runs.append(out)
        print(f"{label}: {len(out['frames'])} steps, target ended {out['frames'][-1]['state'].get('target_class')}")
    path = os.path.join(ROOT, "site", "data", "live_sim.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"built": datetime.date.today().isoformat(),
                   "note": "Simulated learners (S0 generator, truth theta* >= b_c); not real learners. "
                           "Questions: data/demo/questions_maths.json (hand-written).",
                   "runs": runs}, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", os.path.relpath(path, ROOT), os.path.getsize(path) // 1024, "KB")


if __name__ == "__main__":
    main()
