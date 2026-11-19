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
| **adaptive_full** | 2.1750 [1.9700, 2.3851] | 0 | 0 | 100.0% | 152 (SCHEDULING_CONSTRAINTS_UNMET:67, CAPACITY_EXCEEDED:85) | 63.194 | 90.441 |
| **static_prerequisite_order** | 2.0950 [1.8850, 2.3001] | 0 | 0 | 100.0% | 0 | 2.637 | 3.428 |
| **non_adaptive_greedy** | 2.0950 [1.8850, 2.3001] | 0 | 0 | 100.0% | 0 | 0.096 | 0.154 |
| **non_adaptive_greedy_best_singleton** | 2.1100 [1.8950, 2.3251] | 0 | 0 | 100.0% | 0 | 0.196 | 0.288 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0800 | [0.0150, 0.1450] | **adaptive_full improves on static_prerequisite_order** [0.0150, 0.1450] |
| **adaptive_full - non_adaptive_greedy** | 0.0800 | [0.0150, 0.1450] | **adaptive_full improves on non_adaptive_greedy** [0.0150, 0.1450] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0150 | [-0.0350, 0.0700] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.2800 [2.0849, 2.4750] | -0.1050 [-0.1800, -0.0299] | ablation_no_diagnostic improves on adaptive_full [0.0299, 0.1800] |
| **ablation_no_replan** | 2.0950 [1.8850, 2.3001] | 0.0800 [0.0150, 0.1450] | adaptive_full improves on ablation_no_replan [0.0150, 0.1450] |
| **ablation_no_difficulty_step** | 2.1750 [1.9700, 2.3851] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.1750 [1.9700, 2.3851] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.1750 [1.9700, 2.3851] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1582 [0.1422, 0.1741] | 0.1124 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1888 [0.1728, 0.2044] | 0.1200 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1582 [0.1422, 0.1741] | 0.1124 | 800 |
| ablation_no_review | 0.1608 [0.1449, 0.1766] | 0.1090 | 800 |
| ablation_no_remediation | 0.1582 [0.1422, 0.1741] | 0.1124 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0782 | 0.0000 |
| 0.1–0.2 | 142 | 0.1441 | 0.1761 |
| 0.2–0.3 | 123 | 0.2198 | 0.2520 |
| 0.3–0.4 | 44 | 0.3597 | 0.5682 |
| 0.4–0.5 | 55 | 0.4438 | 0.7455 |
| 0.5–0.6 | 89 | 0.5120 | 0.1011 |
| 0.6–0.7 | 28 | 0.6469 | 0.6071 |
| 0.7–0.8 | 46 | 0.7430 | 0.8261 |
| 0.8–0.9 | 151 | 0.8284 | 0.8742 |
| 0.9–1.0 | 118 | 0.9326 | 0.9915 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 202 | 0.1303 | 0.2723 |
| 0.2–0.3 | 29 | 0.2195 | 0.6552 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 71 | 0.4163 | 0.6056 |
| 0.5–0.6 | 226 | 0.5040 | 0.3850 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 57 | 0.7337 | 0.8947 |
| 0.8–0.9 | 56 | 0.8247 | 0.8750 |
| 0.9–1.0 | 159 | 0.9708 | 0.9560 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0782 | 0.0000 |
| 0.1–0.2 | 142 | 0.1441 | 0.1761 |
| 0.2–0.3 | 123 | 0.2198 | 0.2520 |
| 0.3–0.4 | 44 | 0.3597 | 0.5682 |
| 0.4–0.5 | 55 | 0.4438 | 0.7455 |
| 0.5–0.6 | 89 | 0.5120 | 0.1011 |
| 0.6–0.7 | 28 | 0.6469 | 0.6071 |
| 0.7–0.8 | 46 | 0.7430 | 0.8261 |
| 0.8–0.9 | 151 | 0.8284 | 0.8742 |
| 0.9–1.0 | 118 | 0.9326 | 0.9915 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0782 | 0.0000 |
| 0.1–0.2 | 142 | 0.1441 | 0.1761 |
| 0.2–0.3 | 123 | 0.2198 | 0.2520 |
| 0.3–0.4 | 44 | 0.3597 | 0.5682 |
| 0.4–0.5 | 56 | 0.4447 | 0.7500 |
| 0.5–0.6 | 91 | 0.5121 | 0.1209 |
| 0.6–0.7 | 38 | 0.6498 | 0.7105 |
| 0.7–0.8 | 56 | 0.7424 | 0.8571 |
| 0.8–0.9 | 132 | 0.8218 | 0.8561 |
| 0.9–1.0 | 114 | 0.9625 | 0.9912 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0782 | 0.0000 |
| 0.1–0.2 | 142 | 0.1441 | 0.1761 |
| 0.2–0.3 | 123 | 0.2198 | 0.2520 |
| 0.3–0.4 | 44 | 0.3597 | 0.5682 |
| 0.4–0.5 | 55 | 0.4438 | 0.7455 |
| 0.5–0.6 | 89 | 0.5120 | 0.1011 |
| 0.6–0.7 | 28 | 0.6469 | 0.6071 |
| 0.7–0.8 | 46 | 0.7430 | 0.8261 |
| 0.8–0.9 | 151 | 0.8284 | 0.8742 |
| 0.9–1.0 | 118 | 0.9326 | 0.9915 |
