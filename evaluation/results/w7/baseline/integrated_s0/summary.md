# Week 5 Integrated Evaluation Summary: Multi-Seed Benchmark

## 1. Multi-Seed Benchmark Setup

- **Benchmark Name:** `w5_integrated_multiseed`
- **Evaluated Seeds (5):** `[42, 101, 2024, 777, 999]`
- **Synthetic Learners per Seed:** 200
- **Total Synthetic Learners Evaluated:** 1000
- **Planning Horizon:** 5 days
- **Daily Study Budget:** 10 minutes
- **Bootstrap Resamples per Seed:** 1000 (paired percentile bootstrap)
- **Generative Simulator:** `MatchedBKTGenerator` (BKT response dynamics)

## 2. Per-Seed Performance Table (Primary Arms)

| Seed | adaptive_full [95% CI] | static_prerequisite_order [95% CI] | non_adaptive_greedy [95% CI] | adaptive minus static [95% CI] | Claim Assessment | No-Plan Days (adaptive) |
|---|---|---|---|---|---|---|
| **42** | 1.8900 [1.6499, 2.1200] | 1.9700 [1.7299, 2.2050] | 1.9700 [1.7299, 2.2050] | -0.0800 [-0.1200, -0.0450] | static_prerequisite_order improves on adaptive_full [0.0450, 0.1200] | 800 |
| **101** | 1.8950 [1.6650, 2.1300] | 1.9700 [1.7450, 2.2050] | 1.9700 [1.7450, 2.2050] | -0.0750 [-0.1100, -0.0400] | static_prerequisite_order improves on adaptive_full [0.0400, 0.1100] | 800 |
| **2024** | 1.9700 [1.7449, 2.1900] | 2.1150 [1.8850, 2.3250] | 2.1150 [1.8850, 2.3250] | -0.1450 [-0.1950, -0.1000] | static_prerequisite_order improves on adaptive_full [0.1000, 0.1950] | 800 |
| **777** | 1.7950 [1.5649, 2.0200] | 1.8700 [1.6400, 2.1050] | 1.8700 [1.6400, 2.1050] | -0.0750 [-0.1150, -0.0400] | static_prerequisite_order improves on adaptive_full [0.0400, 0.1150] | 800 |
| **999** | 2.1200 [1.8949, 2.3600] | 2.2550 [2.0449, 2.4750] | 2.2550 [2.0449, 2.4750] | -0.1350 [-0.1900, -0.0850] | static_prerequisite_order improves on adaptive_full [0.0850, 0.1900] | 800 |

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
| **ablation_no_diagnostic** | Cold-start priors (p=0.5) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On | On |
| **ablation_no_replan** | Initial priors (IRT CAT) | Static Topological Sort (`generate_static_plan`) | 2-Up / 1-Down staircase | Off | Off | Off |
| **ablation_no_difficulty_step** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | Static base | On | On | On |
| **ablation_no_review** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | Off | On |
| **ablation_no_remediation** | Initial priors (IRT CAT) | Dynamic Replan (`src.planning.replan`) | 2-Up / 1-Down staircase | On | On | Off |

## 2. Primary Arm Performance Results

| Arm | Concepts Mastered [95% CI] | Prereq Violations | Budget Violations | Trace Coverage (%) | No-Plan Results | Runtime p50 (ms) | Runtime p95 (ms) |
|---|---|---|---|---|---|---|---|
| **adaptive_full** | 1.8900 [1.6499, 2.1200] | 0 | 0 | 100.0% | 800 (SCHEDULING_CONSTRAINTS_UNMET:800) | 6.959 | 12.125 |
| **static_prerequisite_order** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.718 | 1.494 |
| **non_adaptive_greedy** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.020 | 0.047 |

## 3. Paired Statistical Comparisons & Claim Rule

Under the strict claim rule: an arm is called better than another only if the paired 95% bootstrap interval for that difference excludes zero (strictly positive lower bound). Otherwise the summary reports 'no difference shown'.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Assessment |
|---|---|---|---|
| **adaptive_full - static_prerequisite_order** | -0.0800 | [-0.1200, -0.0450] | **static_prerequisite_order improves on adaptive_full** [0.0450, 0.1200] |
| **adaptive_full - non_adaptive_greedy** | -0.0800 | [-0.1200, -0.0450] | **non_adaptive_greedy improves on adaptive_full** [0.0450, 0.1200] |
| **non_adaptive_greedy - static_prerequisite_order** | 0.0000 | [0.0000, 0.0000] | no difference shown |

## 4. Ablation Analysis (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from adaptive_full [95% CI] | Claim Assessment |
|---|---|---|---|
| **ablation_no_diagnostic** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_replan** | 1.9700 [1.7299, 2.2050] | -0.0800 [-0.1200, -0.0450] | ablation_no_replan improves on adaptive_full [0.0450, 0.1200] |
| **ablation_no_difficulty_step** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_review** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **ablation_no_remediation** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |

## 5. Architectural & Behavioral Notes

1. **Simulator Properties Disclaimer:** Under the default simulator (`MatchedBKTGenerator`), difficulty and review ablations cannot change a latent mastery outcome, because it ignores difficulty and has no forgetting.
2. **Synthetic Learner Invariant:** All reported figures represent simulator behavior on synthetic learners fitted to synthetic data. Never calibrated, validated or real-world.
3. **Safety Invariants:** Zero prerequisite violations and zero budget violations were observed across all primary and ablation runs.
