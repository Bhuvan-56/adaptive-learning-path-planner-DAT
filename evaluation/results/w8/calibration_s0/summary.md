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
| **adaptive_full** | 2.0150 [1.7650, 2.2450] | 0 | 0 | 100.0% | 127 (SCHEDULING_CONSTRAINTS_UNMET:59, CAPACITY_EXCEEDED:68) | 14.022 | 29.554 |
| **static_prerequisite_order** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.527 | 0.803 |
| **non_adaptive_greedy** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.015 | 0.021 |
| **non_adaptive_greedy_best_singleton** | 1.9850 [1.7400, 2.2200] | 0 | 0 | 100.0% | 0 | 0.032 | 0.056 |

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
