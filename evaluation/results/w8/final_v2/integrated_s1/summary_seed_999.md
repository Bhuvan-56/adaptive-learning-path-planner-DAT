# Week 5 Integrated Evaluation Summary: Closed-Loop Path Planning

## 1. Evaluation Setup & Input Provenance

- **Benchmark Name:** `w5_integrated`
- **Evaluated Cohort:** 200 synthetic learners (paired random seeds)
- **Planning Horizon:** 5 days
- **Daily Study Budget:** 10 minutes
- **Bootstrap Resamples (B):** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `MatchedBKTGenerator` (BKT response dynamics)
- **Runtime Note:** Planning runtimes reported from one machine and one run.

### Arm Configuration Matrix

| Arm | Diagnostic Inputs | Planner Algorithm | Difficulty Stepping | Dynamic Replanning | Spaced Review | Prerequisite Remediation |
|---|---|---|---|---|---|---|
| **adaptive_full** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On (HLR decay baseline) | On (k=2 failures) |
| **static_prerequisite_order** | Initial priors (IRT CAT) | Static Topological Sort (`generate_static_plan`) | Static base | Off | Off | Off |
| **non_adaptive_greedy** | Mastered set ($n < \text{min\_obs} \implies \emptyset$) | Score/duration frontier packing | Static base | Off | Off | Off |
| **non_adaptive_greedy_best_singleton** | Same as non_adaptive_greedy | Frontier packing, then best-singleton fallback (`src.planning.greedy_fallback`) | Static base | Off | Off | Off |
| **ablation_no_diagnostic** | Cold-start priors (p=0.5) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On | On |
| **ablation_no_replan** | Initial priors (IRT CAT) | Static Topological Sort (`generate_static_plan`) | 2-Up / 1-Down staircase | Off | Off | Off |
| **ablation_no_difficulty_step** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | Static base | On | On | On |
| **ablation_no_review** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | Off | On |
| **ablation_no_remediation** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On | Off |

## 2. Primary Arm Performance Results

| Arm | Concepts Mastered [95% CI] | Prereq Violations | Budget Violations | Trace Coverage (%) | No-Plan Results | Runtime p50 (ms) | Runtime p95 (ms) |
|---|---|---|---|---|---|---|---|
| **adaptive_full** | 1.8300 [1.6450, 2.0300] | 0 | 0 | 100.0% | 105 (SCHEDULING_CONSTRAINTS_UNMET:49, CAPACITY_EXCEEDED:56) | 13.516 | 23.387 |
| **static_prerequisite_order** | 1.8100 [1.6250, 2.0150] | 0 | 0 | 100.0% | 0 | 0.583 | 1.288 |
| **non_adaptive_greedy** | 1.8100 [1.6150, 2.0150] | 0 | 0 | 100.0% | 0 | 0.016 | 0.036 |
| **non_adaptive_greedy_best_singleton** | 1.8000 [1.6100, 1.9950] | 0 | 0 | 100.0% | 0 | 0.034 | 0.082 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0200 | [-0.0300, 0.0700] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0200 | [-0.0650, 0.1100] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [-0.0750, 0.0750] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0100 | [-0.0450, 0.0300] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 1.8900 [1.7050, 2.0800] | -0.0600 [-0.1500, 0.0300] | no difference shown |
| **ablation_no_replan** | 1.8100 [1.6250, 2.0151] | 0.0200 [-0.0250, 0.0650] | no difference shown |
| **ablation_no_difficulty_step** | 1.8300 [1.6450, 2.0300] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.8100 [1.6250, 2.0051] | 0.0200 [-0.0151, 0.0600] | no difference shown |
| **ablation_no_remediation** | 1.8300 [1.6450, 2.0300] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1917 [0.1734, 0.2085] | 0.1471 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1842 [0.1681, 0.2006] | 0.1356 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1917 [0.1734, 0.2085] | 0.1471 | 800 |
| ablation_no_review | 0.1901 [0.1732, 0.2070] | 0.1532 | 800 |
| ablation_no_remediation | 0.1917 [0.1734, 0.2085] | 0.1471 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 89 | 0.1424 | 0.0674 |
| 0.2–0.3 | 105 | 0.2195 | 0.1333 |
| 0.3–0.4 | 41 | 0.3593 | 0.2683 |
| 0.4–0.5 | 47 | 0.4529 | 0.3191 |
| 0.5–0.6 | 65 | 0.5115 | 0.1077 |
| 0.6–0.7 | 23 | 0.6506 | 0.4348 |
| 0.7–0.8 | 65 | 0.7493 | 0.5231 |
| 0.8–0.9 | 216 | 0.8336 | 0.7269 |
| 0.9–1.0 | 144 | 0.9349 | 0.7778 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 141 | 0.1347 | 0.0922 |
| 0.2–0.3 | 15 | 0.2195 | 0.2667 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 64 | 0.4163 | 0.3750 |
| 0.5–0.6 | 230 | 0.5045 | 0.2652 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 64 | 0.7335 | 0.6094 |
| 0.8–0.9 | 34 | 0.8247 | 0.5588 |
| 0.9–1.0 | 252 | 0.9726 | 0.8651 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 89 | 0.1424 | 0.0674 |
| 0.2–0.3 | 105 | 0.2195 | 0.1333 |
| 0.3–0.4 | 41 | 0.3593 | 0.2683 |
| 0.4–0.5 | 47 | 0.4529 | 0.3191 |
| 0.5–0.6 | 65 | 0.5115 | 0.1077 |
| 0.6–0.7 | 23 | 0.6506 | 0.4348 |
| 0.7–0.8 | 65 | 0.7493 | 0.5231 |
| 0.8–0.9 | 216 | 0.8336 | 0.7269 |
| 0.9–1.0 | 144 | 0.9349 | 0.7778 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 89 | 0.1424 | 0.0674 |
| 0.2–0.3 | 105 | 0.2195 | 0.1333 |
| 0.3–0.4 | 41 | 0.3593 | 0.2683 |
| 0.4–0.5 | 47 | 0.4529 | 0.3191 |
| 0.5–0.6 | 70 | 0.5139 | 0.1286 |
| 0.6–0.7 | 32 | 0.6574 | 0.3750 |
| 0.7–0.8 | 69 | 0.7495 | 0.5217 |
| 0.8–0.9 | 190 | 0.8277 | 0.6842 |
| 0.9–1.0 | 152 | 0.9633 | 0.8487 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 89 | 0.1424 | 0.0674 |
| 0.2–0.3 | 105 | 0.2195 | 0.1333 |
| 0.3–0.4 | 41 | 0.3593 | 0.2683 |
| 0.4–0.5 | 47 | 0.4529 | 0.3191 |
| 0.5–0.6 | 65 | 0.5115 | 0.1077 |
| 0.6–0.7 | 23 | 0.6506 | 0.4348 |
| 0.7–0.8 | 65 | 0.7493 | 0.5231 |
| 0.8–0.9 | 216 | 0.8336 | 0.7269 |
| 0.9–1.0 | 144 | 0.9349 | 0.7778 |
