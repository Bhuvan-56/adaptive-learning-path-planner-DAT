# Final Report: Adaptive Learning and Path-Planning Engine

**Team:** Bhuvan Chandra (AI23BTECH11013), Abdur Rehman (AI23BTECH11015) · **Course:** CS5903 Distributed AI Training (DAT) · **Week 8 (final)**

Every number below names the file it comes from. All outcomes are **simulator behaviour on synthetic learners**; no real learner data was used.

---

## 1. Problem

Given a learner's prior knowledge, a target concept, a deadline and a daily study budget, produce a daily plan that:
- respects prerequisites;
- fits the budget;
- adapts as answers arrive;
- explains every decision in a machine-checkable trace.

Scope and actors are in `docs/PROBLEM_BOUNDARY.md`. Not in scope: an LMS front end, content authoring, content generation, and real student telemetry.

## 2. System

| Module | Code | What it does |
|---|---|---|
| M1 Curriculum graph and learner state | `src/curriculum/`, `src/state/` | Validated DAG; BKT mastery `p`, Beta evidence proxy `σ²`; four classes (Uncertain, Mastered, Weak, Developing) |
| M2 Diagnostic | `src/diagnostic/diagnostic.py` | CAT with maximum Fisher information over a 24-item synthetic bank; θ̂ → mastery priors |
| M3 Path planning | `src/planning/static_baseline.py`, `greedy.py`, `greedy_fallback.py`, `oracle.py` | Static topological plan; greedy score-per-minute; best-singleton fallback; exhaustive/DP oracle |
| M4 Difficulty | `src/planning/difficulty.py` | 2-up/1-down staircase |
| M5 Review and remediation | `src/planning/review.py` | HLR recall decay review (recall < 0.85); remediation after 2 consecutive failures |
| M6 Replanning and infeasibility | `src/planning/replan.py`, `feasibility.py` | Event-driven replanning; infeasibility proofs with necessary fixes; practice-for-evidence (W7); best-effort plan (W8) |
| M7 Explainability | `src/trace/` | One trace entry per candidate per day with a reason code; `check_trace` enforces completeness |
| M8 Evaluation | `src/evaluation/`, `src/simulation/` | Closed-loop harness, 9 arms, matched synthetic learners, paired bootstrap |

Design decisions: `decisions/ADR-001` … `ADR-009`. Per-track code walkthroughs: [`ownership_track_A.md`](ownership_track_A.md), [`ownership_track_B.md`](ownership_track_B.md).

## 3. Method

- **Scheduling benchmark:** 250 random instances (5 seeds × 50), each planner's score compared with the oracle's (`experiments/w2_scheduling_benchmark.yaml`).
- **Integrated evaluation:** 5 seeds × 200 synthetic learners = 1,000 paired learners, 5 days, 10-minute budget, target D on the 4-concept demo curriculum.
  - Scenarios: S0 is a matched BKT generator; S1 adds daily forgetting (`p_F = 0.05`) and a 7-day delayed retention quiz.
  - Arms: adaptive_full, static_prerequisite_order, non_adaptive_greedy, non_adaptive_greedy_best_singleton, and five ablations.
- **Claim rule:** an arm is better only if the paired 95% bootstrap CI (B = 1,000) of the difference excludes zero. Otherwise the result is "no difference shown".
- **Hard constraints:** 0 prerequisite violations, 0 budget violations and 100% trace coverage, all recounted independently of the planner.
- **Process:**
  - every change was pre-registered (`docs/w7/preregistration*.md`, `docs/w8/preregistration.md`);
  - tests were written to fail first;
  - before and after evidence is stored under `evaluation/results/*_evidence/`.

## 4. Results

### 4.1 Scheduling (`docs/w7/comparison.md`)

| Policy | Mean ratio to oracle | Instances < 0.95 |
|---|---|---|
| greedy | 0.9737 | 35 / 250 |
| greedy + best-singleton | 0.9814 | 25 / 250 |

Paired difference: **+0.0077 [0.0018, 0.0159]**, so the best-singleton fallback is better. It changed 10 instances and every one now equals the oracle; it lowered none.

### 4.2 Integrated S0 (`evaluation/results/w8/final/integrated_s0/`, identical to `evaluation/results/w7/deadlock_fix/integrated_s0/`)

| Arm | Concepts mastered [95% CI] | No-plan days |
|---|---|---|
| adaptive_full | 2.1760 [2.0800, 2.2680] | 1,000 / 5,000 |
| static_prerequisite_order | 2.0360 [1.9360, 2.1400] | 0 / 5,000 |
| non_adaptive_greedy | 2.0360 [1.9360, 2.1400] | 0 / 5,000 |
| non_adaptive_greedy_best_singleton | 2.0490 [1.9510, 2.1510] | 0 / 5,000 |

- adaptive_full − static: **+0.1400 [0.1110, 0.1690]**, adaptive better. Before the Week 7 deadlock fix this was −0.1020 and static was better.
- best-singleton − greedy: +0.0130 [0.0040, 0.0230]. This passes only with all five seeds pooled; every seed alone shows no difference.

### 4.3 Integrated S1, forgetting during study (`docs/w8/results.md`)

| Arm | Concepts mastered [95% CI] | Retained recall |
|---|---|---|
| adaptive_full | 1.7300 [1.6490, 1.8190] | 0.5542 |
| static_prerequisite_order | 1.5870 [1.5010, 1.6740] | 0.5159 |
| non_adaptive_greedy | 1.5940 [1.5050, 1.6820] | 0.5180 |

- adaptive_full − static: **+0.1430 [0.1000, 0.1830]** concepts and **+0.0383 [0.0279, 0.0481]** retained recall, adaptive better on both.
- best-singleton − greedy: −0.0040 [−0.0190, 0.0130], no difference shown.
- Forgetting costs every arm about 0.45 concepts compared with the pre-fix S1 run, which had no forgetting during study.

### 4.4 Robustness: larger curriculum and mismatched simulator (`docs/w8/results_maths.md`)

A pre-registered 2 × 2 check: toy (4 concepts) or maths (16 concepts, target Integrals, 10 days × 30 min), each with the matched BKT simulator (S0) or a mismatched PFA simulator (S3), where learning comes from practice counts. Paired adaptive_full − static_prerequisite_order, concepts mastered:

| | S0 (matched) | S3 (mismatched) |
|---|---|---|
| Toy, 4 concepts | +0.1400 [0.1110, 0.1690] | +0.3540 [0.2990, 0.4100] |
| Maths, 16 concepts | +0.2140 [0.1600, 0.2680] | +0.8110 [0.6980, 0.9170] |

- **Adaptive is better than both baselines in every cell,** on mastery and on retained recall.
- **Caveat:** S3 rewards practice attempts directly, which favours the adaptive arm's extra practice. "Survives a mismatched simulator" is supported; "larger with real learners" is not.
- **Ablations:** they still cannot credit single components. One reason is new: the diagnostic gives priors with n = 0, which the classifier always labels Uncertain, so the CAT result can never change a plan (`LIMITATIONS.md` B10).

### 4.5 Hard constraints

0 prerequisite violations, 0 budget violations and 100% trace coverage in every arm of every final run, including the maths and S3 runs.

## 5. What changed over the project

| Week | Outcome |
|---|---|
| W3 | Correctness repairs (10 defects with before/after evidence); OSS pyBKT slice; frozen acceptance and evaluation protocol |
| W4 | Difficulty, review/remediation, observed-event replanning; horizontal slice (`evaluation/results/w4/slice/`) |
| W5 | Integrated M1–M8 evaluation against both baselines; failed acceptance groups fixed |
| W6 | Beta: clean-run audit, multi-seed fix, S1/S2 configs, retention quiz, ownership packs |
| W7 | Best-singleton fallback (measured improvement); project website; adaptive deadlock fix (adaptive went from worse than static to better) |
| W8 | S1 daily forgetting fixed; best-effort plan instead of idling on infeasible days; final runs, limitations, report, code walkthroughs |

## 6. Limitations

See [`LIMITATIONS.md`](LIMITATIONS.md). The most important:
- **synthetic learners only.** The main results use a generator that matches the planner's own model; the mismatched check (§4.4) has its own bias.
- **two hand-made curricula** (4 and 16 concepts), neither from real data.
- **no single component can be credited:**
  - the replan ablations are identical to adaptive_full;
  - the diagnostic cannot change a plan by design (n = 0 priors are always Uncertain);
  - the remediation ablation never disables remediation;
  - remediation never fires in the closed loop.
- **prerequisite importance,** named in the problem statement, is stored but not used.

## 7. Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q
python -m src.evaluation.integrated --config experiments/w8_final.yaml --out out/s0
python -m src.evaluation.integrated --config experiments/w8_final_s1.yaml --out out/s1
python scripts/w7_pooled_s0.py out/s1 adaptive_full:static_prerequisite_order
python scripts/w8_s1_compare.py evaluation/results/w8/before/integrated_s1 out/s1
```

Compare the per-learner CSVs with `evaluation/results/w8/final/` on all columns except `runtime_ms`. The clean-clone audit is `scripts/clean_run.ps1`. The demo walkthrough is in [`DEMO.md`](DEMO.md).
