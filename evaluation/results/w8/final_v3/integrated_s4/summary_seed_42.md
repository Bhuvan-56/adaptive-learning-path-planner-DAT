# Week 5 Integrated Evaluation Summary: Closed-Loop Path Planning

## 1. Evaluation Setup & Input Provenance

- **Benchmark Name:** `w5_integrated`
- **Evaluated Cohort:** 200 synthetic learners (paired random seeds)
- **Planning Horizon:** 5 days
- **Daily Study Budget:** 10 minutes
- **Bootstrap Resamples (B):** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `CalibratedBKTGenerator` (scenario S4: BKT response dynamics with per learner-concept slip/guess/learn drawn from per-skill fits on ASSISTments 2009-2010 students, config/bkt_assistments.yaml)
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
| **adaptive_full** | 2.2000 [1.9650, 2.4151] | 0 | 0 | 100.0% | 150 (SCHEDULING_CONSTRAINTS_UNMET:68, CAPACITY_EXCEEDED:82) | 13.195 | 22.760 |
| **static_prerequisite_order** | 2.1700 [1.9449, 2.3800] | 0 | 0 | 100.0% | 0 | 0.524 | 0.868 |
| **non_adaptive_greedy** | 2.1700 [1.9449, 2.3800] | 0 | 0 | 100.0% | 0 | 0.017 | 0.026 |
| **non_adaptive_greedy_best_singleton** | 2.1500 [1.9299, 2.3601] | 0 | 0 | 100.0% | 0 | 0.054 | 0.194 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0300 | [-0.0300, 0.0900] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0300 | [-0.0300, 0.0900] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0200 | [-0.0650, 0.0250] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.2850 [2.0750, 2.4800] | -0.0850 [-0.1600, -0.0100] | ablation_no_diagnostic improves on adaptive_full [0.0100, 0.1600] |
| **ablation_no_replan** | 2.1700 [1.9449, 2.3800] | 0.0300 [-0.0300, 0.0900] | no difference shown |
| **ablation_no_difficulty_step** | 2.2000 [1.9650, 2.4151] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.2000 [1.9650, 2.4151] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.2000 [1.9650, 2.4151] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under S4 (`CalibratedBKTGenerator`), as under the default simulator, difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Simulated Learner Invariant:** All reported figures are simulator behaviour. S4 learners take their slip/guess/learn parameters from BKT fits on real ASSISTments 2009-2010 students (train split); the learners, curriculum and outcomes are still simulated, not real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1667 [0.1511, 0.1840] | 0.1075 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1864 [0.1704, 0.2029] | 0.1379 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1667 [0.1511, 0.1840] | 0.1075 | 800 |
| ablation_no_review | 0.1689 [0.1530, 0.1858] | 0.1047 | 800 |
| ablation_no_remediation | 0.1667 [0.1511, 0.1840] | 0.1075 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 114 | 0.1404 | 0.2018 |
| 0.2–0.3 | 160 | 0.2231 | 0.3312 |
| 0.3–0.4 | 48 | 0.3544 | 0.5417 |
| 0.4–0.5 | 34 | 0.4450 | 0.3824 |
| 0.5–0.6 | 89 | 0.5117 | 0.1461 |
| 0.6–0.7 | 18 | 0.6419 | 0.6111 |
| 0.7–0.8 | 67 | 0.7464 | 0.7910 |
| 0.8–0.9 | 170 | 0.8346 | 0.8824 |
| 0.9–1.0 | 98 | 0.9364 | 1.0000 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 180 | 0.1309 | 0.2778 |
| 0.2–0.3 | 27 | 0.2195 | 0.6296 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 72 | 0.4163 | 0.5972 |
| 0.5–0.6 | 235 | 0.5051 | 0.3447 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 80 | 0.7307 | 0.8750 |
| 0.8–0.9 | 33 | 0.8247 | 1.0000 |
| 0.9–1.0 | 173 | 0.9696 | 0.9422 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 114 | 0.1404 | 0.2018 |
| 0.2–0.3 | 160 | 0.2231 | 0.3312 |
| 0.3–0.4 | 48 | 0.3544 | 0.5417 |
| 0.4–0.5 | 34 | 0.4450 | 0.3824 |
| 0.5–0.6 | 89 | 0.5117 | 0.1461 |
| 0.6–0.7 | 18 | 0.6419 | 0.6111 |
| 0.7–0.8 | 67 | 0.7464 | 0.7910 |
| 0.8–0.9 | 170 | 0.8346 | 0.8824 |
| 0.9–1.0 | 98 | 0.9364 | 1.0000 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 114 | 0.1404 | 0.2018 |
| 0.2–0.3 | 160 | 0.2231 | 0.3312 |
| 0.3–0.4 | 48 | 0.3544 | 0.5417 |
| 0.4–0.5 | 34 | 0.4450 | 0.3824 |
| 0.5–0.6 | 95 | 0.5144 | 0.1895 |
| 0.6–0.7 | 27 | 0.6461 | 0.7407 |
| 0.7–0.8 | 73 | 0.7473 | 0.8082 |
| 0.8–0.9 | 148 | 0.8290 | 0.8851 |
| 0.9–1.0 | 99 | 0.9594 | 0.9798 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 2 | 0.0776 | 0.0000 |
| 0.1–0.2 | 114 | 0.1404 | 0.2018 |
| 0.2–0.3 | 160 | 0.2231 | 0.3312 |
| 0.3–0.4 | 48 | 0.3544 | 0.5417 |
| 0.4–0.5 | 34 | 0.4450 | 0.3824 |
| 0.5–0.6 | 89 | 0.5117 | 0.1461 |
| 0.6–0.7 | 18 | 0.6419 | 0.6111 |
| 0.7–0.8 | 67 | 0.7464 | 0.7910 |
| 0.8–0.9 | 170 | 0.8346 | 0.8824 |
| 0.9–1.0 | 98 | 0.9364 | 1.0000 |
