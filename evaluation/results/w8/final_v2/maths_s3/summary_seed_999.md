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
| **adaptive_full** | 8.0550 [7.4149, 8.7203] | 0 | 0 | 100.0% | 1091 (SCHEDULING_CONSTRAINTS_UNMET:474, CAPACITY_EXCEEDED:617) | 73.167 | 102.027 |
| **static_prerequisite_order** | 7.3850 [6.6250, 8.1902] | 0 | 0 | 100.0% | 0 | 2.761 | 4.374 |
| **non_adaptive_greedy** | 7.7050 [6.9349, 8.5200] | 0 | 0 | 100.0% | 0 | 0.061 | 0.101 |
| **non_adaptive_greedy_best_singleton** | 7.7550 [6.9746, 8.5701] | 0 | 0 | 100.0% | 0 | 0.103 | 0.196 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.6700 | [0.4350, 0.9150] | **adaptive_full improves on static_prerequisite_order** [0.4350, 0.9150] |
| **adaptive_full - non_adaptive_greedy** | 0.3500 | [0.1049, 0.5700] | **adaptive_full improves on non_adaptive_greedy** [0.1049, 0.5700] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.3200 | [0.1650, 0.4750] | **non_adaptive_greedy improves on static_prerequisite_order** [0.1650, 0.4750] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0500 | [-0.0100, 0.1100] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 8.0800 [7.4750, 8.7251] | -0.0250 [-0.1450, 0.0950] | no difference shown |
| **ablation_no_replan** | 7.3850 [6.6200, 8.1901] | 0.6700 [0.4399, 0.9150] | adaptive_full improves on ablation_no_replan [0.4399, 0.9150] |
| **ablation_no_difficulty_step** | 8.0450 [7.3949, 8.7151] | 0.0100 [0.0000, 0.0250] | no difference shown |
| **ablation_no_review** | 8.0550 [7.4149, 8.7203] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 8.0550 [7.4149, 8.7203] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1832 [0.1746, 0.1919] | 0.1462 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1884 [0.1803, 0.1964] | 0.1479 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1831 [0.1748, 0.1917] | 0.1472 | 3200 |
| ablation_no_review | 0.1833 [0.1747, 0.1920] | 0.1443 | 3200 |
| ablation_no_remediation | 0.1832 [0.1746, 0.1919] | 0.1462 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0737 | 0.0000 |
| 0.1–0.2 | 99 | 0.1449 | 0.1717 |
| 0.2–0.3 | 68 | 0.2261 | 0.3971 |
| 0.3–0.4 | 14 | 0.3661 | 0.3571 |
| 0.4–0.5 | 98 | 0.4314 | 0.3980 |
| 0.5–0.6 | 1661 | 0.5011 | 0.2468 |
| 0.6–0.7 | 53 | 0.6559 | 0.4906 |
| 0.7–0.8 | 266 | 0.7401 | 0.7820 |
| 0.8–0.9 | 305 | 0.8374 | 0.8557 |
| 0.9–1.0 | 634 | 0.9713 | 0.9748 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 70 | 0.1526 | 0.2571 |
| 0.2–0.3 | 150 | 0.2103 | 0.2867 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 66 | 0.4149 | 0.3333 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2487 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 216 | 0.7350 | 0.7870 |
| 0.8–0.9 | 466 | 0.8116 | 0.7554 |
| 0.9–1.0 | 632 | 0.9851 | 0.9699 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0737 | 0.0000 |
| 0.1–0.2 | 110 | 0.1447 | 0.1727 |
| 0.2–0.3 | 66 | 0.2266 | 0.4242 |
| 0.3–0.4 | 14 | 0.3661 | 0.3571 |
| 0.4–0.5 | 96 | 0.4324 | 0.4062 |
| 0.5–0.6 | 1663 | 0.5011 | 0.2465 |
| 0.6–0.7 | 53 | 0.6559 | 0.4906 |
| 0.7–0.8 | 258 | 0.7404 | 0.7868 |
| 0.8–0.9 | 300 | 0.8376 | 0.8600 |
| 0.9–1.0 | 638 | 0.9713 | 0.9734 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0737 | 0.0000 |
| 0.1–0.2 | 101 | 0.1455 | 0.1881 |
| 0.2–0.3 | 64 | 0.2266 | 0.3594 |
| 0.3–0.4 | 14 | 0.3661 | 0.3571 |
| 0.4–0.5 | 102 | 0.4307 | 0.4216 |
| 0.5–0.6 | 1662 | 0.5012 | 0.2473 |
| 0.6–0.7 | 54 | 0.6550 | 0.5000 |
| 0.7–0.8 | 269 | 0.7396 | 0.7844 |
| 0.8–0.9 | 284 | 0.8346 | 0.8451 |
| 0.9–1.0 | 648 | 0.9788 | 0.9753 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0737 | 0.0000 |
| 0.1–0.2 | 99 | 0.1449 | 0.1717 |
| 0.2–0.3 | 68 | 0.2261 | 0.3971 |
| 0.3–0.4 | 14 | 0.3661 | 0.3571 |
| 0.4–0.5 | 98 | 0.4314 | 0.3980 |
| 0.5–0.6 | 1661 | 0.5011 | 0.2468 |
| 0.6–0.7 | 53 | 0.6559 | 0.4906 |
| 0.7–0.8 | 266 | 0.7401 | 0.7820 |
| 0.8–0.9 | 305 | 0.8374 | 0.8557 |
| 0.9–1.0 | 634 | 0.9713 | 0.9748 |
