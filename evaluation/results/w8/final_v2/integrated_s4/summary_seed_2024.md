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
| **adaptive_full** | 2.3400 [2.1400, 2.5400] | 0 | 0 | 100.0% | 143 (SCHEDULING_CONSTRAINTS_UNMET:65, CAPACITY_EXCEEDED:78) | 58.848 | 96.356 |
| **static_prerequisite_order** | 2.2900 [2.0849, 2.5000] | 0 | 0 | 100.0% | 0 | 2.796 | 4.546 |
| **non_adaptive_greedy** | 2.2900 [2.0849, 2.5000] | 0 | 0 | 100.0% | 0 | 0.078 | 0.168 |
| **non_adaptive_greedy_best_singleton** | 2.2650 [2.0499, 2.4650] | 0 | 0 | 100.0% | 0 | 0.154 | 0.327 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0500 | [-0.0050, 0.1050] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0500 | [-0.0050, 0.1050] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0250 | [-0.0700, 0.0150] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.3500 [2.1600, 2.5350] | -0.0100 [-0.0850, 0.0650] | no difference shown |
| **ablation_no_replan** | 2.2850 [2.0799, 2.4950] | 0.0550 [0.0000, 0.1100] | no difference shown |
| **ablation_no_difficulty_step** | 2.3400 [2.1400, 2.5400] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.3400 [2.1400, 2.5400] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.3400 [2.1400, 2.5400] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under S4 (`CalibratedBKTGenerator`), as under the default simulator, difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Simulated Learner Invariant:** All reported figures are simulator behaviour. S4 learners take their slip/guess/learn parameters from BKT fits on real ASSISTments 2009-2010 students (train split); the learners, curriculum and outcomes are still simulated, not real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1557 [0.1406, 0.1729] | 0.1395 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1728 [0.1581, 0.1892] | 0.1259 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1557 [0.1406, 0.1729] | 0.1395 | 800 |
| ablation_no_review | 0.1584 [0.1432, 0.1753] | 0.1329 | 800 |
| ablation_no_remediation | 0.1557 [0.1406, 0.1729] | 0.1395 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 14 | 0.0681 | 0.0000 |
| 0.1–0.2 | 128 | 0.1466 | 0.2578 |
| 0.2–0.3 | 134 | 0.2161 | 0.3134 |
| 0.3–0.4 | 46 | 0.3569 | 0.6087 |
| 0.4–0.5 | 51 | 0.4520 | 0.5686 |
| 0.5–0.6 | 79 | 0.5089 | 0.1266 |
| 0.6–0.7 | 27 | 0.6497 | 0.7037 |
| 0.7–0.8 | 61 | 0.7478 | 0.8689 |
| 0.8–0.9 | 161 | 0.8382 | 0.9689 |
| 0.9–1.0 | 99 | 0.9321 | 0.9899 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 163 | 0.1293 | 0.2209 |
| 0.2–0.3 | 40 | 0.2195 | 0.6000 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 65 | 0.4164 | 0.6615 |
| 0.5–0.6 | 239 | 0.5056 | 0.3640 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 74 | 0.7336 | 0.9459 |
| 0.8–0.9 | 54 | 0.8247 | 0.9074 |
| 0.9–1.0 | 165 | 0.9719 | 0.9758 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 14 | 0.0681 | 0.0000 |
| 0.1–0.2 | 128 | 0.1466 | 0.2578 |
| 0.2–0.3 | 134 | 0.2161 | 0.3134 |
| 0.3–0.4 | 46 | 0.3569 | 0.6087 |
| 0.4–0.5 | 51 | 0.4520 | 0.5686 |
| 0.5–0.6 | 79 | 0.5089 | 0.1266 |
| 0.6–0.7 | 27 | 0.6497 | 0.7037 |
| 0.7–0.8 | 61 | 0.7478 | 0.8689 |
| 0.8–0.9 | 161 | 0.8382 | 0.9689 |
| 0.9–1.0 | 99 | 0.9321 | 0.9899 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 14 | 0.0681 | 0.0000 |
| 0.1–0.2 | 128 | 0.1466 | 0.2578 |
| 0.2–0.3 | 134 | 0.2161 | 0.3134 |
| 0.3–0.4 | 46 | 0.3569 | 0.6087 |
| 0.4–0.5 | 53 | 0.4536 | 0.5849 |
| 0.5–0.6 | 86 | 0.5120 | 0.1977 |
| 0.6–0.7 | 32 | 0.6499 | 0.7500 |
| 0.7–0.8 | 64 | 0.7483 | 0.8750 |
| 0.8–0.9 | 137 | 0.8314 | 0.9635 |
| 0.9–1.0 | 106 | 0.9610 | 0.9906 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 14 | 0.0681 | 0.0000 |
| 0.1–0.2 | 128 | 0.1466 | 0.2578 |
| 0.2–0.3 | 134 | 0.2161 | 0.3134 |
| 0.3–0.4 | 46 | 0.3569 | 0.6087 |
| 0.4–0.5 | 51 | 0.4520 | 0.5686 |
| 0.5–0.6 | 79 | 0.5089 | 0.1266 |
| 0.6–0.7 | 27 | 0.6497 | 0.7037 |
| 0.7–0.8 | 61 | 0.7478 | 0.8689 |
| 0.8–0.9 | 161 | 0.8382 | 0.9689 |
| 0.9–1.0 | 99 | 0.9321 | 0.9899 |
