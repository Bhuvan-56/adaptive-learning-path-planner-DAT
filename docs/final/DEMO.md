# Final Demo Script (about 12 minutes)

Website: <https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/> (or run it locally: `python -m http.server 8000` from the repository root, then open <http://localhost:8000/site/>). The live demos run the real `src/` code in the browser. Without internet they show saved outputs of every preset (`site/data/fallback.json`).

Before the demo: open the site once with internet so Pyodide (about 10 MB) is cached. Keep a terminal open in the repository with the venv active.

## 1. Problem and system (2 min): `index.html`, `curriculum.html`

- The task: target concept, deadline, daily budget → a day-by-day plan that respects prerequisites, adapts to answers and explains itself.
- The curriculum page shows the 4-concept graph: A → B, A → C, B → D, C → D, with durations of 5, 5, 10 and 10 minutes.
- The modules M1–M8 are summarised in `docs/final/FINAL_REPORT.md` §2.

## 2. Planning live (4 min): `demos.html`, demo B

1. **Cold start**: the plan for D with every concept Uncertain. Point at a conditional item (`*`) and open the trace: every concept on every day has a reason code.
2. **B weak**: B is planned on day 1, and its dependent D only on a later day (conditional).
3. **Replan: A, B studied once**: `PRACTICE_FOR_EVIDENCE`, the Week 7 deadlock fix. A concept studied once but still Uncertain gets more practice instead of blocking everything.
4. **2 days (infeasible)**: `INFEASIBLE_PROVED / CAPACITY_EXCEEDED`, with the necessary fixes (extend by N days or add N minutes).
5. **Replan: deadline cut to 2 days** (Week 8): the same infeasibility report, plus a **best-effort plan**: B on day 1, C on day 2. The learner keeps working instead of idling.
6. **Budget 8 (infeasible)**: a single block (10 min) is longer than the budget. This is proved infeasible and there is no best-effort plan, because that block can never run.

## 3. Scheduling (1 min): `demos.html` demo A, `scheduling.html`

- **12/18 counterexample:** greedy 12, oracle 18. The best-singleton fallback does not help here.
- **Seed 47, instance 215:** greedy 3, fallback 14, oracle 14.
- **Benchmark:** the fallback is better by +0.0077 [0.0018, 0.0159] in ratio to the oracle, over 250 instances.

## 4. Results (3 min): `results.html`

- **S0:** adaptive_full 2.1760 against static 2.0360, +0.1400 [0.1110, 0.1690]. Before the Week 7 fix the adaptive arm was worse.
- **S1 (Week 8), forgetting during study:** every arm loses about 0.45 concepts. Adaptive is still better: +0.1430 [0.1000, 0.1830] concepts and +0.0383 [0.0279, 0.0481] retained recall. The best-singleton gain disappears.
- **Hard constraints:** 0 prerequisite violations, 0 budget violations, 100% trace coverage, in every arm.

## 5. Limitations (1 min): `docs/final/LIMITATIONS.md`

- The learners are synthetic, and the generator matches the planner's own model.
- The curriculum has only 4 concepts.
- The ablations are identical to adaptive_full, so no component is credited alone. The remediation ablation is a known harness bug.

## 6. Reproduce a number (1 min, terminal)

```bash
python -m pytest -q tests/test_w8_best_effort.py tests/test_w7_b1_s1_forgetting.py
python scripts/w8_s1_compare.py evaluation/results/w8/before/integrated_s1 evaluation/results/w8/final/integrated_s1
```

The second command prints the S1 before/after table from the committed per-learner files.

## Code explanation and change tasks

Each member explains one track and makes one live change:
- Track A (planning, state, diagnostic, traces): [`ownership_track_A.md`](ownership_track_A.md). Change task: cap practice blocks per day.
- Track B (evaluation, simulator, retention): [`ownership_track_B.md`](ownership_track_B.md). Change task: make `ablation_no_remediation` real.
