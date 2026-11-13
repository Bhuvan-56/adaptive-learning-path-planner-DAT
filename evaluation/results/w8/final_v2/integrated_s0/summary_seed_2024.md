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
| **adaptive_full** | 2.1600 [1.9449, 2.3750] | 0 | 0 | 100.0% | 126 (SCHEDULING_CONSTRAINTS_UNMET:56, CAPACITY_EXCEEDED:70) | 14.133 | 40.469 |
| **static_prerequisite_order** | 2.1150 [1.8850, 2.3250] | 0 | 0 | 100.0% | 0 | 0.546 | 1.536 |
| **non_adaptive_greedy** | 2.1150 [1.8850, 2.3250] | 0 | 0 | 100.0% | 0 | 0.016 | 0.033 |
| **non_adaptive_greedy_best_singleton** | 2.1200 [1.8900, 2.3300] | 0 | 0 | 100.0% | 0 | 0.034 | 0.059 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0450 | [0.0099, 0.0800] | **adaptive_full improves on static_prerequisite_order** [0.0099, 0.0800] |
| **adaptive_full - non_adaptive_greedy** | 0.0450 | [0.0099, 0.0800] | **adaptive_full improves on non_adaptive_greedy** [0.0099, 0.0800] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0050 | [-0.0150, 0.0250] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.1850 [1.9800, 2.3850] | -0.0250 [-0.0800, 0.0250] | no difference shown |
| **ablation_no_replan** | 2.1100 [1.8800, 2.3200] | 0.0500 [0.0150, 0.0850] | adaptive_full improves on ablation_no_replan [0.0150, 0.0850] |
| **ablation_no_difficulty_step** | 2.1600 [1.9449, 2.3750] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.1600 [1.9449, 2.3750] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.1600 [1.9449, 2.3750] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1232 [0.1089, 0.1386] | 0.0875 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1362 [0.1238, 0.1492] | 0.0795 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1232 [0.1089, 0.1386] | 0.0875 | 800 |
| ablation_no_review | 0.1242 [0.1102, 0.1395] | 0.0774 | 800 |
| ablation_no_remediation | 0.1232 [0.1089, 0.1386] | 0.0875 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 104 | 0.1468 | 0.1346 |
| 0.2–0.3 | 116 | 0.2159 | 0.1293 |
| 0.3–0.4 | 35 | 0.3590 | 0.3429 |
| 0.4–0.5 | 46 | 0.4489 | 0.3043 |
| 0.5–0.6 | 71 | 0.5090 | 0.1268 |
| 0.6–0.7 | 25 | 0.6551 | 0.6400 |
| 0.7–0.8 | 71 | 0.7507 | 0.7746 |
| 0.8–0.9 | 195 | 0.8357 | 0.9179 |
| 0.9–1.0 | 121 | 0.9328 | 0.9752 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 140 | 0.1309 | 0.1214 |
| 0.2–0.3 | 24 | 0.2195 | 0.1250 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 59 | 0.4163 | 0.3051 |
| 0.5–0.6 | 230 | 0.5045 | 0.3217 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 58 | 0.7318 | 0.8448 |
| 0.8–0.9 | 39 | 0.8247 | 0.8974 |
| 0.9–1.0 | 250 | 0.9720 | 0.9640 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 104 | 0.1468 | 0.1346 |
| 0.2–0.3 | 116 | 0.2159 | 0.1293 |
| 0.3–0.4 | 35 | 0.3590 | 0.3429 |
| 0.4–0.5 | 46 | 0.4489 | 0.3043 |
| 0.5–0.6 | 71 | 0.5090 | 0.1268 |
| 0.6–0.7 | 25 | 0.6551 | 0.6400 |
| 0.7–0.8 | 71 | 0.7507 | 0.7746 |
| 0.8–0.9 | 195 | 0.8357 | 0.9179 |
| 0.9–1.0 | 121 | 0.9328 | 0.9752 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 104 | 0.1468 | 0.1346 |
| 0.2–0.3 | 116 | 0.2159 | 0.1293 |
| 0.3–0.4 | 35 | 0.3590 | 0.3429 |
| 0.4–0.5 | 48 | 0.4509 | 0.3333 |
| 0.5–0.6 | 74 | 0.5106 | 0.1622 |
| 0.6–0.7 | 28 | 0.6550 | 0.6786 |
| 0.7–0.8 | 73 | 0.7517 | 0.7808 |
| 0.8–0.9 | 167 | 0.8290 | 0.9042 |
| 0.9–1.0 | 139 | 0.9629 | 0.9784 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 104 | 0.1468 | 0.1346 |
| 0.2–0.3 | 116 | 0.2159 | 0.1293 |
| 0.3–0.4 | 35 | 0.3590 | 0.3429 |
| 0.4–0.5 | 46 | 0.4489 | 0.3043 |
| 0.5–0.6 | 71 | 0.5090 | 0.1268 |
| 0.6–0.7 | 25 | 0.6551 | 0.6400 |
| 0.7–0.8 | 71 | 0.7507 | 0.7746 |
| 0.8–0.9 | 195 | 0.8357 | 0.9179 |
| 0.9–1.0 | 121 | 0.9328 | 0.9752 |
