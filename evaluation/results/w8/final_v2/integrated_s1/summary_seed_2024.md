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
| **adaptive_full** | 1.6750 [1.4900, 1.8451] | 0 | 0 | 100.0% | 127 (SCHEDULING_CONSTRAINTS_UNMET:57, CAPACITY_EXCEEDED:70) | 12.363 | 20.079 |
| **static_prerequisite_order** | 1.6150 [1.4249, 1.8050] | 0 | 0 | 100.0% | 0 | 0.546 | 0.805 |
| **non_adaptive_greedy** | 1.5800 [1.4050, 1.7550] | 0 | 0 | 100.0% | 0 | 0.016 | 0.039 |
| **non_adaptive_greedy_best_singleton** | 1.5750 [1.3999, 1.7500] | 0 | 0 | 100.0% | 0 | 0.035 | 0.050 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0600 | [0.0150, 0.1050] | **adaptive_full improves on static_prerequisite_order** [0.0150, 0.1050] |
| **adaptive_full - non_adaptive_greedy** | 0.0950 | [0.0200, 0.1750] | **adaptive_full improves on non_adaptive_greedy** [0.0200, 0.1750] |
| **non_adaptive_greedy - static_prerequisite_order** | -0.0350 | [-0.1050, 0.0300] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0050 | [-0.0350, 0.0250] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 1.7900 [1.5950, 1.9700] | -0.1150 [-0.1950, -0.0350] | ablation_no_diagnostic improves on adaptive_full [0.0350, 0.1950] |
| **ablation_no_replan** | 1.6250 [1.4350, 1.8100] | 0.0500 [0.0100, 0.0900] | adaptive_full improves on ablation_no_replan [0.0100, 0.0900] |
| **ablation_no_difficulty_step** | 1.6750 [1.4900, 1.8451] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.7100 [1.5250, 1.8751] | -0.0350 [-0.0800, 0.0100] | no difference shown |
| **ablation_no_remediation** | 1.6750 [1.4900, 1.8451] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1964 [0.1787, 0.2162] | 0.1457 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1874 [0.1718, 0.2038] | 0.1367 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1964 [0.1787, 0.2162] | 0.1457 | 800 |
| ablation_no_review | 0.1834 [0.1668, 0.2014] | 0.1367 | 800 |
| ablation_no_remediation | 0.1964 [0.1787, 0.2162] | 0.1457 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 107 | 0.1472 | 0.1121 |
| 0.2–0.3 | 121 | 0.2166 | 0.1322 |
| 0.3–0.4 | 36 | 0.3624 | 0.2500 |
| 0.4–0.5 | 47 | 0.4510 | 0.2979 |
| 0.5–0.6 | 69 | 0.5091 | 0.0870 |
| 0.6–0.7 | 25 | 0.6485 | 0.6000 |
| 0.7–0.8 | 68 | 0.7508 | 0.6324 |
| 0.8–0.9 | 188 | 0.8358 | 0.7234 |
| 0.9–1.0 | 123 | 0.9328 | 0.6829 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 143 | 0.1344 | 0.1329 |
| 0.2–0.3 | 26 | 0.2195 | 0.1154 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 68 | 0.4163 | 0.2941 |
| 0.5–0.6 | 241 | 0.5059 | 0.2531 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 67 | 0.7347 | 0.6269 |
| 0.8–0.9 | 33 | 0.8247 | 0.7576 |
| 0.9–1.0 | 222 | 0.9721 | 0.8468 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 107 | 0.1472 | 0.1121 |
| 0.2–0.3 | 121 | 0.2166 | 0.1322 |
| 0.3–0.4 | 36 | 0.3624 | 0.2500 |
| 0.4–0.5 | 47 | 0.4510 | 0.2979 |
| 0.5–0.6 | 69 | 0.5091 | 0.0870 |
| 0.6–0.7 | 25 | 0.6485 | 0.6000 |
| 0.7–0.8 | 68 | 0.7508 | 0.6324 |
| 0.8–0.9 | 188 | 0.8358 | 0.7234 |
| 0.9–1.0 | 123 | 0.9328 | 0.6829 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 107 | 0.1472 | 0.1121 |
| 0.2–0.3 | 121 | 0.2166 | 0.1157 |
| 0.3–0.4 | 36 | 0.3624 | 0.2500 |
| 0.4–0.5 | 47 | 0.4510 | 0.2979 |
| 0.5–0.6 | 76 | 0.5123 | 0.1184 |
| 0.6–0.7 | 32 | 0.6465 | 0.6250 |
| 0.7–0.8 | 73 | 0.7529 | 0.6027 |
| 0.8–0.9 | 161 | 0.8292 | 0.7329 |
| 0.9–1.0 | 131 | 0.9615 | 0.7786 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 16 | 0.0693 | 0.0000 |
| 0.1–0.2 | 107 | 0.1472 | 0.1121 |
| 0.2–0.3 | 121 | 0.2166 | 0.1322 |
| 0.3–0.4 | 36 | 0.3624 | 0.2500 |
| 0.4–0.5 | 47 | 0.4510 | 0.2979 |
| 0.5–0.6 | 69 | 0.5091 | 0.0870 |
| 0.6–0.7 | 25 | 0.6485 | 0.6000 |
| 0.7–0.8 | 68 | 0.7508 | 0.6324 |
| 0.8–0.9 | 188 | 0.8358 | 0.7234 |
| 0.9–1.0 | 123 | 0.9328 | 0.6829 |
