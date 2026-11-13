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
| **adaptive_full** | 2.5300 [2.3050, 2.7452] | 0 | 0 | 100.0% | 53 (SCHEDULING_CONSTRAINTS_UNMET:22, CAPACITY_EXCEEDED:31) | 13.205 | 22.549 |
| **static_prerequisite_order** | 2.4100 [2.1849, 2.6250] | 0 | 0 | 100.0% | 0 | 0.548 | 1.244 |
| **non_adaptive_greedy** | 2.4100 [2.1849, 2.6250] | 0 | 0 | 100.0% | 0 | 0.016 | 0.041 |
| **non_adaptive_greedy_best_singleton** | 2.4300 [2.2049, 2.6401] | 0 | 0 | 100.0% | 0 | 0.035 | 0.084 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.1200 | [0.0700, 0.1800] | **adaptive_full improves on static_prerequisite_order** [0.0700, 0.1800] |
| **adaptive_full - non_adaptive_greedy** | 0.1200 | [0.0700, 0.1800] | **adaptive_full improves on non_adaptive_greedy** [0.0700, 0.1800] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0200 | [-0.0150, 0.0551] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.6950 [2.5248, 2.8601] | -0.1650 [-0.2900, -0.0350] | ablation_no_diagnostic improves on adaptive_full [0.0350, 0.2900] |
| **ablation_no_replan** | 2.4100 [2.1849, 2.6250] | 0.1200 [0.0700, 0.1800] | adaptive_full improves on ablation_no_replan [0.0700, 0.1800] |
| **ablation_no_difficulty_step** | 2.5300 [2.3050, 2.7452] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.5300 [2.3050, 2.7452] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.5300 [2.3050, 2.7452] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1550 [0.1381, 0.1724] | 0.0700 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1391 [0.1229, 0.1550] | 0.0890 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1546 [0.1376, 0.1715] | 0.0694 | 800 |
| ablation_no_review | 0.1552 [0.1385, 0.1724] | 0.0670 | 800 |
| ablation_no_remediation | 0.1550 [0.1381, 0.1724] | 0.0700 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 9 | 0.0672 | 0.0000 |
| 0.1–0.2 | 39 | 0.1391 | 0.1795 |
| 0.2–0.3 | 89 | 0.2178 | 0.2921 |
| 0.3–0.4 | 27 | 0.3578 | 0.1481 |
| 0.4–0.5 | 41 | 0.4424 | 0.3171 |
| 0.5–0.6 | 55 | 0.5292 | 0.3091 |
| 0.6–0.7 | 49 | 0.6547 | 0.5714 |
| 0.7–0.8 | 103 | 0.7511 | 0.7087 |
| 0.8–0.9 | 253 | 0.8295 | 0.8024 |
| 0.9–1.0 | 135 | 0.9334 | 1.0000 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 29 | 0.1346 | 0.1034 |
| 0.2–0.3 | 10 | 0.2195 | 0.4000 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 38 | 0.4174 | 0.3421 |
| 0.5–0.6 | 239 | 0.5056 | 0.3180 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 63 | 0.7323 | 0.8571 |
| 0.8–0.9 | 48 | 0.8247 | 0.7917 |
| 0.9–1.0 | 373 | 0.9715 | 0.9410 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0678 | 0.0000 |
| 0.1–0.2 | 39 | 0.1391 | 0.1795 |
| 0.2–0.3 | 89 | 0.2178 | 0.2921 |
| 0.3–0.4 | 26 | 0.3600 | 0.1538 |
| 0.4–0.5 | 42 | 0.4432 | 0.3095 |
| 0.5–0.6 | 55 | 0.5292 | 0.3091 |
| 0.6–0.7 | 49 | 0.6547 | 0.5714 |
| 0.7–0.8 | 102 | 0.7515 | 0.7157 |
| 0.8–0.9 | 253 | 0.8295 | 0.8024 |
| 0.9–1.0 | 135 | 0.9334 | 1.0000 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 9 | 0.0672 | 0.0000 |
| 0.1–0.2 | 39 | 0.1391 | 0.1795 |
| 0.2–0.3 | 89 | 0.2178 | 0.2921 |
| 0.3–0.4 | 27 | 0.3578 | 0.1481 |
| 0.4–0.5 | 42 | 0.4438 | 0.3333 |
| 0.5–0.6 | 56 | 0.5299 | 0.3214 |
| 0.6–0.7 | 52 | 0.6554 | 0.5962 |
| 0.7–0.8 | 105 | 0.7511 | 0.7143 |
| 0.8–0.9 | 227 | 0.8244 | 0.7797 |
| 0.9–1.0 | 154 | 0.9630 | 1.0000 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 9 | 0.0672 | 0.0000 |
| 0.1–0.2 | 39 | 0.1391 | 0.1795 |
| 0.2–0.3 | 89 | 0.2178 | 0.2921 |
| 0.3–0.4 | 27 | 0.3578 | 0.1481 |
| 0.4–0.5 | 41 | 0.4424 | 0.3171 |
| 0.5–0.6 | 55 | 0.5292 | 0.3091 |
| 0.6–0.7 | 49 | 0.6547 | 0.5714 |
| 0.7–0.8 | 103 | 0.7511 | 0.7087 |
| 0.8–0.9 | 253 | 0.8295 | 0.8024 |
| 0.9–1.0 | 135 | 0.9334 | 1.0000 |
