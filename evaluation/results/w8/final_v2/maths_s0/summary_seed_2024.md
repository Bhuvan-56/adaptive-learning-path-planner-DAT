# Week 5 Integrated Evaluation Summary: Closed-Loop Path Planning

## 1. Evaluation Setup & Input Provenance

- **Benchmark Name:** `w5_integrated`
- **Evaluated Cohort:** 200 synthetic learners (paired random seeds)
- **Planning Horizon:** 10 days
- **Daily Study Budget:** 30 minutes
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
| **adaptive_full** | 6.3850 [5.6599, 7.1102] | 0 | 0 | 100.0% | 1149 (SCHEDULING_CONSTRAINTS_UNMET:478, CAPACITY_EXCEEDED:671) | 75.157 | 115.422 |
| **static_prerequisite_order** | 6.3100 [5.5749, 7.0351] | 0 | 0 | 100.0% | 0 | 2.958 | 5.588 |
| **non_adaptive_greedy** | 6.4150 [5.7048, 7.1452] | 0 | 0 | 100.0% | 0 | 0.063 | 0.143 |
| **non_adaptive_greedy_best_singleton** | 6.5050 [5.7950, 7.2550] | 0 | 0 | 100.0% | 0 | 0.105 | 0.149 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0750 | [-0.0201, 0.1750] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | -0.0300 | [-0.1350, 0.0750] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.1050 | [0.0299, 0.1750] | **non_adaptive_greedy improves on static_prerequisite_order** [0.0299, 0.1750] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0900 | [0.0500, 0.1350] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0500, 0.1350] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 6.5300 [5.8300, 7.2301] | -0.1450 [-0.2401, -0.0450] | ablation_no_diagnostic improves on adaptive_full [0.0450, 0.2401] |
| **ablation_no_replan** | 6.3200 [5.5849, 7.0700] | 0.0650 [-0.0350, 0.1700] | no difference shown |
| **ablation_no_difficulty_step** | 6.3850 [5.6599, 7.1102] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 6.3850 [5.6550, 7.1100] | 0.0000 [-0.0200, 0.0200] | no difference shown |
| **ablation_no_remediation** | 6.3850 [5.6599, 7.1102] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1877 [0.1815, 0.1943] | 0.1676 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1828 [0.1768, 0.1886] | 0.1485 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1877 [0.1815, 0.1943] | 0.1676 | 3200 |
| ablation_no_review | 0.1881 [0.1820, 0.1947] | 0.1647 | 3200 |
| ablation_no_remediation | 0.1877 [0.1815, 0.1943] | 0.1676 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 13 | 0.0694 | 0.0000 |
| 0.1–0.2 | 330 | 0.1348 | 0.1242 |
| 0.2–0.3 | 81 | 0.2238 | 0.2469 |
| 0.3–0.4 | 24 | 0.3572 | 0.4583 |
| 0.4–0.5 | 127 | 0.4256 | 0.4252 |
| 0.5–0.6 | 1747 | 0.5004 | 0.2124 |
| 0.6–0.7 | 32 | 0.6526 | 0.5938 |
| 0.7–0.8 | 201 | 0.7404 | 0.7264 |
| 0.8–0.9 | 229 | 0.8376 | 0.9083 |
| 0.9–1.0 | 416 | 0.9697 | 0.9784 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 317 | 0.1342 | 0.0978 |
| 0.2–0.3 | 267 | 0.2104 | 0.2060 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 125 | 0.4149 | 0.4800 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2319 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 140 | 0.7334 | 0.8071 |
| 0.8–0.9 | 340 | 0.8115 | 0.7824 |
| 0.9–1.0 | 411 | 0.9851 | 0.9976 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 13 | 0.0694 | 0.0000 |
| 0.1–0.2 | 330 | 0.1348 | 0.1242 |
| 0.2–0.3 | 81 | 0.2238 | 0.2469 |
| 0.3–0.4 | 24 | 0.3572 | 0.4583 |
| 0.4–0.5 | 127 | 0.4256 | 0.4252 |
| 0.5–0.6 | 1747 | 0.5004 | 0.2124 |
| 0.6–0.7 | 32 | 0.6526 | 0.5938 |
| 0.7–0.8 | 201 | 0.7404 | 0.7264 |
| 0.8–0.9 | 229 | 0.8376 | 0.9083 |
| 0.9–1.0 | 416 | 0.9697 | 0.9784 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 13 | 0.0694 | 0.0000 |
| 0.1–0.2 | 328 | 0.1348 | 0.1220 |
| 0.2–0.3 | 86 | 0.2234 | 0.2674 |
| 0.3–0.4 | 24 | 0.3572 | 0.4583 |
| 0.4–0.5 | 126 | 0.4256 | 0.4206 |
| 0.5–0.6 | 1750 | 0.5005 | 0.2137 |
| 0.6–0.7 | 37 | 0.6521 | 0.6486 |
| 0.7–0.8 | 208 | 0.7411 | 0.7404 |
| 0.8–0.9 | 206 | 0.8336 | 0.8932 |
| 0.9–1.0 | 422 | 0.9792 | 0.9810 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 13 | 0.0694 | 0.0000 |
| 0.1–0.2 | 330 | 0.1348 | 0.1242 |
| 0.2–0.3 | 81 | 0.2238 | 0.2469 |
| 0.3–0.4 | 24 | 0.3572 | 0.4583 |
| 0.4–0.5 | 127 | 0.4256 | 0.4252 |
| 0.5–0.6 | 1747 | 0.5004 | 0.2124 |
| 0.6–0.7 | 32 | 0.6526 | 0.5938 |
| 0.7–0.8 | 201 | 0.7404 | 0.7264 |
| 0.8–0.9 | 229 | 0.8376 | 0.9083 |
| 0.9–1.0 | 416 | 0.9697 | 0.9784 |
