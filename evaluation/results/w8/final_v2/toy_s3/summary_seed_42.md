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
