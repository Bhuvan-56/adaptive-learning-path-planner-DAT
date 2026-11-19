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
| **adaptive_full** | 2.4000 [2.1850, 2.6150] | 0 | 0 | 100.0% | 129 (SCHEDULING_CONSTRAINTS_UNMET:66, CAPACITY_EXCEEDED:63) | 62.718 | 84.876 |
| **static_prerequisite_order** | 2.3500 [2.1350, 2.5651] | 0 | 0 | 100.0% | 0 | 2.562 | 3.410 |
| **non_adaptive_greedy** | 2.3500 [2.1350, 2.5651] | 0 | 0 | 100.0% | 0 | 0.094 | 0.147 |
| **non_adaptive_greedy_best_singleton** | 2.3800 [2.1649, 2.6000] | 0 | 0 | 100.0% | 0 | 0.193 | 0.265 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0500 | [-0.0050, 0.1100] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0500 | [-0.0050, 0.1100] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0300 | [-0.0150, 0.0750] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.4850 [2.2950, 2.6850] | -0.0850 [-0.1600, -0.0200] | ablation_no_diagnostic improves on adaptive_full [0.0200, 0.1600] |
| **ablation_no_replan** | 2.3500 [2.1350, 2.5651] | 0.0500 [-0.0050, 0.1100] | no difference shown |
| **ablation_no_difficulty_step** | 2.4000 [2.1850, 2.6150] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.4000 [2.1850, 2.6150] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.4000 [2.1850, 2.6150] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1536 [0.1392, 0.1673] | 0.1040 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1860 [0.1710, 0.2010] | 0.1279 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1536 [0.1392, 0.1673] | 0.1040 | 800 |
| ablation_no_review | 0.1576 [0.1437, 0.1711] | 0.1011 | 800 |
| ablation_no_remediation | 0.1536 [0.1392, 0.1673] | 0.1040 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 110 | 0.1412 | 0.1909 |
| 0.2–0.3 | 112 | 0.2275 | 0.3482 |
| 0.3–0.4 | 53 | 0.3655 | 0.5283 |
| 0.4–0.5 | 56 | 0.4525 | 0.5536 |
| 0.5–0.6 | 86 | 0.5103 | 0.2093 |
| 0.6–0.7 | 17 | 0.6456 | 0.7059 |
| 0.7–0.8 | 51 | 0.7484 | 0.7451 |
| 0.8–0.9 | 187 | 0.8319 | 0.9091 |
| 0.9–1.0 | 123 | 0.9348 | 1.0000 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 161 | 0.1318 | 0.3168 |
| 0.2–0.3 | 19 | 0.2195 | 0.6842 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 81 | 0.4166 | 0.6790 |
| 0.5–0.6 | 244 | 0.5062 | 0.4057 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 68 | 0.7309 | 0.9412 |
| 0.8–0.9 | 42 | 0.8247 | 0.7857 |
| 0.9–1.0 | 185 | 0.9731 | 0.9838 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 110 | 0.1412 | 0.1909 |
| 0.2–0.3 | 112 | 0.2275 | 0.3482 |
| 0.3–0.4 | 53 | 0.3655 | 0.5283 |
| 0.4–0.5 | 56 | 0.4525 | 0.5536 |
| 0.5–0.6 | 86 | 0.5103 | 0.2093 |
| 0.6–0.7 | 17 | 0.6456 | 0.7059 |
| 0.7–0.8 | 51 | 0.7484 | 0.7451 |
| 0.8–0.9 | 187 | 0.8319 | 0.9091 |
| 0.9–1.0 | 123 | 0.9348 | 1.0000 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 110 | 0.1412 | 0.1909 |
| 0.2–0.3 | 112 | 0.2275 | 0.3482 |
| 0.3–0.4 | 53 | 0.3655 | 0.5283 |
| 0.4–0.5 | 57 | 0.4533 | 0.5614 |
| 0.5–0.6 | 93 | 0.5130 | 0.2688 |
| 0.6–0.7 | 32 | 0.6554 | 0.8438 |
| 0.7–0.8 | 58 | 0.7501 | 0.7759 |
| 0.8–0.9 | 169 | 0.8273 | 0.8994 |
| 0.9–1.0 | 111 | 0.9609 | 1.0000 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0737 | 0.0000 |
| 0.1–0.2 | 110 | 0.1412 | 0.1909 |
| 0.2–0.3 | 112 | 0.2275 | 0.3482 |
| 0.3–0.4 | 53 | 0.3655 | 0.5283 |
| 0.4–0.5 | 56 | 0.4525 | 0.5536 |
| 0.5–0.6 | 86 | 0.5103 | 0.2093 |
| 0.6–0.7 | 17 | 0.6456 | 0.7059 |
| 0.7–0.8 | 51 | 0.7484 | 0.7451 |
| 0.8–0.9 | 187 | 0.8319 | 0.9091 |
| 0.9–1.0 | 123 | 0.9348 | 1.0000 |
