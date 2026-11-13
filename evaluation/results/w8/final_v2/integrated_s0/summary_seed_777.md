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
| **adaptive_full** | 1.9150 [1.6949, 2.1401] | 0 | 0 | 100.0% | 128 (SCHEDULING_CONSTRAINTS_UNMET:56, CAPACITY_EXCEEDED:72) | 13.046 | 20.718 |
| **static_prerequisite_order** | 1.8700 [1.6400, 2.1050] | 0 | 0 | 100.0% | 0 | 0.557 | 1.412 |
| **non_adaptive_greedy** | 1.8700 [1.6400, 2.1050] | 0 | 0 | 100.0% | 0 | 0.016 | 0.046 |
| **non_adaptive_greedy_best_singleton** | 1.8950 [1.6650, 2.1250] | 0 | 0 | 100.0% | 0 | 0.034 | 0.086 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0450 | [0.0150, 0.0850] | **adaptive_full improves on static_prerequisite_order** [0.0150, 0.0850] |
| **adaptive_full - non_adaptive_greedy** | 0.0450 | [0.0150, 0.0850] | **adaptive_full improves on non_adaptive_greedy** [0.0150, 0.0850] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0250 | [0.0000, 0.0550] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.0200 [1.8000, 2.2301] | -0.1050 [-0.1700, -0.0450] | ablation_no_diagnostic improves on adaptive_full [0.0450, 0.1700] |
| **ablation_no_replan** | 1.8700 [1.6400, 2.1050] | 0.0450 [0.0150, 0.0850] | adaptive_full improves on ablation_no_replan [0.0150, 0.0850] |
| **ablation_no_difficulty_step** | 1.9150 [1.6949, 2.1401] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.9150 [1.6949, 2.1401] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 1.9150 [1.6949, 2.1401] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1441 [0.1287, 0.1607] | 0.1030 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1441 [0.1317, 0.1574] | 0.0838 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1441 [0.1287, 0.1607] | 0.1030 | 800 |
| ablation_no_review | 0.1445 [0.1288, 0.1614] | 0.0976 | 800 |
| ablation_no_remediation | 0.1441 [0.1287, 0.1607] | 0.1030 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 131 | 0.1444 | 0.0687 |
| 0.2–0.3 | 103 | 0.2221 | 0.1650 |
| 0.3–0.4 | 36 | 0.3614 | 0.3889 |
| 0.4–0.5 | 45 | 0.4401 | 0.2667 |
| 0.5–0.6 | 75 | 0.5098 | 0.0800 |
| 0.6–0.7 | 29 | 0.6409 | 0.5172 |
| 0.7–0.8 | 66 | 0.7476 | 0.7121 |
| 0.8–0.9 | 184 | 0.8285 | 0.7717 |
| 0.9–1.0 | 121 | 0.9298 | 1.0000 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 143 | 0.1311 | 0.0839 |
| 0.2–0.3 | 34 | 0.2195 | 0.2353 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 63 | 0.4168 | 0.3175 |
| 0.5–0.6 | 234 | 0.5050 | 0.3034 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 51 | 0.7359 | 0.6471 |
| 0.8–0.9 | 42 | 0.8247 | 0.8333 |
| 0.9–1.0 | 233 | 0.9720 | 0.9657 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 131 | 0.1444 | 0.0687 |
| 0.2–0.3 | 103 | 0.2221 | 0.1650 |
| 0.3–0.4 | 36 | 0.3614 | 0.3889 |
| 0.4–0.5 | 45 | 0.4401 | 0.2667 |
| 0.5–0.6 | 75 | 0.5098 | 0.0800 |
| 0.6–0.7 | 29 | 0.6409 | 0.5172 |
| 0.7–0.8 | 66 | 0.7476 | 0.7121 |
| 0.8–0.9 | 184 | 0.8285 | 0.7717 |
| 0.9–1.0 | 121 | 0.9298 | 1.0000 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 131 | 0.1444 | 0.0687 |
| 0.2–0.3 | 103 | 0.2221 | 0.1650 |
| 0.3–0.4 | 36 | 0.3614 | 0.3889 |
| 0.4–0.5 | 45 | 0.4401 | 0.2667 |
| 0.5–0.6 | 75 | 0.5098 | 0.0800 |
| 0.6–0.7 | 36 | 0.6436 | 0.6111 |
| 0.7–0.8 | 68 | 0.7483 | 0.7206 |
| 0.8–0.9 | 167 | 0.8238 | 0.7485 |
| 0.9–1.0 | 129 | 0.9621 | 1.0000 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 10 | 0.0740 | 0.0000 |
| 0.1–0.2 | 131 | 0.1444 | 0.0687 |
| 0.2–0.3 | 103 | 0.2221 | 0.1650 |
| 0.3–0.4 | 36 | 0.3614 | 0.3889 |
| 0.4–0.5 | 45 | 0.4401 | 0.2667 |
| 0.5–0.6 | 75 | 0.5098 | 0.0800 |
| 0.6–0.7 | 29 | 0.6409 | 0.5172 |
| 0.7–0.8 | 66 | 0.7476 | 0.7121 |
| 0.8–0.9 | 184 | 0.8285 | 0.7717 |
| 0.9–1.0 | 121 | 0.9298 | 1.0000 |
