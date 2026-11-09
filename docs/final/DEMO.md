# Final Demo Script (about 12 minutes)

Website: <https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/> (or run it locally: `python -m http.server 8000` from the repository root, then open <http://localhost:8000/site/>). The live demos run the real `src/` code in the browser. Without internet they show saved outputs of every preset (`site/data/fallback.json`).

Before the demo: open the site once with internet so Pyodide (about 10 MB) is cached. Keep a terminal open in the repository with the venv active.

## 1. Problem and system (2 min): `index.html`, `curriculum.html`

- The task: target concept, deadline, daily budget → a day-by-day plan that respects prerequisites, adapts to answers and explains itself.
- The curriculum page opens on the 16-concept **Mathematics** curriculum (fractions to integrals, 10–25 minute topics). Click **QUAD** to show everything it requires (4 prerequisites, 65 minutes from scratch), then **Plan QUAD in the live demo**.
- Switch to **Toy** to show the 4-concept curriculum (A → B, A → C, B → D, C → D) that every evaluation result uses.
- The modules M1–M8 are summarised in `docs/final/FINAL_REPORT.md` §2.

## 2. Planning live (4 min): `demos.html`, demo B, Mathematics curriculum

Each plan is drawn on the curriculum graph, with each concept shaded by the day it is first scheduled.

1. **Cold start → Integrals** (30 min/day, 10 days): 12 concepts over 8 days. Concepts not needed for Integrals (logarithms, trigonometry, inequalities, systems) are faded. Point at a conditional item (`*`) and open the trace: every concept on every day has a reason code.
2. **Algebra already mastered**: the same target with 5 algebra concepts mastered; the plan skips them and finishes 2 days sooner.
3. **Budget 20 (calculus won't fit)**: Derivatives and Integrals are 25-minute topics, so a 20-minute budget is proved infeasible (`BLOCK_EXCEEDS_DAILY_BUDGET`) with the minimum fix.
4. **Studied twice, still unproven** (replan): `PRACTICE_FOR_EVIDENCE`, the Week 7 deadlock fix. A concept studied but still Uncertain gets more practice instead of blocking everything.
5. **Quadratics failed twice** (replan): two wrong answers on QUAD trigger **remediation** of its unmastered prerequisite (Exponents) before anything else (`REMEDIATION_TRIGGERED`).
6. **Missed day (review comes due)** (replan): the day is recorded as missed, the rest is replanned, and a mastered concept comes back as a **spaced review** (`REVIEW_DUE`).
7. **Deadline cut to 4 days** (replan, Week 8): `INFEASIBLE_PROVED / CAPACITY_EXCEEDED` with the necessary fixes, plus a **best-effort plan** of the work that still fits. The learner keeps working instead of idling.

The **Toy** presets show the same behaviours on 4 concepts. The 4-concept curriculum is the one behind every number in section 4.

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
- Track A, Bhuvan (planning, state, diagnostic, traces): [`ownership_track_A.md`](ownership_track_A.md). Change task: cap practice blocks per day.
- Track B, Abdur (evaluation, simulator, retention): [`ownership_track_B.md`](ownership_track_B.md). Change task: make `ablation_no_remediation` real.
