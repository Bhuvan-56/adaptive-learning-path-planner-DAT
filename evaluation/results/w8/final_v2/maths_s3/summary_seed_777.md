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
| **adaptive_full** | 6.9950 [6.3149, 7.7101] | 0 | 0 | 100.0% | 1133 (SCHEDULING_CONSTRAINTS_UNMET:500, CAPACITY_EXCEEDED:633) | 73.752 | 92.157 |
| **static_prerequisite_order** | 6.3000 [5.5143, 7.1202] | 0 | 0 | 100.0% | 0 | 2.833 | 4.175 |
| **non_adaptive_greedy** | 6.6000 [5.8048, 7.4052] | 0 | 0 | 100.0% | 0 | 0.063 | 0.093 |
| **non_adaptive_greedy_best_singleton** | 6.6950 [5.8849, 7.5351] | 0 | 0 | 100.0% | 0 | 0.107 | 0.178 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.6950 | [0.4699, 0.9100] | **adaptive_full improves on static_prerequisite_order** [0.4699, 0.9100] |
| **adaptive_full - non_adaptive_greedy** | 0.3950 | [0.1700, 0.6050] | **adaptive_full improves on non_adaptive_greedy** [0.1700, 0.6050] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.3000 | [0.1650, 0.4450] | **non_adaptive_greedy improves on static_prerequisite_order** [0.1650, 0.4450] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0950 | [0.0400, 0.1500] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0400, 0.1500] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 7.0650 [6.4099, 7.7552] | -0.0700 [-0.1851, 0.0400] | no difference shown |
| **ablation_no_replan** | 6.3050 [5.5143, 7.1252] | 0.6900 [0.4650, 0.9050] | adaptive_full improves on ablation_no_replan [0.4650, 0.9050] |
| **ablation_no_difficulty_step** | 7.0000 [6.3199, 7.7100] | -0.0050 [-0.0300, 0.0200] | no difference shown |
| **ablation_no_review** | 6.9950 [6.3149, 7.7101] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 6.9950 [6.3149, 7.7101] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1920 [0.1838, 0.2002] | 0.1730 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1960 [0.1875, 0.2048] | 0.1783 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1895 [0.1817, 0.1974] | 0.1729 | 3200 |
| ablation_no_review | 0.1921 [0.1841, 0.2003] | 0.1744 | 3200 |
| ablation_no_remediation | 0.1920 [0.1838, 0.2002] | 0.1730 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0647 | 0.0000 |
| 0.1–0.2 | 156 | 0.1406 | 0.1026 |
| 0.2–0.3 | 85 | 0.2249 | 0.3176 |
| 0.3–0.4 | 30 | 0.3738 | 0.2333 |
| 0.4–0.5 | 109 | 0.4294 | 0.3028 |
| 0.5–0.6 | 1660 | 0.5011 | 0.2060 |
| 0.6–0.7 | 50 | 0.6466 | 0.3800 |
| 0.7–0.8 | 290 | 0.7412 | 0.7310 |
| 0.8–0.9 | 260 | 0.8343 | 0.8077 |
| 0.9–1.0 | 558 | 0.9705 | 0.9552 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 103 | 0.1384 | 0.0583 |
| 0.2–0.3 | 161 | 0.2101 | 0.1863 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 75 | 0.4149 | 0.2800 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2100 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 234 | 0.7353 | 0.7137 |
| 0.8–0.9 | 459 | 0.8119 | 0.6667 |
| 0.9–1.0 | 568 | 0.9851 | 0.9630 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0647 | 0.0000 |
| 0.1–0.2 | 166 | 0.1417 | 0.0964 |
| 0.2–0.3 | 86 | 0.2248 | 0.3140 |
| 0.3–0.4 | 30 | 0.3738 | 0.2333 |
| 0.4–0.5 | 109 | 0.4291 | 0.3119 |
| 0.5–0.6 | 1665 | 0.5010 | 0.2054 |
| 0.6–0.7 | 50 | 0.6466 | 0.3800 |
| 0.7–0.8 | 274 | 0.7416 | 0.7555 |
| 0.8–0.9 | 253 | 0.8347 | 0.8261 |
| 0.9–1.0 | 565 | 0.9706 | 0.9540 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0647 | 0.0000 |
| 0.1–0.2 | 158 | 0.1408 | 0.1076 |
| 0.2–0.3 | 86 | 0.2246 | 0.3256 |
| 0.3–0.4 | 30 | 0.3738 | 0.2333 |
| 0.4–0.5 | 106 | 0.4305 | 0.2925 |
| 0.5–0.6 | 1662 | 0.5011 | 0.2070 |
| 0.6–0.7 | 53 | 0.6470 | 0.4151 |
| 0.7–0.8 | 289 | 0.7412 | 0.7301 |
| 0.8–0.9 | 246 | 0.8319 | 0.7967 |
| 0.9–1.0 | 568 | 0.9774 | 0.9560 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0647 | 0.0000 |
| 0.1–0.2 | 156 | 0.1406 | 0.1026 |
| 0.2–0.3 | 85 | 0.2249 | 0.3176 |
| 0.3–0.4 | 30 | 0.3738 | 0.2333 |
| 0.4–0.5 | 109 | 0.4294 | 0.3028 |
| 0.5–0.6 | 1660 | 0.5011 | 0.2060 |
| 0.6–0.7 | 50 | 0.6466 | 0.3800 |
| 0.7–0.8 | 290 | 0.7412 | 0.7310 |
| 0.8–0.9 | 260 | 0.8343 | 0.8077 |
| 0.9–1.0 | 558 | 0.9705 | 0.9552 |
