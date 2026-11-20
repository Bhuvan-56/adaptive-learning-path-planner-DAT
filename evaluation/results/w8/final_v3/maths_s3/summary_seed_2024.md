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
| **adaptive_full** | 7.5900 [6.8950, 8.2751] | 0 | 0 | 100.0% | 1113 (SCHEDULING_CONSTRAINTS_UNMET:490, CAPACITY_EXCEEDED:623) | 80.769 | 103.796 |
| **static_prerequisite_order** | 6.8950 [6.1195, 7.6701] | 0 | 0 | 100.0% | 0 | 2.810 | 5.368 |
| **non_adaptive_greedy** | 7.2650 [6.4700, 8.0854] | 0 | 0 | 100.0% | 0 | 0.060 | 0.092 |
| **non_adaptive_greedy_best_singleton** | 7.3250 [6.5298, 8.1357] | 0 | 0 | 100.0% | 0 | 0.100 | 0.157 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.6950 | [0.4849, 0.8901] | **adaptive_full improves on static_prerequisite_order** [0.4849, 0.8901] |
| **adaptive_full - non_adaptive_greedy** | 0.3250 | [0.1200, 0.5350] | **adaptive_full improves on non_adaptive_greedy** [0.1200, 0.5350] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.3700 | [0.2400, 0.5001] | **non_adaptive_greedy improves on static_prerequisite_order** [0.2400, 0.5001] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0600 | [0.0100, 0.1100] | **non_adaptive_greedy_best_singleton improves on non_adaptive_greedy** [0.0100, 0.1100] |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 7.7000 [7.0449, 8.3552] | -0.1100 [-0.2351, 0.0101] | no difference shown |
| **ablation_no_replan** | 6.9050 [6.1198, 7.6801] | 0.6850 [0.4700, 0.8800] | adaptive_full improves on ablation_no_replan [0.4700, 0.8800] |
| **ablation_no_difficulty_step** | 7.5800 [6.8850, 8.2652] | 0.0100 [0.0000, 0.0250] | no difference shown |
| **ablation_no_review** | 7.5900 [6.8950, 8.2751] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 7.5900 [6.8950, 8.2751] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.

## 6. Mastery calibration (end of horizon)

Engine estimate p per concept at the end of the horizon against the simulator's latent mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept pairs, 10 equal-width bins on p. Arms that never update p after the diagnostic (static plan, greedy) are not applicable.

| Arm | Mastery Brier [95% CI] | ECE | Pairs |
|---|---|---|---|
| adaptive_full | 0.1851 [0.1778, 0.1928] | 0.1622 | 3200 |
| static_prerequisite_order | not applicable | not applicable | – |
| non_adaptive_greedy | not applicable | not applicable | – |
| non_adaptive_greedy_best_singleton | not applicable | not applicable | – |
| ablation_no_diagnostic | 0.1864 [0.1792, 0.1937] | 0.1570 | 3200 |
| ablation_no_replan | not applicable | not applicable | – |
| ablation_no_difficulty_step | 0.1839 [0.1767, 0.1912] | 0.1621 | 3200 |
| ablation_no_review | 0.1851 [0.1779, 0.1927] | 0.1631 | 3200 |
| ablation_no_remediation | 0.1851 [0.1778, 0.1928] | 0.1622 | 3200 |

Reliability, adaptive_full:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0699 | 0.0000 |
| 0.1–0.2 | 137 | 0.1393 | 0.1679 |
| 0.2–0.3 | 70 | 0.2250 | 0.3857 |
| 0.3–0.4 | 19 | 0.3590 | 0.2105 |
| 0.4–0.5 | 106 | 0.4293 | 0.3113 |
| 0.5–0.6 | 1671 | 0.5012 | 0.2256 |
| 0.6–0.7 | 53 | 0.6542 | 0.5849 |
| 0.7–0.8 | 271 | 0.7414 | 0.7934 |
| 0.8–0.9 | 250 | 0.8323 | 0.8440 |
| 0.9–1.0 | 618 | 0.9775 | 0.9660 |

Reliability, ablation_no_diagnostic:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 0 | – | – |
| 0.1–0.2 | 104 | 0.1376 | 0.1346 |
| 0.2–0.3 | 159 | 0.2099 | 0.2704 |
| 0.3–0.4 | 0 | – | – |
| 0.4–0.5 | 73 | 0.4149 | 0.2466 |
| 0.5–0.6 | 1600 | 0.5000 | 0.2319 |
| 0.6–0.7 | 0 | – | – |
| 0.7–0.8 | 231 | 0.7362 | 0.8009 |
| 0.8–0.9 | 415 | 0.8106 | 0.7542 |
| 0.9–1.0 | 618 | 0.9851 | 0.9644 |

Reliability, ablation_no_difficulty_step:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0712 | 0.0000 |
| 0.1–0.2 | 145 | 0.1373 | 0.1586 |
| 0.2–0.3 | 70 | 0.2248 | 0.3714 |
| 0.3–0.4 | 19 | 0.3590 | 0.2105 |
| 0.4–0.5 | 104 | 0.4270 | 0.3365 |
| 0.5–0.6 | 1672 | 0.5011 | 0.2255 |
| 0.6–0.7 | 54 | 0.6536 | 0.5741 |
| 0.7–0.8 | 264 | 0.7420 | 0.7917 |
| 0.8–0.9 | 242 | 0.8325 | 0.8595 |
| 0.9–1.0 | 625 | 0.9776 | 0.9648 |

Reliability, ablation_no_review:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0699 | 0.0000 |
| 0.1–0.2 | 137 | 0.1393 | 0.1679 |
| 0.2–0.3 | 70 | 0.2250 | 0.3857 |
| 0.3–0.4 | 19 | 0.3590 | 0.2105 |
| 0.4–0.5 | 106 | 0.4293 | 0.3113 |
| 0.5–0.6 | 1670 | 0.5011 | 0.2251 |
| 0.6–0.7 | 53 | 0.6542 | 0.5849 |
| 0.7–0.8 | 275 | 0.7415 | 0.7964 |
| 0.8–0.9 | 251 | 0.8324 | 0.8446 |
| 0.9–1.0 | 614 | 0.9794 | 0.9658 |

Reliability, ablation_no_remediation:

| p bin | Pairs | Mean p | Fraction mastered |
|---|---|---|---|
| 0.0–0.1 | 5 | 0.0699 | 0.0000 |
| 0.1–0.2 | 137 | 0.1393 | 0.1679 |
| 0.2–0.3 | 70 | 0.2250 | 0.3857 |
| 0.3–0.4 | 19 | 0.3590 | 0.2105 |
| 0.4–0.5 | 106 | 0.4293 | 0.3113 |
| 0.5–0.6 | 1671 | 0.5012 | 0.2256 |
| 0.6–0.7 | 53 | 0.6542 | 0.5849 |
| 0.7–0.8 | 271 | 0.7414 | 0.7934 |
| 0.8–0.9 | 250 | 0.8323 | 0.8440 |
| 0.9–1.0 | 618 | 0.9775 | 0.9660 |
