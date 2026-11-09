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
| **adaptive_full** | 8.0800 [7.4750, 8.7251] | 0 | 0 | 100.0% | 1200 (SCHEDULING_CONSTRAINTS_UNMET:400, CAPACITY_EXCEEDED:800) | 112.361 | 258.824 |
| **static_prerequisite_order** | 7.3850 [6.6250, 8.1902] | 0 | 0 | 100.0% | 0 | 3.971 | 5.364 |
| **non_adaptive_greedy** | 7.7050 [6.9349, 8.5200] | 0 | 0 | 100.0% | 0 | 0.081 | 0.112 |
| **non_adaptive_greedy_best_singleton** | 7.7550 [6.9746, 8.5701] | 0 | 0 | 100.0% | 0 | 0.132 | 0.202 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.6950 | [0.4496, 0.9501] | **adaptive_full improves on static_prerequisite_order** [0.4496, 0.9501] |
| **adaptive_full - non_adaptive_greedy** | 0.3750 | [0.1050, 0.6350] | **adaptive_full improves on non_adaptive_greedy** [0.1050, 0.6350] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.3200 | [0.1650, 0.4750] | **non_adaptive_greedy improves on static_prerequisite_order** [0.1650, 0.4750] |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | 0.0500 | [-0.0100, 0.1100] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 8.0800 [7.4750, 8.7251] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_replan** | 7.3850 [6.6250, 8.1902] | 0.6950 [0.4496, 0.9501] | adaptive_full improves on ablation_no_replan [0.4496, 0.9501] |
| **ablation_no_difficulty_step** | 8.0750 [7.4699, 8.7251] | 0.0050 [-0.0100, 0.0250] | no difference shown |
| **ablation_no_review** | 8.0800 [7.4750, 8.7251] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 8.0800 [7.4750, 8.7251] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.
