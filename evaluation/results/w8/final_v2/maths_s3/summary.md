# Week 5 Integrated Evaluation Summary: Multi-Seed Benchmark

## 1. Multi-Seed Benchmark Setup

- **Benchmark Name:** `w5_integrated_multiseed`
- **Evaluated Seeds (5):** `[42, 101, 2024, 777, 999]`
- **Synthetic Learners per Seed:** 200
- **Total Synthetic Learners Evaluated:** 1000
- **Planning Horizon:** 10 days
- **Daily Study Budget:** 30 minutes
- **Bootstrap Resamples per Seed:** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `MatchedBKTGenerator` (BKT response dynamics)

## 2. Per-Seed Performance Table (Primary Arms)

| Seed | adaptive_full [95% CI] | static_prerequisite_order [95% CI] | non_adaptive_greedy [95% CI] | adaptive minus static [95% CI] | Claim Assessment | No-Plan Days (adaptive) |
|---|---|---|---|---|---|---|
| **42** | 7.4850 [6.8148, 8.1404] | 6.5400 [5.7399, 7.3302] | 6.9600 [6.1299, 7.7850] | 0.9450 [0.7249, 1.1751] | adaptive_full improves on static_prerequisite_order [0.7249, 1.1751] | 1112 |
| **101** | 7.3900 [6.6950, 8.1151] | 6.7600 [5.9948, 7.6151] | 6.9600 [6.1948, 7.7901] | 0.6300 [0.4350, 0.8301] | adaptive_full improves on static_prerequisite_order [0.4350, 0.8301] | 1116 |
| **2024** | 7.5900 [6.8950, 8.2751] | 6.8950 [6.1195, 7.6701] | 7.2650 [6.4700, 8.0854] | 0.6950 [0.4849, 0.8901] | adaptive_full improves on static_prerequisite_order [0.4849, 0.8901] | 1113 |
| **777** | 6.9950 [6.3149, 7.7101] | 6.3000 [5.5143, 7.1202] | 6.6000 [5.8048, 7.4052] | 0.6950 [0.4699, 0.9100] | adaptive_full improves on static_prerequisite_order [0.4699, 0.9100] | 1133 |
| **999** | 8.0550 [7.4149, 8.7203] | 7.3850 [6.6250, 8.1902] | 7.7050 [6.9349, 8.5200] | 0.6700 [0.4350, 0.9150] | adaptive_full improves on static_prerequisite_order [0.4350, 0.9150] | 1091 |

## Mastery calibration, pooled over seeds [42, 101, 2024, 777, 999] (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1881 [0.1846, 0.1918] | 0.1550 | 16000 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1914 [0.1877, 0.1950] | 0.1563 | 16000 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1870 [0.1837, 0.1907] | 0.1565 | 16000 |
| ablation_no_review | 0.1881 [0.1846, 0.1918] | 0.1556 | 16000 |
| ablation_no_remediation | 0.1881 [0.1846, 0.1918] | 0.1550 | 16000 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 11 | 0.0711 | 0.0000 |
| 0.1–0.2 | 660 | 0.1427 | 0.1333 |
| 0.2–0.3 | 405 | 0.2240 | 0.3580 |
| 0.3–0.4 | 91 | 0.3647 | 0.3297 |
| 0.4–0.5 | 535 | 0.4283 | 0.3215 |
| 0.5–0.6 | 8328 | 0.5011 | 0.2275 |
| 0.6–0.7 | 241 | 0.6514 | 0.4979 |
| 0.7–0.8 | 1342 | 0.7405 | 0.7504 |
| 0.8–0.9 | 1438 | 0.8357 | 0.8387 |
| 0.9–1.0 | 2949 | 0.9714 | 0.9630 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 449 | 0.1416 | 0.1359 |
| 0.2–0.3 | 834 | 0.2104 | 0.2518 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 355 | 0.4149 | 0.2873 |
| 0.5–0.6 | 8000 | 0.5000 | 0.2321 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 1073 | 0.7359 | 0.7474 |
| 0.8–0.9 | 2263 | 0.8117 | 0.7185 |
| 0.9–1.0 | 3026 | 0.9851 | 0.9679 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 11 | 0.0717 | 0.0000 |
| 0.1–0.2 | 707 | 0.1423 | 0.1301 |
| 0.2–0.3 | 408 | 0.2240 | 0.3627 |
| 0.3–0.4 | 92 | 0.3650 | 0.3370 |
| 0.4–0.5 | 523 | 0.4280 | 0.3346 |
| 0.5–0.6 | 8337 | 0.5011 | 0.2273 |
| 0.6–0.7 | 242 | 0.6513 | 0.4959 |
| 0.7–0.8 | 1288 | 0.7410 | 0.7562 |
| 0.8–0.9 | 1406 | 0.8359 | 0.8492 |
| 0.9–1.0 | 2986 | 0.9716 | 0.9622 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 11 | 0.0711 | 0.0000 |
| 0.1–0.2 | 663 | 0.1427 | 0.1388 |
| 0.2–0.3 | 402 | 0.2240 | 0.3483 |
| 0.3–0.4 | 91 | 0.3647 | 0.3297 |
| 0.4–0.5 | 538 | 0.4286 | 0.3290 |
| 0.5–0.6 | 8335 | 0.5012 | 0.2282 |
| 0.6–0.7 | 248 | 0.6507 | 0.5121 |
| 0.7–0.8 | 1357 | 0.7406 | 0.7531 |
| 0.8–0.9 | 1329 | 0.8329 | 0.8262 |
| 0.9–1.0 | 3026 | 0.9786 | 0.9640 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 11 | 0.0711 | 0.0000 |
| 0.1–0.2 | 660 | 0.1427 | 0.1333 |
| 0.2–0.3 | 405 | 0.2240 | 0.3580 |
| 0.3–0.4 | 91 | 0.3647 | 0.3297 |
| 0.4–0.5 | 535 | 0.4283 | 0.3215 |
| 0.5–0.6 | 8328 | 0.5011 | 0.2275 |
| 0.6–0.7 | 241 | 0.6514 | 0.4979 |
| 0.7–0.8 | 1342 | 0.7405 | 0.7504 |
| 0.8–0.9 | 1438 | 0.8357 | 0.8387 |
| 0.9–1.0 | 2949 | 0.9714 | 0.9630 |

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
| **adaptive_full** | 7.4850 [6.8148, 8.1404] | 0 | 0 | 100.0% | 1112 (SCHEDULING_CONSTRAINTS_UNMET:484, CAPACITY_EXCEEDED:628) | 71.555 | 96.673 |
| **static_prerequisite_order** | 6.5400 [5.7399, 7.3302] | 0 | 0 | 100.0% | 0 | 2.801 | 5.283 |
| **non_adaptive_greedy** | 6.9600 [6.1299, 7.7850] | 0 | 0 | 100.0% | 0 | 0.059 | 0.111 |
| **non_adaptive_greedy_best_singleton** | 7.0450 [6.2000, 7.8750] | 0 | 0 | 100.0% | 0 | 0.101 | 0.286 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.9450 | [0.7249, 1.1751] | **adaptive_full improves on static_prerequisite_order** [0.7249, 1.1751] |
| **adaptive_full - non_adaptive_greedy** | 0.5250 | [0.2899, 0.7851] | **adaptive_full improves on non_adaptive_greedy** [0.2899, 0.7851] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.4200 | [0.2999, 0.5550] | **non_adaptive_greedy improves on static_prerequisite_order** [0.2999, 0.5550] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0850 | [0.0350, 0.1350] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0350, 0.1350] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 7.5350 [6.9149, 8.1950] | -0.0500 [-0.1651, 0.0650] | no difference shown |
| **ablation_no_replan** | 6.5400 [5.7400, 7.3351] | 0.9450 [0.7300, 1.1750] | adaptive_full improves on ablation_no_replan [0.7300, 1.1750] |
| **ablation_no_difficulty_step** | 7.4850 [6.8148, 8.1404] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 7.4850 [6.8098, 8.1454] | 0.0000 [-0.0150, 0.0150] | no difference shown |
| **ablation_no_remediation** | 7.4850 [6.8148, 8.1404] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1847 [0.1778, 0.1926] | 0.1676 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1904 [0.1830, 0.1988] | 0.1634 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1840 [0.1771, 0.1916] | 0.1676 | 3200 |
| ablation_no_review | 0.1845 [0.1778, 0.1924] | 0.1675 | 3200 |
| ablation_no_remediation | 0.1847 [0.1778, 0.1926] | 0.1676 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 123 | 0.1508 | 0.1138 |
| 0.2–0.3 | 92 | 0.2226 | 0.3478 |
| 0.3–0.4 | 14 | 0.3580 | 0.4286 |
| 0.4–0.5 | 101 | 0.4291 | 0.3564 |
| 0.5–0.6 | 1664 | 0.5009 | 0.2091 |
| 0.6–0.7 | 35 | 0.6436 | 0.4286 |
| 0.7–0.8 | 271 | 0.7400 | 0.7786 |
| 0.8–0.9 | 315 | 0.8358 | 0.8571 |
| 0.9–1.0 | 583 | 0.9720 | 0.9691 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 71 | 0.1461 | 0.1408 |
| 0.2–0.3 | 180 | 0.2108 | 0.2667 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 78 | 0.4149 | 0.3462 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2137 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 187 | 0.7361 | 0.7487 |
| 0.8–0.9 | 470 | 0.8123 | 0.7277 |
| 0.9–1.0 | 614 | 0.9851 | 0.9739 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 133 | 0.1489 | 0.1053 |
| 0.2–0.3 | 91 | 0.2230 | 0.3736 |
| 0.3–0.4 | 14 | 0.3580 | 0.4286 |
| 0.4–0.5 | 96 | 0.4304 | 0.3750 |
| 0.5–0.6 | 1665 | 0.5009 | 0.2090 |
| 0.6–0.7 | 35 | 0.6436 | 0.4286 |
| 0.7–0.8 | 256 | 0.7411 | 0.7734 |
| 0.8–0.9 | 312 | 0.8359 | 0.8590 |
| 0.9–1.0 | 596 | 0.9722 | 0.9698 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 122 | 0.1506 | 0.1148 |
| 0.2–0.3 | 93 | 0.2226 | 0.3441 |
| 0.3–0.4 | 14 | 0.3580 | 0.4286 |
| 0.4–0.5 | 101 | 0.4299 | 0.3564 |
| 0.5–0.6 | 1666 | 0.5010 | 0.2101 |
| 0.6–0.7 | 35 | 0.6436 | 0.4286 |
| 0.7–0.8 | 275 | 0.7405 | 0.7782 |
| 0.8–0.9 | 289 | 0.8336 | 0.8478 |
| 0.9–1.0 | 603 | 0.9786 | 0.9701 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 123 | 0.1508 | 0.1138 |
| 0.2–0.3 | 92 | 0.2226 | 0.3478 |
| 0.3–0.4 | 14 | 0.3580 | 0.4286 |
| 0.4–0.5 | 101 | 0.4291 | 0.3564 |
| 0.5–0.6 | 1664 | 0.5009 | 0.2091 |
| 0.6–0.7 | 35 | 0.6436 | 0.4286 |
| 0.7–0.8 | 271 | 0.7400 | 0.7786 |
| 0.8–0.9 | 315 | 0.8358 | 0.8571 |
| 0.9–1.0 | 583 | 0.9720 | 0.9691 |
