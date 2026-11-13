# Week 5 Integrated Evaluation Summary: Multi-Seed Benchmark

## 1. Multi-Seed Benchmark Setup

- **Benchmark Name:** `w5_integrated_multiseed`
- **Evaluated Seeds (5):** `[42, 101, 2024, 777, 999]`
- **Synthetic Learners per Seed:** 200
- **Total Synthetic Learners Evaluated:** 1000
- **Planning Horizon:** 5 days
- **Daily Study Budget:** 10 minutes
- **Bootstrap Resamples per Seed:** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `MatchedBKTGenerator` (BKT response dynamics)

## 2. Per-Seed Performance Table (Primary Arms)

| Seed | adaptive_full [95% CI] | static_prerequisite_order [95% CI] | non_adaptive_greedy [95% CI] | adaptive minus static [95% CI] | Claim Assessment | No-Plan Days (adaptive) |
|---|---|---|---|---|---|---|
| **42** | 2.4750 [2.2399, 2.6901] | 2.3450 [2.0900, 2.5800] | 2.3450 [2.0900, 2.5800] | 0.1300 [0.0750, 0.1900] | adaptive_full improves on static_prerequisite_order [0.0750, 0.1900] | 54 |
| **101** | 2.3500 [2.1250, 2.5651] | 2.2100 [1.9898, 2.4450] | 2.2100 [1.9898, 2.4450] | 0.1400 [0.0900, 0.1900] | adaptive_full improves on static_prerequisite_order [0.0900, 0.1900] | 61 |
| **2024** | 2.5300 [2.3050, 2.7452] | 2.4100 [2.1849, 2.6250] | 2.4100 [2.1849, 2.6250] | 0.1200 [0.0700, 0.1800] | adaptive_full improves on static_prerequisite_order [0.0700, 0.1800] | 53 |
| **777** | 2.2600 [2.0299, 2.4901] | 2.1650 [1.9250, 2.4001] | 2.1650 [1.9250, 2.4001] | 0.0950 [0.0500, 0.1450] | adaptive_full improves on static_prerequisite_order [0.0500, 0.1450] | 52 |
| **999** | 2.6400 [2.4150, 2.8650] | 2.5400 [2.3000, 2.7800] | 2.5400 [2.3000, 2.7800] | 0.1000 [0.0500, 0.1600] | adaptive_full improves on static_prerequisite_order [0.0500, 0.1600] | 38 |

## Mastery calibration, pooled over seeds [42, 101, 2024, 777, 999] (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1667 [0.1581, 0.1760] | 0.0888 | 4000 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1416 [0.1346, 0.1481] | 0.0791 | 4000 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1664 [0.1577, 0.1757] | 0.0879 | 4000 |
| ablation_no_review | 0.1665 [0.1579, 0.1757] | 0.0833 | 4000 |
| ablation_no_remediation | 0.1667 [0.1581, 0.1760] | 0.0888 | 4000 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 25 | 0.0705 | 0.0000 |
| 0.1–0.2 | 239 | 0.1422 | 0.0962 |
| 0.2–0.3 | 449 | 0.2175 | 0.3229 |
| 0.3–0.4 | 105 | 0.3653 | 0.3048 |
| 0.4–0.5 | 229 | 0.4449 | 0.3668 |
| 0.5–0.6 | 290 | 0.5285 | 0.2655 |
| 0.6–0.7 | 230 | 0.6520 | 0.4304 |
| 0.7–0.8 | 450 | 0.7488 | 0.6956 |
| 0.8–0.9 | 1280 | 0.8289 | 0.7672 |
| 0.9–1.0 | 703 | 0.9320 | 0.9900 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 173 | 0.1377 | 0.1676 |
| 0.2–0.3 | 56 | 0.2195 | 0.3750 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 229 | 0.4173 | 0.4410 |
| 0.5–0.6 | 1187 | 0.5054 | 0.3210 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 353 | 0.7348 | 0.8272 |
| 0.8–0.9 | 241 | 0.8247 | 0.7884 |
| 0.9–1.0 | 1761 | 0.9716 | 0.9506 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 27 | 0.0708 | 0.0000 |
| 0.1–0.2 | 239 | 0.1420 | 0.0962 |
| 0.2–0.3 | 451 | 0.2176 | 0.3215 |
| 0.3–0.4 | 105 | 0.3661 | 0.3143 |
| 0.4–0.5 | 228 | 0.4444 | 0.3684 |
| 0.5–0.6 | 289 | 0.5283 | 0.2664 |
| 0.6–0.7 | 230 | 0.6520 | 0.4304 |
| 0.7–0.8 | 448 | 0.7490 | 0.6987 |
| 0.8–0.9 | 1280 | 0.8289 | 0.7672 |
| 0.9–1.0 | 703 | 0.9320 | 0.9900 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 25 | 0.0705 | 0.0000 |
| 0.1–0.2 | 239 | 0.1422 | 0.0962 |
| 0.2–0.3 | 449 | 0.2175 | 0.3229 |
| 0.3–0.4 | 105 | 0.3653 | 0.3048 |
| 0.4–0.5 | 231 | 0.4453 | 0.3723 |
| 0.5–0.6 | 308 | 0.5309 | 0.3084 |
| 0.6–0.7 | 245 | 0.6525 | 0.4653 |
| 0.7–0.8 | 456 | 0.7490 | 0.6996 |
| 0.8–0.9 | 1153 | 0.8240 | 0.7450 |
| 0.9–1.0 | 789 | 0.9631 | 0.9911 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 25 | 0.0705 | 0.0000 |
| 0.1–0.2 | 239 | 0.1422 | 0.0962 |
| 0.2–0.3 | 449 | 0.2175 | 0.3229 |
| 0.3–0.4 | 105 | 0.3653 | 0.3048 |
| 0.4–0.5 | 229 | 0.4449 | 0.3668 |
| 0.5–0.6 | 290 | 0.5285 | 0.2655 |
| 0.6–0.7 | 230 | 0.6520 | 0.4304 |
| 0.7–0.8 | 450 | 0.7488 | 0.6956 |
| 0.8–0.9 | 1280 | 0.8289 | 0.7672 |
| 0.9–1.0 | 703 | 0.9320 | 0.9900 |

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
| **adaptive_full** | 2.4750 [2.2399, 2.6901] | 0 | 0 | 100.0% | 54 (SCHEDULING_CONSTRAINTS_UNMET:26, CAPACITY_EXCEEDED:28) | 12.946 | 20.866 |
| **static_prerequisite_order** | 2.3450 [2.0900, 2.5800] | 0 | 0 | 100.0% | 0 | 0.534 | 1.350 |
| **non_adaptive_greedy** | 2.3450 [2.0900, 2.5800] | 0 | 0 | 100.0% | 0 | 0.016 | 0.041 |
| **non_adaptive_greedy_best_singleton** | 2.3400 [2.0850, 2.5800] | 0 | 0 | 100.0% | 0 | 0.034 | 0.086 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.1300 | [0.0750, 0.1900] | **adaptive_full improves on static_prerequisite_order** [0.0750, 0.1900] |
| **adaptive_full - non_adaptive_greedy** | 0.1300 | [0.0750, 0.1900] | **adaptive_full improves on non_adaptive_greedy** [0.0750, 0.1900] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0050 | [-0.0500, 0.0350] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.7050 [2.5400, 2.8600] | -0.2300 [-0.3551, -0.1050] | ablation_no_diagnostic improves on adaptive_full [0.1050, 0.3551] |
| **ablation_no_replan** | 2.3450 [2.0900, 2.5800] | 0.1300 [0.0750, 0.1900] | adaptive_full improves on ablation_no_replan [0.0750, 0.1900] |
| **ablation_no_difficulty_step** | 2.4750 [2.2399, 2.6901] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.4850 [2.2550, 2.7050] | -0.0100 [-0.0400, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.4750 [2.2399, 2.6901] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1696 [0.1505, 0.1919] | 0.1056 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1353 [0.1240, 0.1496] | 0.0904 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1695 [0.1503, 0.1919] | 0.1045 | 800 |
| ablation_no_review | 0.1686 [0.1499, 0.1904] | 0.0996 | 800 |
| ablation_no_remediation | 0.1696 [0.1505, 0.1919] | 0.1056 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 45 | 0.1424 | 0.0444 |
| 0.2–0.3 | 90 | 0.2183 | 0.3444 |
| 0.3–0.4 | 18 | 0.3568 | 0.4444 |
| 0.4–0.5 | 33 | 0.4456 | 0.3333 |
| 0.5–0.6 | 71 | 0.5289 | 0.2676 |
| 0.6–0.7 | 39 | 0.6459 | 0.3333 |
| 0.7–0.8 | 87 | 0.7493 | 0.8046 |
| 0.8–0.9 | 288 | 0.8290 | 0.7569 |
| 0.9–1.0 | 125 | 0.9296 | 0.9840 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 33 | 0.1381 | 0.1818 |
| 0.2–0.3 | 11 | 0.2195 | 0.3636 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 55 | 0.4171 | 0.4727 |
| 0.5–0.6 | 241 | 0.5059 | 0.2988 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 73 | 0.7367 | 0.9041 |
| 0.8–0.9 | 44 | 0.8247 | 0.8409 |
| 0.9–1.0 | 343 | 0.9720 | 0.9621 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 45 | 0.1424 | 0.0444 |
| 0.2–0.3 | 90 | 0.2183 | 0.3444 |
| 0.3–0.4 | 19 | 0.3585 | 0.4211 |
| 0.4–0.5 | 32 | 0.4443 | 0.3438 |
| 0.5–0.6 | 71 | 0.5289 | 0.2676 |
| 0.6–0.7 | 39 | 0.6459 | 0.3333 |
| 0.7–0.8 | 87 | 0.7493 | 0.8046 |
| 0.8–0.9 | 288 | 0.8290 | 0.7569 |
| 0.9–1.0 | 125 | 0.9296 | 0.9840 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 45 | 0.1424 | 0.0444 |
| 0.2–0.3 | 90 | 0.2183 | 0.3444 |
| 0.3–0.4 | 18 | 0.3568 | 0.4444 |
| 0.4–0.5 | 34 | 0.4469 | 0.3529 |
| 0.5–0.6 | 75 | 0.5312 | 0.3067 |
| 0.6–0.7 | 42 | 0.6472 | 0.3810 |
| 0.7–0.8 | 87 | 0.7493 | 0.8046 |
| 0.8–0.9 | 261 | 0.8248 | 0.7395 |
| 0.9–1.0 | 144 | 0.9604 | 0.9861 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 45 | 0.1424 | 0.0444 |
| 0.2–0.3 | 90 | 0.2183 | 0.3444 |
| 0.3–0.4 | 18 | 0.3568 | 0.4444 |
| 0.4–0.5 | 33 | 0.4456 | 0.3333 |
| 0.5–0.6 | 71 | 0.5289 | 0.2676 |
| 0.6–0.7 | 39 | 0.6459 | 0.3333 |
| 0.7–0.8 | 87 | 0.7493 | 0.8046 |
| 0.8–0.9 | 288 | 0.8290 | 0.7569 |
| 0.9–1.0 | 125 | 0.9296 | 0.9840 |
