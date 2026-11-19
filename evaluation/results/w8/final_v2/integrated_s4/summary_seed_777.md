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
| **adaptive_full** | 2.1200 [1.9200, 2.3250] | 0 | 0 | 100.0% | 160 (SCHEDULING_CONSTRAINTS_UNMET:75, CAPACITY_EXCEEDED:85) | 55.471 | 90.046 |
| **static_prerequisite_order** | 2.0550 [1.8350, 2.2700] | 0 | 0 | 100.0% | 0 | 1.961 | 3.539 |
| **non_adaptive_greedy** | 2.0550 [1.8350, 2.2700] | 0 | 0 | 100.0% | 0 | 0.068 | 0.133 |
| **non_adaptive_greedy_best_singleton** | 2.0400 [1.8250, 2.2601] | 0 | 0 | 100.0% | 0 | 0.146 | 0.277 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0650 | [0.0000, 0.1301] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0650 | [0.0000, 0.1301] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0150 | [-0.0700, 0.0350] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 2.1800 [1.9800, 2.3750] | -0.0600 [-0.1451, 0.0250] | no difference shown |
| **ablation_no_replan** | 2.0550 [1.8350, 2.2700] | 0.0650 [0.0000, 0.1301] | no difference shown |
| **ablation_no_difficulty_step** | 2.1200 [1.9200, 2.3250] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 2.1200 [1.9200, 2.3250] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 2.1200 [1.9200, 2.3250] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under S4 (`CalibratedBKTGenerator`), as under the default simulator, difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Simulated Learner Invariant:** All reported figures are simulator behaviour. S4 learners take their slip/guess/learn parameters from BKT fits on real ASSISTments 2009-2010 students (train split); the learners, curriculum and outcomes are still simulated, not real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1692 [0.1525, 0.1863] | 0.1149 | 800 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1748 [0.1604, 0.1894] | 0.1211 | 800 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1692 [0.1525, 0.1863] | 0.1149 | 800 |
| ablation_no_review | 0.1710 [0.1548, 0.1882] | 0.1077 | 800 |
| ablation_no_remediation | 0.1692 [0.1525, 0.1863] | 0.1149 | 800 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0744 | 0.0000 |
| 0.1–0.2 | 153 | 0.1410 | 0.1961 |
| 0.2–0.3 | 118 | 0.2209 | 0.3390 |
| 0.3–0.4 | 49 | 0.3626 | 0.6122 |
| 0.4–0.5 | 51 | 0.4487 | 0.5098 |
| 0.5–0.6 | 93 | 0.5089 | 0.1290 |
| 0.6–0.7 | 25 | 0.6410 | 0.5200 |
| 0.7–0.8 | 56 | 0.7466 | 0.8036 |
| 0.8–0.9 | 141 | 0.8325 | 0.8652 |
| 0.9–1.0 | 106 | 0.9296 | 1.0000 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 187 | 0.1292 | 0.2193 |
| 0.2–0.3 | 37 | 0.2195 | 0.4595 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 65 | 0.4164 | 0.6615 |
| 0.5–0.6 | 231 | 0.5046 | 0.3290 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 71 | 0.7355 | 0.8169 |
| 0.8–0.9 | 44 | 0.8247 | 0.9773 |
| 0.9–1.0 | 165 | 0.9706 | 0.9576 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0744 | 0.0000 |
| 0.1–0.2 | 153 | 0.1410 | 0.1961 |
| 0.2–0.3 | 118 | 0.2209 | 0.3390 |
| 0.3–0.4 | 49 | 0.3626 | 0.6122 |
| 0.4–0.5 | 51 | 0.4487 | 0.5098 |
| 0.5–0.6 | 93 | 0.5089 | 0.1290 |
| 0.6–0.7 | 25 | 0.6410 | 0.5200 |
| 0.7–0.8 | 56 | 0.7466 | 0.8036 |
| 0.8–0.9 | 141 | 0.8325 | 0.8652 |
| 0.9–1.0 | 106 | 0.9296 | 1.0000 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0744 | 0.0000 |
| 0.1–0.2 | 153 | 0.1410 | 0.1961 |
| 0.2–0.3 | 118 | 0.2209 | 0.3390 |
| 0.3–0.4 | 49 | 0.3626 | 0.6122 |
| 0.4–0.5 | 52 | 0.4496 | 0.5192 |
| 0.5–0.6 | 93 | 0.5089 | 0.1290 |
| 0.6–0.7 | 38 | 0.6439 | 0.6842 |
| 0.7–0.8 | 58 | 0.7475 | 0.8103 |
| 0.8–0.9 | 126 | 0.8276 | 0.8492 |
| 0.9–1.0 | 105 | 0.9610 | 1.0000 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 8 | 0.0744 | 0.0000 |
| 0.1–0.2 | 153 | 0.1410 | 0.1961 |
| 0.2–0.3 | 118 | 0.2209 | 0.3390 |
| 0.3–0.4 | 49 | 0.3626 | 0.6122 |
| 0.4–0.5 | 51 | 0.4487 | 0.5098 |
| 0.5–0.6 | 93 | 0.5089 | 0.1290 |
| 0.6–0.7 | 25 | 0.6410 | 0.5200 |
| 0.7–0.8 | 56 | 0.7466 | 0.8036 |
| 0.8–0.9 | 141 | 0.8325 | 0.8652 |
| 0.9–1.0 | 106 | 0.9296 | 1.0000 |
