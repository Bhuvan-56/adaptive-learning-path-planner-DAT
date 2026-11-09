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
| **adaptive_full** | 1.8900 [1.7050, 2.0800] | 0 | 0 | 100.0% | 200 (SCHEDULING_CONSTRAINTS_UNMET:200) | 41.880 | 48.336 |
| **static_prerequisite_order** | 1.8100 [1.6250, 2.0150] | 0 | 0 | 100.0% | 0 | 0.934 | 1.109 |
| **non_adaptive_greedy** | 1.8100 [1.6150, 2.0150] | 0 | 0 | 100.0% | 0 | 0.023 | 0.024 |
| **non_adaptive_greedy_best_singleton** | 1.8000 [1.6100, 1.9950] | 0 | 0 | 100.0% | 0 | 0.070 | 0.098 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | 0.0800 | [-0.0200, 0.1750] | no difference shown |
| **adaptive_full - non_adaptive_greedy** | 0.0800 | [-0.0300, 0.1851] | no difference shown |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [-0.0750, 0.0750] | no difference shown |
| **non_adaptive_greedy_best_singleton - non_adaptive_greedy** | -0.0100 | [-0.0450, 0.0300] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 1.8900 [1.7050, 2.0800] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_replan** | 1.8100 [1.6250, 2.0150] | 0.0800 [-0.0200, 0.1750] | no difference shown |
| **ablation_no_difficulty_step** | 1.8900 [1.7050, 2.0800] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.8900 [1.7050, 2.0800] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 1.8900 [1.7050, 2.0800] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.
