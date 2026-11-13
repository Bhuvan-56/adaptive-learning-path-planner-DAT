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
| **adaptive_full** | 6.0600 [5.3149, 6.7605] | 0 | 0 | 100.0% | 1147 (SCHEDULING_CONSTRAINTS_UNMET:473, CAPACITY_EXCEEDED:674) | 78.327 | 134.056 |
| **static_prerequisite_order** | 6.0650 [5.2898, 6.8001] | 0 | 0 | 100.0% | 0 | 2.774 | 3.792 |
| **non_adaptive_greedy** | 6.1600 [5.4100, 6.8659] | 0 | 0 | 100.0% | 0 | 0.061 | 0.150 |
| **non_adaptive_greedy_best_singleton** | 6.2100 [5.4600, 6.9259] | 0 | 0 | 100.0% | 0 | 0.101 | 0.241 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | -0.0050 | [-0.1000, 0.0950] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | -0.1000 | [-0.2100, 0.0150] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0950 | [0.0100, 0.1750] | **non_adaptive_greedy improves on static_prerequisite_order** [0.0100, 0.1750] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0500 | [0.0050, 0.0950] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0050, 0.0950] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 6.2600 [5.5249, 6.9400] | -0.2000 [-0.3100, -0.1050] | ablation_no_diagnostic improves on adaptive_full [0.1050, 0.3100] |
| **ablation_no_replan** | 6.0550 [5.2796, 6.7805] | 0.0050 [-0.0901, 0.1050] | no difference shown |
| **ablation_no_difficulty_step** | 6.0600 [5.3149, 6.7605] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 6.0600 [5.2999, 6.7651] | 0.0000 [-0.0250, 0.0300] | no difference shown |
| **ablation_no_remediation** | 6.0600 [5.3149, 6.7605] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1872 [0.1803, 0.1943] | 0.1789 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1856 [0.1785, 0.1929] | 0.1562 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1872 [0.1803, 0.1943] | 0.1789 | 3200 |
| ablation_no_review | 0.1867 [0.1800, 0.1935] | 0.1779 | 3200 |
| ablation_no_remediation | 0.1872 [0.1803, 0.1943] | 0.1789 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 328 | 0.1388 | 0.0945 |
| 0.2–0.3 | 120 | 0.2230 | 0.2000 |
| 0.3–0.4 | 24 | 0.3594 | 0.5000 |
| 0.4–0.5 | 116 | 0.4244 | 0.3534 |
| 0.5–0.6 | 1738 | 0.5006 | 0.1985 |
| 0.6–0.7 | 15 | 0.6500 | 0.4000 |
| 0.7–0.8 | 188 | 0.7390 | 0.7074 |
| 0.8–0.9 | 259 | 0.8369 | 0.8378 |
| 0.9–1.0 | 408 | 0.9680 | 0.9877 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 309 | 0.1323 | 0.1230 |
| 0.2–0.3 | 262 | 0.2103 | 0.1527 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 111 | 0.4149 | 0.4144 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2137 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 151 | 0.7333 | 0.6623 |
| 0.8–0.9 | 351 | 0.8118 | 0.7806 |
| 0.9–1.0 | 416 | 0.9851 | 0.9904 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 328 | 0.1388 | 0.0945 |
| 0.2–0.3 | 120 | 0.2230 | 0.2000 |
| 0.3–0.4 | 24 | 0.3594 | 0.5000 |
| 0.4–0.5 | 116 | 0.4244 | 0.3534 |
| 0.5–0.6 | 1738 | 0.5006 | 0.1985 |
| 0.6–0.7 | 15 | 0.6500 | 0.4000 |
| 0.7–0.8 | 188 | 0.7390 | 0.7074 |
| 0.8–0.9 | 259 | 0.8369 | 0.8378 |
| 0.9–1.0 | 408 | 0.9680 | 0.9877 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 331 | 0.1384 | 0.0997 |
| 0.2–0.3 | 122 | 0.2231 | 0.1967 |
| 0.3–0.4 | 24 | 0.3594 | 0.5000 |
| 0.4–0.5 | 113 | 0.4247 | 0.3363 |
| 0.5–0.6 | 1742 | 0.5007 | 0.1998 |
| 0.6–0.7 | 20 | 0.6527 | 0.5500 |
| 0.7–0.8 | 191 | 0.7393 | 0.7068 |
| 0.8–0.9 | 239 | 0.8342 | 0.8410 |
| 0.9–1.0 | 414 | 0.9775 | 0.9903 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 4 | 0.0764 | 0.0000 |
| 0.1–0.2 | 328 | 0.1388 | 0.0945 |
| 0.2–0.3 | 120 | 0.2230 | 0.2000 |
| 0.3–0.4 | 24 | 0.3594 | 0.5000 |
| 0.4–0.5 | 116 | 0.4244 | 0.3534 |
| 0.5–0.6 | 1738 | 0.5006 | 0.1985 |
| 0.6–0.7 | 15 | 0.6500 | 0.4000 |
| 0.7–0.8 | 188 | 0.7390 | 0.7074 |
| 0.8–0.9 | 259 | 0.8369 | 0.8378 |
| 0.9–1.0 | 408 | 0.9680 | 0.9877 |
