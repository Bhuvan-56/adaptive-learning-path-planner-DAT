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
| **adaptive_full** | 2.6400 [2.4150, 2.8650] | 0 | 0 | 100.0% | 38 (SCHEDULING_CONSTRAINTS_UNMET:19, CAPACITY_EXCEEDED:19) | 13.225 | 23.796 |
| **static_prerequisite_order** | 2.5400 [2.3000, 2.7800] | 0 | 0 | 100.0% | 0 | 0.561 | 1.425 |
| **non_adaptive_greedy** | 2.5400 [2.3000, 2.7800] | 0 | 0 | 100.0% | 0 | 0.017 | 0.041 |
| **non_adaptive_greedy_best_singleton** | 2.5500 [2.3100, 2.7800] | 0 | 0 | 100.0% | 0 | 0.034 | 0.071 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.1000 | [0.0500, 0.1600] | **adaptive_full improves on static_prerequisite_order** [0.0500, 0.1600] |
| **adaptive_full - non_adaptive_greedy** | 0.1000 | [0.0500, 0.1600] | **adaptive_full improves on non_adaptive_greedy** [0.0500, 0.1600] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0100 | [-0.0250, 0.0450] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.8650 [2.7000, 3.0151] | -0.2250 [-0.3450, -0.1050] | ablation_no_diagnostic improves on adaptive_full [0.1050, 0.3450] |
| **ablation_no_replan** | 2.5350 [2.2950, 2.7701] | 0.1050 [0.0550, 0.1601] | adaptive_full improves on ablation_no_replan [0.0550, 0.1601] |
| **ablation_no_difficulty_step** | 2.6450 [2.4199, 2.8701] | -0.0050 [-0.0150, 0.0000] | no difference shown |
| **ablation_no_review** | 2.6400 [2.4150, 2.8650] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.6400 [2.4150, 2.8650] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1650 [0.1463, 0.1843] | 0.0896 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1359 [0.1232, 0.1491] | 0.0793 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1645 [0.1462, 0.1841] | 0.0906 | 800 |
| ablation_no_review | 0.1657 [0.1473, 0.1849] | 0.0841 | 800 |
| ablation_no_remediation | 0.1650 [0.1463, 0.1843] | 0.0896 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 43 | 0.1436 | 0.0930 |
| 0.2–0.3 | 89 | 0.2192 | 0.4270 |
| 0.3–0.4 | 19 | 0.3737 | 0.4211 |
| 0.4–0.5 | 42 | 0.4502 | 0.5000 |
| 0.5–0.6 | 48 | 0.5314 | 0.3125 |
| 0.6–0.7 | 52 | 0.6564 | 0.4423 |
| 0.7–0.8 | 81 | 0.7473 | 0.6543 |
| 0.8–0.9 | 264 | 0.8298 | 0.7955 |
| 0.9–1.0 | 157 | 0.9336 | 0.9936 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 28 | 0.1479 | 0.3571 |
| 0.2–0.3 | 7 | 0.2195 | 0.5714 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 48 | 0.4176 | 0.5625 |
| 0.5–0.6 | 241 | 0.5059 | 0.3485 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 73 | 0.7363 | 0.8493 |
| 0.8–0.9 | 52 | 0.8247 | 0.8462 |
| 0.9–1.0 | 351 | 0.9718 | 0.9744 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 6 | 0.0737 | 0.0000 |
| 0.1–0.2 | 43 | 0.1440 | 0.0930 |
| 0.2–0.3 | 90 | 0.2195 | 0.4222 |
| 0.3–0.4 | 19 | 0.3734 | 0.4737 |
| 0.4–0.5 | 41 | 0.4476 | 0.5122 |
| 0.5–0.6 | 47 | 0.5300 | 0.3191 |
| 0.6–0.7 | 52 | 0.6564 | 0.4423 |
| 0.7–0.8 | 81 | 0.7473 | 0.6543 |
| 0.8–0.9 | 264 | 0.8298 | 0.7955 |
| 0.9–1.0 | 157 | 0.9336 | 0.9936 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 43 | 0.1436 | 0.0930 |
| 0.2–0.3 | 89 | 0.2192 | 0.4270 |
| 0.3–0.4 | 19 | 0.3737 | 0.4211 |
| 0.4–0.5 | 42 | 0.4502 | 0.5000 |
| 0.5–0.6 | 53 | 0.5350 | 0.3774 |
| 0.6–0.7 | 55 | 0.6562 | 0.4727 |
| 0.7–0.8 | 83 | 0.7478 | 0.6627 |
| 0.8–0.9 | 235 | 0.8238 | 0.7702 |
| 0.9–1.0 | 176 | 0.9649 | 0.9943 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 43 | 0.1436 | 0.0930 |
| 0.2–0.3 | 89 | 0.2192 | 0.4270 |
| 0.3–0.4 | 19 | 0.3737 | 0.4211 |
| 0.4–0.5 | 42 | 0.4502 | 0.5000 |
| 0.5–0.6 | 48 | 0.5314 | 0.3125 |
| 0.6–0.7 | 52 | 0.6564 | 0.4423 |
| 0.7–0.8 | 81 | 0.7473 | 0.6543 |
| 0.8–0.9 | 264 | 0.8298 | 0.7955 |
| 0.9–1.0 | 157 | 0.9336 | 0.9936 |
