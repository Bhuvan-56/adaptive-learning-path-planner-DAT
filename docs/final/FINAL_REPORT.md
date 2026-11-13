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
  - Scenarios: S0 is a matched BKT generator; S1 adds daily forgetting (`p_F = 0.05`) and a 7-day delayed retention quiz; S3 is a mismatched PFA generator. A 16-concept maths curriculum (10 days × 30 min) is run under S0 and S3.
  - Arms: adaptive_full, static_prerequisite_order, non_adaptive_greedy, non_adaptive_greedy_best_singleton, and five ablations.
- **Claim rule:** an arm is better only if the paired 95% bootstrap CI (B = 1,000) of the difference excludes zero. Otherwise the result is "no difference shown".
- **Hard constraints:** 0 prerequisite violations, 0 budget violations and 100% trace coverage, all recounted independently of the planner. A prerequisite counts as met if it was studied or was evidence-Mastered before day 1 (the planner's own rule; Week 8 B10 fix).
- **Calibration:** at the end of the horizon, the engine's p per concept is scored against the simulator's latent mastery (Brier, 10-bin ECE) for the arms that update p.
- **Process:**
  - every change up to Week 8 addendum 2 was pre-registered (`docs/w7/preregistration*.md`, `docs/w8/preregistration*.md`); the final fixes (B10, B11, M2 comparison, calibration) were not;
  - tests were written to fail first;
  - before and after evidence is stored under `evaluation/results/*_evidence/`.

## 4. Results

### 4.1 Scheduling (`docs/w7/comparison.md`)

| Policy | Mean ratio to oracle | Instances < 0.95 |
|---|---|---|
| greedy | 0.9737 | 35 / 250 |
| greedy + best-singleton | 0.9814 | 25 / 250 |

Paired difference: **+0.0077 [0.0018, 0.0159]**, so the best-singleton fallback is better. It changed 10 instances and every one now equals the oracle; it lowered none.

All integrated results below are the **final runs after every Week 8 fix** (`evaluation/results/w8/final_v2/`, five seeds × 200 learners, pooled with `scripts/w7_pooled_s0.py`). The earlier Week 8 runs (`evaluation/results/w8/final/`, `evaluation/results/w8/maths_eval/`) are kept unchanged; `evaluation/results/w8/final_v2/before_after.txt` compares the two.

### 4.2 Integrated S0 (`evaluation/results/w8/final_v2/integrated_s0/`, `evaluation/results/w8/final_v2/pooled_integrated_s0.txt`)

| Arm | Concepts mastered [95% CI] | Retained recall | No-plan days |
|---|---|---|---|
| adaptive_full | 2.0920 [1.9940, 2.1900] | 0.6604 | 623 / 5,000 |
| static_prerequisite_order | 2.0360 [1.9360, 2.1400] | 0.6362 | 0 / 5,000 |
| non_adaptive_greedy | 2.0360 [1.9360, 2.1400] | 0.6362 | 0 / 5,000 |
| non_adaptive_greedy_best_singleton | 2.0490 [1.9510, 2.1510] | 0.6382 | 0 / 5,000 |
| ablation_no_diagnostic | 2.1760 [2.0800, 2.2680] | 0.6985 | 1,000 / 5,000 |

- adaptive_full − static (and − greedy, identical here): **+0.0560 [0.0400, 0.0740]** concepts and +0.0242 [0.0168, 0.0316] retained recall, adaptive better. In the earlier Week 8 run this was +0.1400 [0.1110, 0.1690]; before the Week 7 deadlock fix it was −0.1020.
- adaptive_full − ablation_no_diagnostic: **−0.0840 [−0.1110, −0.0580]**: since the diagnostic can change plans (B10 fix), the cold-start ablation is better than adaptive_full (§4.6).
- best-singleton − greedy: +0.0130 [0.0040, 0.0230] (baselines unchanged). This passes only with all five seeds pooled; every seed alone shows no difference.

### 4.3 Integrated S1, forgetting during study (`evaluation/results/w8/final_v2/integrated_s1/`, `evaluation/results/w8/final_v2/pooled_integrated_s1.txt`)

| Arm | Concepts mastered [95% CI] | Retained recall |
|---|---|---|
| adaptive_full | 1.6320 [1.5460, 1.7150] | 0.5309 |
| static_prerequisite_order | 1.5870 [1.5010, 1.6740] | 0.5159 |
| non_adaptive_greedy | 1.5940 [1.5050, 1.6820] | 0.5180 |

- adaptive_full − static: **+0.0450 [0.0220, 0.0640]** concepts and **+0.0150 [0.0072, 0.0236]** retained recall, adaptive better on both.
- adaptive_full − greedy: +0.0380 [0.0000, 0.0750] concepts, **no difference shown** (it was +0.1360 [0.0860, 0.1830] in the earlier Week 8 run); retained recall +0.0129 [0.0032, 0.0231], adaptive better (`evaluation/results/w8/final_v2/before_after.txt`).
- best-singleton − greedy: −0.0040 [−0.0190, 0.0130], no difference shown.
- Forgetting costs every arm compared with the pre-fix S1 run, which had no forgetting during study (`docs/w8/results.md` §3).

### 4.4 Robustness: larger curriculum and mismatched simulator (`evaluation/results/w8/final_v2/before_after.txt`)

The pre-registered 2 × 2 check (`docs/w8/preregistration_maths.md`): toy (4 concepts) or maths (16 concepts, target Integrals, 10 days × 30 min), each with the matched BKT simulator (S0) or a mismatched PFA simulator (S3), where learning comes from practice counts. Paired differences in concepts mastered, final_v2:

| | adaptive − static, S0 | adaptive − static, S3 | adaptive − greedy, S0 | adaptive − greedy, S3 |
|---|---|---|---|---|
| Toy, 4 concepts | +0.0560 [0.0400, 0.0740] | +0.1170 [0.0960, 0.1390] | +0.0560 [0.0400, 0.0740] | +0.1170 [0.0960, 0.1390] |
| Maths, 16 concepts | +0.0940 [0.0470, 0.1400] | +0.7270 [0.6310, 0.8240] | +0.0110 [−0.0310, 0.0590] | +0.4050 [0.3100, 0.5000] |

- **Adaptive is better than static in every cell,** on mastery and on retained recall.
- **Against greedy** it is better in three cells; on the maths curriculum under S0 the mastery difference shows **no difference** (it was +0.1310 [0.0840, 0.1810] before the B10 fix). Retained recall still favours adaptive there, +0.0811 [0.0741, 0.0889].
- **Caveat:** S3 rewards practice attempts directly, which favours the adaptive arm's extra practice. "Survives a mismatched simulator" is supported; "larger with real learners" is not.
- **Ablations:** ablation_no_diagnostic is better than adaptive_full on mastery in all five final runs (§4.6). The difficulty, review and remediation ablations show no difference on mastery in any of the four cells.

### 4.5 Hard constraints (`evaluation/results/w8/final_v2/before_after.txt`)

0 prerequisite violations and 0 budget violations in every arm of every final_v2 run, recounted independently. Trace coverage is 100% for the four primary arms in every run (`summary_seed_<s>.md`); the harness does not write coverage for ablation arms.

### 4.6 Diagnostic (M2)

**CAT vs fixed vs random** (`evaluation/results/w8/diagnostic_comparison/summary.md`; `experiments/w4_comparison.yaml`, 5 seeds × 200 learners, paired, B = 1,000; lower is better):

| adaptive − X | \|θ̂ − θ*\| error | Concept Brier | Held-out log loss |
|---|---|---|---|
| fixed | −0.0643 [−0.0921, −0.0375], adaptive better | −0.0030 [−0.0067, +0.0008], no difference shown | −0.0090 [−0.0158, −0.0026], adaptive better |
| random | −0.0823 [−0.1103, −0.0560], adaptive better | −0.0057 [−0.0096, −0.0017], adaptive better | −0.0155 [−0.0237, −0.0082], adaptive better |

The gains are small (for example about 0.009 on a log loss of about 0.55).

**Diagnostic evidence in the plan (B10 fix).** A concept probed by k answered items now starts with n = k, κ = 2 + k and its answers as history (ADR-009 Week 8 amendment). The diagnostic now changes plans, but on the planning outcome it **hurts**: ablation_no_diagnostic (cold start) beats adaptive_full on mastery in every final run, from −0.0840 [−0.1380, −0.0300] (maths S3) to −0.2370 [−0.2890, −0.1870] (toy S3) (`evaluation/results/w8/final_v2/before_after.txt`). Observed: one θ̂ sets the same p for every probed concept, an all-correct diagnostic stops at θ̂ ≈ 1.13 (p ≈ 0.76 < 0.85), so most probed concepts start Developing or Weak rather than Mastered (`evaluation/results/w8_evidence/after_fix3_diagnostic_prior.txt`); adaptive_full's no-plan days also fell (toy S0 1,000 → 623 of 5,000). Why this lowers mastery was **not tested**; a plausible but unverified factor is that concepts no longer Uncertain lose the practice-for-evidence sessions added in Week 7.

### 4.7 Mastery calibration (M8) (`evaluation/results/w8/final_v2/pooled_<run>.txt`)

Engine p per concept at the end of the horizon against the simulator's latent mastery, read only by the evaluator. Brier is the per-learner mean over concepts (mean [95% CI] over 1,000 learners); ECE pools all learner × concept pairs, 10 bins.

| Run | adaptive_full Brier / ECE | ablation_no_diagnostic Brier / ECE |
|---|---|---|
| Toy S0 | 0.1358 [0.1288, 0.1429] / 0.0821 | 0.1462 [0.1401, 0.1526] / 0.0641 |
| Toy S1 | 0.1955 [0.1873, 0.2033] / 0.1625 | 0.1890 [0.1817, 0.1959] / 0.1453 |
| Toy S3 | 0.1667 [0.1581, 0.1760] / 0.0888 | 0.1416 [0.1346, 0.1481] / 0.0791 |
| Maths S0 | 0.1897 [0.1865, 0.1928] / 0.1657 | 0.1872 [0.1842, 0.1903] / 0.1407 |
| Maths S3 | 0.1881 [0.1846, 0.1918] / 0.1550 | 0.1914 [0.1877, 0.1950] / 0.1563 |

The static and greedy arms never update p after the diagnostic, so calibration is **not applicable** to them. Calibration is worse under forgetting (S1) and on the 16-concept curriculum. Concepts never practised keep p = 0.5 (cold start), which is the largest miscalibrated bin on the toy curriculum (`evaluation/results/w8/calibration_s0/summary.md`, 0.5–0.6 bin).

## 5. What changed over the project

| Week | Outcome |
|---|---|
| W3 | Correctness repairs (10 defects with before/after evidence); OSS pyBKT slice; frozen acceptance and evaluation protocol |
| W4 | Difficulty, review/remediation, observed-event replanning; horizontal slice (`evaluation/results/w4/slice/`) |
| W5 | Integrated M1–M8 evaluation against both baselines; failed acceptance groups fixed |
| W6 | Beta: clean-run audit, multi-seed fix, S1/S2 configs, retention quiz, ownership packs |
| W7 | Best-singleton fallback (measured improvement); project website; adaptive deadlock fix (adaptive went from worse than static to better) |
| W8 | S1 daily forgetting fixed; best-effort plan instead of idling on infeasible days; final runs, limitations, report, code walkthroughs. Final fixes: diagnostic answers count as evidence (B10); review ordered by forgetting risk × prerequisite importance (B11); pooled CAT vs fixed vs random comparison with paired CIs (M2); end-of-horizon mastery calibration, Brier and ECE (M8); all integrated runs re-made (`evaluation/results/w8/final_v2/`) |

## 6. Limitations

See [`LIMITATIONS.md`](LIMITATIONS.md). The most important:
- **synthetic learners only.** The main results use a generator that matches the planner's own model; the mismatched check (§4.4) has its own bias.
- **two hand-made curricula** (4 and 16 concepts), neither from real data.
- **no single component can be credited positively:**
  - the diagnostic now changes plans, but the cold-start ablation is better than adaptive_full (§4.6);
  - the difficulty and remediation ablations show no difference on mastery; the review ablation shows none except under S1, where it is better than adaptive_full, −0.0170 [−0.0330, −0.0010] (adaptive − no_review; recomputed from `evaluation/results/w8/final_v2/integrated_s1/per_learner_seed_*.csv`);
  - the remediation ablation never disables remediation;
  - remediation never fires in the closed loop.
- **prerequisite importance** now orders due reviews (B11 fix). Its effect on the final runs was not isolated: a 20-learner toy S0 check showed no change (`evaluation/results/w8_evidence/after_fix4_review_importance.txt`).

## 7. Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q
python -m src.evaluation.integrated --config experiments/w8_final.yaml --out out/s0
python -m src.evaluation.integrated --config experiments/w8_final_s1.yaml --out out/s1
python -m src.evaluation.integrated --config experiments/w8_toy_s3.yaml --out out/toy_s3
python -m src.evaluation.integrated --config experiments/w8_maths_s0.yaml --out out/maths_s0
python -m src.evaluation.integrated --config experiments/w8_maths_s3.yaml --out out/maths_s3
python scripts/w7_pooled_s0.py out/s1 adaptive_full:static_prerequisite_order adaptive_full:non_adaptive_greedy adaptive_full:ablation_no_diagnostic
python scripts/w8_final_v2_compare.py
python -m src.evaluation.diagnostic_comparison --config experiments/w4_comparison.yaml --out out/diagnostic_comparison
```

Compare the per-learner CSVs with `evaluation/results/w8/final_v2/` on all columns except `runtime_ms` (add `--horizon=10` to `w7_pooled_s0.py` for the maths runs). `scripts/w8_final_v2_compare.py` reads the committed runs. The clean-clone audit is `scripts/clean_run.ps1`. The demo walkthrough is in [`DEMO.md`](DEMO.md).
