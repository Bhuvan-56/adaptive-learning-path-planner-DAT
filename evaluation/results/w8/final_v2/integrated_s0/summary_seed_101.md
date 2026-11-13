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
| **adaptive_full** | 2.0500 [1.8250, 2.2701] | 0 | 0 | 100.0% | 132 (SCHEDULING_CONSTRAINTS_UNMET:57, CAPACITY_EXCEEDED:75) | 14.136 | 24.213 |
| **static_prerequisite_order** | 1.9700 [1.7450, 2.2050] | 0 | 0 | 100.0% | 0 | 0.597 | 1.528 |
| **non_adaptive_greedy** | 1.9700 [1.7450, 2.2050] | 0 | 0 | 100.0% | 0 | 0.017 | 0.043 |
| **non_adaptive_greedy_best_singleton** | 1.9800 [1.7550, 2.2151] | 0 | 0 | 100.0% | 0 | 0.037 | 0.094 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0800 | [0.0350, 0.1300] | **adaptive_full improves on static_prerequisite_order** [0.0350, 0.1300] |
| **adaptive_full - non_adaptive_greedy** | 0.0800 | [0.0350, 0.1300] | **adaptive_full improves on non_adaptive_greedy** [0.0350, 0.1300] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0100 | [-0.0100, 0.0300] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.1600 [1.9500, 2.3650] | -0.1100 [-0.1750, -0.0500] | ablation_no_diagnostic improves on adaptive_full [0.0500, 0.1750] |
| **ablation_no_replan** | 1.9700 [1.7450, 2.2050] | 0.0800 [0.0350, 0.1300] | adaptive_full improves on ablation_no_replan [0.0350, 0.1300] |
| **ablation_no_difficulty_step** | 2.0500 [1.8250, 2.2701] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.0500 [1.8250, 2.2701] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.0500 [1.8250, 2.2701] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1439 [0.1287, 0.1597] | 0.0829 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1550 [0.1414, 0.1697] | 0.0668 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1439 [0.1287, 0.1597] | 0.0829 | 800 |
| ablation_no_review | 0.1449 [0.1301, 0.1604] | 0.0729 | 800 |
| ablation_no_remediation | 0.1439 [0.1287, 0.1597] | 0.0829 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 107 | 0.1465 | 0.1215 |
| 0.2–0.3 | 115 | 0.2203 | 0.1565 |
| 0.3–0.4 | 36 | 0.3660 | 0.3333 |
| 0.4–0.5 | 58 | 0.4396 | 0.4138 |
| 0.5–0.6 | 82 | 0.5138 | 0.0976 |
| 0.6–0.7 | 29 | 0.6551 | 0.5172 |
| 0.7–0.8 | 56 | 0.7454 | 0.6607 |
| 0.8–0.9 | 178 | 0.8292 | 0.8371 |
| 0.9–1.0 | 134 | 0.9334 | 1.0000 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 152 | 0.1331 | 0.1316 |
| 0.2–0.3 | 28 | 0.2195 | 0.4286 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 60 | 0.4167 | 0.3167 |
| 0.5–0.6 | 224 | 0.5037 | 0.3616 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 56 | 0.7344 | 0.7679 |
| 0.8–0.9 | 48 | 0.8247 | 0.7500 |
| 0.9–1.0 | 232 | 0.9703 | 0.9526 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 107 | 0.1465 | 0.1215 |
| 0.2–0.3 | 115 | 0.2203 | 0.1565 |
| 0.3–0.4 | 36 | 0.3660 | 0.3333 |
| 0.4–0.5 | 58 | 0.4396 | 0.4138 |
| 0.5–0.6 | 82 | 0.5138 | 0.0976 |
| 0.6–0.7 | 29 | 0.6551 | 0.5172 |
| 0.7–0.8 | 56 | 0.7454 | 0.6607 |
| 0.8–0.9 | 178 | 0.8292 | 0.8371 |
| 0.9–1.0 | 134 | 0.9334 | 1.0000 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 107 | 0.1465 | 0.1215 |
| 0.2–0.3 | 115 | 0.2203 | 0.1565 |
| 0.3–0.4 | 36 | 0.3660 | 0.3333 |
| 0.4–0.5 | 59 | 0.4406 | 0.4237 |
| 0.5–0.6 | 84 | 0.5141 | 0.1190 |
| 0.6–0.7 | 32 | 0.6541 | 0.5625 |
| 0.7–0.8 | 63 | 0.7460 | 0.6984 |
| 0.8–0.9 | 154 | 0.8216 | 0.8117 |
| 0.9–1.0 | 145 | 0.9649 | 1.0000 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 107 | 0.1465 | 0.1215 |
| 0.2–0.3 | 115 | 0.2203 | 0.1565 |
| 0.3–0.4 | 36 | 0.3660 | 0.3333 |
| 0.4–0.5 | 58 | 0.4396 | 0.4138 |
| 0.5–0.6 | 82 | 0.5138 | 0.0976 |
| 0.6–0.7 | 29 | 0.6551 | 0.5172 |
| 0.7–0.8 | 56 | 0.7454 | 0.6607 |
| 0.8–0.9 | 178 | 0.8292 | 0.8371 |
| 0.9–1.0 | 134 | 0.9334 | 1.0000 |
