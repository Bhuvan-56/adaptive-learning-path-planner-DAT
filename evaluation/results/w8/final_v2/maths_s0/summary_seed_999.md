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
| **adaptive_full** | 6.8050 [6.1346, 7.5150] | 0 | 0 | 100.0% | 1129 (SCHEDULING_CONSTRAINTS_UNMET:468, CAPACITY_EXCEEDED:661) | 74.141 | 99.932 |
| **static_prerequisite_order** | 6.6600 [5.9496, 7.4210] | 0 | 0 | 100.0% | 0 | 2.847 | 4.748 |
| **non_adaptive_greedy** | 6.8000 [6.0899, 7.5402] | 0 | 0 | 100.0% | 0 | 0.063 | 0.134 |
| **non_adaptive_greedy_best_singleton** | 6.9200 [6.2149, 7.6601] | 0 | 0 | 100.0% | 0 | 0.104 | 0.188 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.1450 | [0.0400, 0.2500] | **adaptive_full improves on static_prerequisite_order** [0.0400, 0.2500] |
| **adaptive_full - non_adaptive_greedy** | 0.0050 | [-0.0850, 0.1050] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.1400 | [0.0650, 0.2150] | **non_adaptive_greedy improves on static_prerequisite_order** [0.0650, 0.2150] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.1200 | [0.0749, 0.1700] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0749, 0.1700] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 6.9100 [6.2400, 7.6004] | -0.1050 [-0.1901, -0.0150] | ablation_no_diagnostic improves on adaptive_full [0.0150, 0.1901] |
| **ablation_no_replan** | 6.6550 [5.9496, 7.4207] | 0.1500 [0.0500, 0.2550] | adaptive_full improves on ablation_no_replan [0.0500, 0.2550] |
| **ablation_no_difficulty_step** | 6.8050 [6.1346, 7.5150] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 6.8250 [6.1546, 7.5400] | -0.0200 [-0.0450, 0.0050] | no difference shown |
| **ablation_no_remediation** | 6.8050 [6.1346, 7.5150] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1922 [0.1852, 0.1991] | 0.1552 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1840 [0.1776, 0.1902] | 0.1348 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1922 [0.1852, 0.1991] | 0.1552 | 3200 |
| ablation_no_review | 0.1918 [0.1846, 0.1986] | 0.1530 | 3200 |
| ablation_no_remediation | 0.1922 [0.1852, 0.1991] | 0.1552 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 3 | 0.0737 | 0.0000 |
| 0.1–0.2 | 291 | 0.1383 | 0.1375 |
| 0.2–0.3 | 101 | 0.2245 | 0.3267 |
| 0.3–0.4 | 29 | 0.3593 | 0.4828 |
| 0.4–0.5 | 129 | 0.4256 | 0.4651 |
| 0.5–0.6 | 1718 | 0.5005 | 0.2357 |
| 0.6–0.7 | 27 | 0.6500 | 0.4815 |
| 0.7–0.8 | 195 | 0.7394 | 0.7077 |
| 0.8–0.9 | 246 | 0.8385 | 0.8252 |
| 0.9–1.0 | 461 | 0.9689 | 0.9870 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 272 | 0.1365 | 0.1471 |
| 0.2–0.3 | 262 | 0.2104 | 0.1832 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 120 | 0.4149 | 0.4750 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2487 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 156 | 0.7331 | 0.7179 |
| 0.8–0.9 | 352 | 0.8117 | 0.8324 |
| 0.9–1.0 | 438 | 0.9851 | 0.9909 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 3 | 0.0737 | 0.0000 |
| 0.1–0.2 | 291 | 0.1383 | 0.1375 |
| 0.2–0.3 | 101 | 0.2245 | 0.3267 |
| 0.3–0.4 | 29 | 0.3593 | 0.4828 |
| 0.4–0.5 | 129 | 0.4256 | 0.4651 |
| 0.5–0.6 | 1718 | 0.5005 | 0.2357 |
| 0.6–0.7 | 27 | 0.6500 | 0.4815 |
| 0.7–0.8 | 195 | 0.7394 | 0.7077 |
| 0.8–0.9 | 246 | 0.8385 | 0.8252 |
| 0.9–1.0 | 461 | 0.9689 | 0.9870 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 3 | 0.0737 | 0.0000 |
| 0.1–0.2 | 287 | 0.1381 | 0.1359 |
| 0.2–0.3 | 102 | 0.2241 | 0.3333 |
| 0.3–0.4 | 29 | 0.3593 | 0.4828 |
| 0.4–0.5 | 133 | 0.4253 | 0.4586 |
| 0.5–0.6 | 1720 | 0.5006 | 0.2366 |
| 0.6–0.7 | 33 | 0.6496 | 0.5758 |
| 0.7–0.8 | 197 | 0.7394 | 0.7157 |
| 0.8–0.9 | 230 | 0.8355 | 0.8217 |
| 0.9–1.0 | 466 | 0.9782 | 0.9893 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 3 | 0.0737 | 0.0000 |
| 0.1–0.2 | 291 | 0.1383 | 0.1375 |
| 0.2–0.3 | 101 | 0.2245 | 0.3267 |
| 0.3–0.4 | 29 | 0.3593 | 0.4828 |
| 0.4–0.5 | 129 | 0.4256 | 0.4651 |
| 0.5–0.6 | 1718 | 0.5005 | 0.2357 |
| 0.6–0.7 | 27 | 0.6500 | 0.4815 |
| 0.7–0.8 | 195 | 0.7394 | 0.7077 |
| 0.8–0.9 | 246 | 0.8385 | 0.8252 |
| 0.9–1.0 | 461 | 0.9689 | 0.9870 |
