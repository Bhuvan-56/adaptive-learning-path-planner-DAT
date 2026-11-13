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
| **adaptive_full** | 2.2600 [2.0299, 2.4901] | 0 | 0 | 100.0% | 52 (SCHEDULING_CONSTRAINTS_UNMET:23, CAPACITY_EXCEEDED:29) | 12.777 | 21.657 |
| **static_prerequisite_order** | 2.1650 [1.9250, 2.4001] | 0 | 0 | 100.0% | 0 | 0.541 | 0.889 |
| **non_adaptive_greedy** | 2.1650 [1.9250, 2.4001] | 0 | 0 | 100.0% | 0 | 0.016 | 0.040 |
| **non_adaptive_greedy_best_singleton** | 2.1800 [1.9499, 2.4100] | 0 | 0 | 100.0% | 0 | 0.034 | 0.075 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0950 | [0.0500, 0.1450] | **adaptive_full improves on static_prerequisite_order** [0.0500, 0.1450] |
| **adaptive_full - non_adaptive_greedy** | 0.0950 | [0.0500, 0.1450] | **adaptive_full improves on non_adaptive_greedy** [0.0500, 0.1450] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0150 | [-0.0200, 0.0500] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.5450 [2.3650, 2.7200] | -0.2850 [-0.4000, -0.1650] | ablation_no_diagnostic improves on adaptive_full [0.1650, 0.4000] |
| **ablation_no_replan** | 2.1650 [1.9250, 2.4001] | 0.0950 [0.0500, 0.1450] | adaptive_full improves on ablation_no_replan [0.0500, 0.1450] |
| **ablation_no_difficulty_step** | 2.2600 [2.0299, 2.4901] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.2600 [2.0299, 2.4901] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.2600 [2.0299, 2.4901] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1684 [0.1483, 0.1885] | 0.1063 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1523 [0.1370, 0.1674] | 0.0943 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1683 [0.1483, 0.1885] | 0.1062 | 800 |
| ablation_no_review | 0.1692 [0.1492, 0.1889] | 0.1000 | 800 |
| ablation_no_remediation | 0.1684 [0.1483, 0.1885] | 0.1063 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 6 | 0.0696 | 0.0000 |
| 0.1–0.2 | 50 | 0.1427 | 0.0600 |
| 0.2–0.3 | 82 | 0.2164 | 0.2073 |
| 0.3–0.4 | 27 | 0.3707 | 0.1852 |
| 0.4–0.5 | 57 | 0.4462 | 0.3509 |
| 0.5–0.6 | 50 | 0.5238 | 0.2000 |
| 0.6–0.7 | 46 | 0.6456 | 0.2826 |
| 0.7–0.8 | 102 | 0.7494 | 0.6863 |
| 0.8–0.9 | 242 | 0.8278 | 0.7355 |
| 0.9–1.0 | 138 | 0.9302 | 0.9855 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 45 | 0.1365 | 0.1111 |
| 0.2–0.3 | 13 | 0.2195 | 0.3077 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 40 | 0.4171 | 0.4500 |
| 0.5–0.6 | 235 | 0.5051 | 0.2979 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 81 | 0.7320 | 0.7778 |
| 0.8–0.9 | 44 | 0.8247 | 0.7045 |
| 0.9–1.0 | 342 | 0.9712 | 0.9298 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 6 | 0.0696 | 0.0000 |
| 0.1–0.2 | 50 | 0.1416 | 0.0600 |
| 0.2–0.3 | 82 | 0.2164 | 0.2073 |
| 0.3–0.4 | 27 | 0.3707 | 0.1852 |
| 0.4–0.5 | 57 | 0.4462 | 0.3509 |
| 0.5–0.6 | 50 | 0.5238 | 0.2000 |
| 0.6–0.7 | 46 | 0.6456 | 0.2826 |
| 0.7–0.8 | 102 | 0.7494 | 0.6863 |
| 0.8–0.9 | 242 | 0.8278 | 0.7355 |
| 0.9–1.0 | 138 | 0.9302 | 0.9855 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 6 | 0.0696 | 0.0000 |
| 0.1–0.2 | 50 | 0.1427 | 0.0600 |
| 0.2–0.3 | 82 | 0.2164 | 0.2073 |
| 0.3–0.4 | 27 | 0.3707 | 0.1852 |
| 0.4–0.5 | 57 | 0.4462 | 0.3509 |
| 0.5–0.6 | 55 | 0.5288 | 0.2727 |
| 0.6–0.7 | 50 | 0.6464 | 0.3400 |
| 0.7–0.8 | 103 | 0.7494 | 0.6893 |
| 0.8–0.9 | 221 | 0.8236 | 0.7104 |
| 0.9–1.0 | 149 | 0.9621 | 0.9866 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 6 | 0.0696 | 0.0000 |
| 0.1–0.2 | 50 | 0.1427 | 0.0600 |
| 0.2–0.3 | 82 | 0.2164 | 0.2073 |
| 0.3–0.4 | 27 | 0.3707 | 0.1852 |
| 0.4–0.5 | 57 | 0.4462 | 0.3509 |
| 0.5–0.6 | 50 | 0.5238 | 0.2000 |
| 0.6–0.7 | 46 | 0.6456 | 0.2826 |
| 0.7–0.8 | 102 | 0.7494 | 0.6863 |
| 0.8–0.9 | 242 | 0.8278 | 0.7355 |
| 0.9–1.0 | 138 | 0.9302 | 0.9855 |
