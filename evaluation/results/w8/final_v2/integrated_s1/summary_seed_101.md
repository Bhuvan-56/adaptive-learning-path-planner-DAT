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
| **adaptive_full** | 1.5700 [1.3948, 1.7550] | 0 | 0 | 100.0% | 135 (SCHEDULING_CONSTRAINTS_UNMET:61, CAPACITY_EXCEEDED:74) | 13.341 | 20.879 |
| **static_prerequisite_order** | 1.4800 [1.2950, 1.6700] | 0 | 0 | 100.0% | 0 | 0.550 | 0.904 |
| **non_adaptive_greedy** | 1.4800 [1.2900, 1.6601] | 0 | 0 | 100.0% | 0 | 0.017 | 0.020 |
| **non_adaptive_greedy_best_singleton** | 1.4650 [1.2800, 1.6450] | 0 | 0 | 100.0% | 0 | 0.034 | 0.080 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0900 | [0.0350, 0.1450] | **adaptive_full improves on static_prerequisite_order** [0.0350, 0.1450] |
| **adaptive_full - non_adaptive_greedy** | 0.0900 | [0.0100, 0.1700] | **adaptive_full improves on non_adaptive_greedy** [0.0100, 0.1700] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [-0.0700, 0.0750] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0150 | [-0.0450, 0.0150] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 1.6700 [1.4950, 1.8500] | -0.1000 [-0.1901, -0.0100] | ablation_no_diagnostic improves on adaptive_full [0.0100, 0.1901] |
| **ablation_no_replan** | 1.4950 [1.3050, 1.6801] | 0.0750 [0.0250, 0.1300] | adaptive_full improves on ablation_no_replan [0.0250, 0.1300] |
| **ablation_no_difficulty_step** | 1.5700 [1.3948, 1.7550] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.6100 [1.4250, 1.7950] | -0.0400 [-0.0750, -0.0050] | ablation_no_review improves on adaptive_full [0.0050, 0.0750] |
| **ablation_no_remediation** | 1.5700 [1.3948, 1.7550] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.2064 [0.1901, 0.2219] | 0.1695 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.2044 [0.1870, 0.2217] | 0.1536 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.2064 [0.1901, 0.2219] | 0.1695 | 800 |
| ablation_no_review | 0.1990 [0.1828, 0.2170] | 0.1610 | 800 |
| ablation_no_remediation | 0.2064 [0.1901, 0.2219] | 0.1695 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 115 | 0.1450 | 0.0957 |
| 0.2–0.3 | 116 | 0.2204 | 0.1034 |
| 0.3–0.4 | 33 | 0.3708 | 0.3030 |
| 0.4–0.5 | 60 | 0.4414 | 0.4500 |
| 0.5–0.6 | 89 | 0.5139 | 0.1461 |
| 0.6–0.7 | 28 | 0.6577 | 0.2500 |
| 0.7–0.8 | 53 | 0.7478 | 0.4906 |
| 0.8–0.9 | 169 | 0.8296 | 0.6331 |
| 0.9–1.0 | 132 | 0.9331 | 0.7652 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 169 | 0.1342 | 0.1361 |
| 0.2–0.3 | 22 | 0.2195 | 0.1364 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 57 | 0.4164 | 0.2807 |
| 0.5–0.6 | 234 | 0.5050 | 0.2735 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 62 | 0.7335 | 0.4839 |
| 0.8–0.9 | 50 | 0.8247 | 0.6200 |
| 0.9–1.0 | 206 | 0.9715 | 0.8107 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 115 | 0.1450 | 0.0957 |
| 0.2–0.3 | 116 | 0.2204 | 0.1034 |
| 0.3–0.4 | 33 | 0.3708 | 0.3030 |
| 0.4–0.5 | 60 | 0.4414 | 0.4500 |
| 0.5–0.6 | 89 | 0.5139 | 0.1461 |
| 0.6–0.7 | 28 | 0.6577 | 0.2500 |
| 0.7–0.8 | 53 | 0.7478 | 0.4906 |
| 0.8–0.9 | 169 | 0.8296 | 0.6331 |
| 0.9–1.0 | 132 | 0.9331 | 0.7652 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 115 | 0.1450 | 0.0957 |
| 0.2–0.3 | 116 | 0.2204 | 0.1121 |
| 0.3–0.4 | 33 | 0.3708 | 0.3030 |
| 0.4–0.5 | 63 | 0.4440 | 0.4762 |
| 0.5–0.6 | 95 | 0.5171 | 0.1474 |
| 0.6–0.7 | 35 | 0.6541 | 0.3143 |
| 0.7–0.8 | 60 | 0.7491 | 0.5000 |
| 0.8–0.9 | 150 | 0.8229 | 0.6533 |
| 0.9–1.0 | 128 | 0.9645 | 0.8203 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0810 | 0.0000 |
| 0.1–0.2 | 115 | 0.1450 | 0.0957 |
| 0.2–0.3 | 116 | 0.2204 | 0.1034 |
| 0.3–0.4 | 33 | 0.3708 | 0.3030 |
| 0.4–0.5 | 60 | 0.4414 | 0.4500 |
| 0.5–0.6 | 89 | 0.5139 | 0.1461 |
| 0.6–0.7 | 28 | 0.6577 | 0.2500 |
| 0.7–0.8 | 53 | 0.7478 | 0.4906 |
| 0.8–0.9 | 169 | 0.8296 | 0.6331 |
| 0.9–1.0 | 132 | 0.9331 | 0.7652 |
