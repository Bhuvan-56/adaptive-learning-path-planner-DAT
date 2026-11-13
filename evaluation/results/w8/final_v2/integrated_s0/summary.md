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
| **42** | 2.0150 [1.7650, 2.2450] | 1.9700 [1.7299, 2.2050] | 1.9700 [1.7299, 2.2050] | 0.0450 [0.0100, 0.0800] | adaptive_full improves on static_prerequisite_order [0.0100, 0.0800] | 127 |
| **101** | 2.0500 [1.8250, 2.2701] | 1.9700 [1.7450, 2.2050] | 1.9700 [1.7450, 2.2050] | 0.0800 [0.0350, 0.1300] | adaptive_full improves on static_prerequisite_order [0.0350, 0.1300] | 132 |
| **2024** | 2.1600 [1.9449, 2.3750] | 2.1150 [1.8850, 2.3250] | 2.1150 [1.8850, 2.3250] | 0.0450 [0.0099, 0.0800] | adaptive_full improves on static_prerequisite_order [0.0099, 0.0800] | 126 |
| **777** | 1.9150 [1.6949, 2.1401] | 1.8700 [1.6400, 2.1050] | 1.8700 [1.6400, 2.1050] | 0.0450 [0.0150, 0.0850] | adaptive_full improves on static_prerequisite_order [0.0150, 0.0850] | 128 |
| **999** | 2.3200 [2.1150, 2.5400] | 2.2550 [2.0449, 2.4750] | 2.2550 [2.0449, 2.4750] | 0.0650 [0.0300, 0.1050] | adaptive_full improves on static_prerequisite_order [0.0300, 0.1050] | 110 |

## Mastery calibration, pooled over seeds [42, 101, 2024, 777, 999] (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1358 [0.1288, 0.1429] | 0.0821 | 4000 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1462 [0.1401, 0.1526] | 0.0641 | 4000 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1358 [0.1288, 0.1429] | 0.0821 | 4000 |
| ablation_no_review | 0.1364 [0.1295, 0.1435] | 0.0698 | 4000 |
| ablation_no_remediation | 0.1358 [0.1288, 0.1429] | 0.0821 | 4000 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 537 | 0.1445 | 0.0987 |
| 0.2–0.3 | 555 | 0.2203 | 0.1532 |
| 0.3–0.4 | 194 | 0.3593 | 0.3711 |
| 0.4–0.5 | 235 | 0.4455 | 0.3489 |
| 0.5–0.6 | 368 | 0.5100 | 0.0978 |
| 0.6–0.7 | 123 | 0.6505 | 0.5203 |
| 0.7–0.8 | 321 | 0.7488 | 0.7040 |
| 0.8–0.9 | 993 | 0.8320 | 0.8489 |
| 0.9–1.0 | 634 | 0.9325 | 0.9953 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 721 | 0.1321 | 0.1304 |
| 0.2–0.3 | 122 | 0.2195 | 0.2705 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 303 | 0.4166 | 0.3630 |
| 0.5–0.6 | 1150 | 0.5045 | 0.3296 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 271 | 0.7343 | 0.7860 |
| 0.8–0.9 | 193 | 0.8247 | 0.7927 |
| 0.9–1.0 | 1240 | 0.9719 | 0.9629 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 537 | 0.1445 | 0.0987 |
| 0.2–0.3 | 555 | 0.2203 | 0.1532 |
| 0.3–0.4 | 194 | 0.3593 | 0.3711 |
| 0.4–0.5 | 235 | 0.4455 | 0.3489 |
| 0.5–0.6 | 368 | 0.5100 | 0.0978 |
| 0.6–0.7 | 123 | 0.6505 | 0.5203 |
| 0.7–0.8 | 321 | 0.7488 | 0.7040 |
| 0.8–0.9 | 993 | 0.8320 | 0.8489 |
| 0.9–1.0 | 634 | 0.9325 | 0.9953 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 537 | 0.1445 | 0.0987 |
| 0.2–0.3 | 555 | 0.2203 | 0.1532 |
| 0.3–0.4 | 194 | 0.3593 | 0.3711 |
| 0.4–0.5 | 240 | 0.4465 | 0.3625 |
| 0.5–0.6 | 380 | 0.5109 | 0.1211 |
| 0.6–0.7 | 149 | 0.6527 | 0.6040 |
| 0.7–0.8 | 340 | 0.7495 | 0.7206 |
| 0.8–0.9 | 870 | 0.8259 | 0.8322 |
| 0.9–1.0 | 695 | 0.9635 | 0.9942 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 40 | 0.0732 | 0.0000 |
| 0.1–0.2 | 537 | 0.1445 | 0.0987 |
| 0.2–0.3 | 555 | 0.2203 | 0.1532 |
| 0.3–0.4 | 194 | 0.3593 | 0.3711 |
| 0.4–0.5 | 235 | 0.4455 | 0.3489 |
| 0.5–0.6 | 368 | 0.5100 | 0.0978 |
| 0.6–0.7 | 123 | 0.6505 | 0.5203 |
| 0.7–0.8 | 321 | 0.7488 | 0.7040 |
| 0.8–0.9 | 993 | 0.8320 | 0.8489 |
| 0.9–1.0 | 634 | 0.9325 | 0.9953 |

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
| **adaptive_full** | 2.0150 [1.7650, 2.2450] | 0 | 0 | 100.0% | 127 (SCHEDULING_CONSTRAINTS_UNMET:59, CAPACITY_EXCEEDED:68) | 13.682 | 24.136 |
| **static_prerequisite_order** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.555 | 0.834 |
| **non_adaptive_greedy** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.017 | 0.030 |
| **non_adaptive_greedy_best_singleton** | 1.9850 [1.7400, 2.2200] | 0 | 0 | 100.0% | 0 | 0.035 | 0.062 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0450 | [0.0100, 0.0800] | **adaptive_full improves on static_prerequisite_order** [0.0100, 0.0800] |
| **adaptive_full - non_adaptive_greedy** | 0.0450 | [0.0100, 0.0800] | **adaptive_full improves on non_adaptive_greedy** [0.0100, 0.0800] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0150 | [0.0000, 0.0350] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.1300 [1.9146, 2.3350] | -0.1150 [-0.1750, -0.0550] | ablation_no_diagnostic improves on adaptive_full [0.0550, 0.1750] |
| **ablation_no_replan** | 1.9700 [1.7299, 2.2050] | 0.0450 [0.0100, 0.0800] | adaptive_full improves on ablation_no_replan [0.0100, 0.0800] |
| **ablation_no_difficulty_step** | 2.0150 [1.7650, 2.2450] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.0200 [1.7749, 2.2500] | -0.0050 [-0.0200, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.0150 [1.7650, 2.2450] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1364 [0.1208, 0.1529] | 0.0904 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1446 [0.1314, 0.1596] | 0.0763 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1364 [0.1208, 0.1529] | 0.0904 | 800 |
| ablation_no_review | 0.1349 [0.1190, 0.1517] | 0.0834 | 800 |
| ablation_no_remediation | 0.1364 [0.1208, 0.1529] | 0.0904 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 107 | 0.1419 | 0.0935 |
| 0.2–0.3 | 126 | 0.2212 | 0.1508 |
| 0.3–0.4 | 39 | 0.3493 | 0.3333 |
| 0.4–0.5 | 37 | 0.4448 | 0.2162 |
| 0.5–0.6 | 73 | 0.5087 | 0.0411 |
| 0.6–0.7 | 20 | 0.6497 | 0.5000 |
| 0.7–0.8 | 64 | 0.7493 | 0.7031 |
| 0.8–0.9 | 214 | 0.8326 | 0.8364 |
| 0.9–1.0 | 116 | 0.9311 | 1.0000 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 162 | 0.1327 | 0.1481 |
| 0.2–0.3 | 21 | 0.2195 | 0.1905 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 55 | 0.4168 | 0.3636 |
| 0.5–0.6 | 227 | 0.5041 | 0.3040 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 52 | 0.7339 | 0.8269 |
| 0.8–0.9 | 30 | 0.8247 | 0.7333 |
| 0.9–1.0 | 253 | 0.9723 | 0.9644 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 107 | 0.1419 | 0.0935 |
| 0.2–0.3 | 126 | 0.2212 | 0.1508 |
| 0.3–0.4 | 39 | 0.3493 | 0.3333 |
| 0.4–0.5 | 37 | 0.4448 | 0.2162 |
| 0.5–0.6 | 73 | 0.5087 | 0.0411 |
| 0.6–0.7 | 20 | 0.6497 | 0.5000 |
| 0.7–0.8 | 64 | 0.7493 | 0.7031 |
| 0.8–0.9 | 214 | 0.8326 | 0.8364 |
| 0.9–1.0 | 116 | 0.9311 | 1.0000 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 107 | 0.1419 | 0.0935 |
| 0.2–0.3 | 126 | 0.2212 | 0.1508 |
| 0.3–0.4 | 39 | 0.3493 | 0.3333 |
| 0.4–0.5 | 38 | 0.4460 | 0.2368 |
| 0.5–0.6 | 76 | 0.5095 | 0.0526 |
| 0.6–0.7 | 24 | 0.6520 | 0.5833 |
| 0.7–0.8 | 66 | 0.7497 | 0.7121 |
| 0.8–0.9 | 185 | 0.8268 | 0.8324 |
| 0.9–1.0 | 135 | 0.9638 | 0.9926 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 107 | 0.1419 | 0.0935 |
| 0.2–0.3 | 126 | 0.2212 | 0.1508 |
| 0.3–0.4 | 39 | 0.3493 | 0.3333 |
| 0.4–0.5 | 37 | 0.4448 | 0.2162 |
| 0.5–0.6 | 73 | 0.5087 | 0.0411 |
| 0.6–0.7 | 20 | 0.6497 | 0.5000 |
| 0.7–0.8 | 64 | 0.7493 | 0.7031 |
| 0.8–0.9 | 214 | 0.8326 | 0.8364 |
| 0.9–1.0 | 116 | 0.9311 | 1.0000 |
