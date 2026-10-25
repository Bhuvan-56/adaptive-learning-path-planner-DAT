# Week 5 Final Integrated Evaluation Report

## 1. Executive Summary & Disclaimer

- **Evaluation Benchmark:** `w5_integrated` (configured via `experiments/w5_final.yaml`)
- **Evaluation Engine:** `python -m src.cli evaluate`
- **Output Commit:** `cfe2ea7`
- **Synthetic Learner Invariant:** **All results reported herein represent simulator behaviour on synthetic learners fitted to synthetic data. No real-learner or real-world claim is made or implied.**

---

## 2. Experimental Setup & Pre-Registered Parameters

- **Synthetic Cohort:** $N = 200$ synthetic learners evaluated across matched random seeds (`seeds: [42, 101, 2024, 777, 999]`).
- **Planning Horizon:** 5 days.
- **Daily Study Budget:** 10 minutes.
- **Bootstrap Resamples:** $B = 1000$ paired percentile bootstrap iterations (95% confidence level).
- **Claim Rule:** An arm is called better than another only if the paired 95% bootstrap confidence interval for that difference excludes zero (strictly positive lower bound). If the interval includes zero, the outcome is recorded as "no difference shown".
- **Primary Outcome:** Concepts truly mastered at the end of the 5-day horizon, read strictly at evaluation time via `EvaluatorView`.
- **Secondary Outcomes:** Prerequisite violations, daily budget violations, trace coverage, no-plan counts, and planning runtime distributions.

---

## 3. Arm Performance Tables (Scenario S0: Matched BKT Generator)

All numbers are drawn strictly from committed outputs (`evaluation/results/w5/final/summary.md` and `evaluation/results/w5/final/per_learner.csv`).

### Primary Arms

| Arm | Concepts Mastered [95% CI] | Prereq Violations | Budget Violations | Trace Coverage (%) | No-Plan Days | Runtime p50 (ms) | Runtime p95 (ms) |
|---|---|---|---|---|---|---|---|
| **`adaptive_full`** | 1.8900 [1.6499, 2.1200] | 0 | 0 | 100.0% | 800 (SCHEDULING_CONSTRAINTS_UNMET: 800) | 25.598 | 28.916 |
| **`static_prerequisite_order`** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 2.371 | 2.776 |
| **`non_adaptive_greedy`** | 1.9700 [1.7299, 2.2050] | 0 | 0 | 100.0% | 0 | 0.058 | 0.077 |

### Ablation Arms (Single-Component Removals)

| Ablation Arm | Concepts Mastered [95% CI] | Difference from `adaptive_full` [95% CI] | Claim Assessment |
|---|---|---|---|
| **`ablation_no_diagnostic`** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **`ablation_no_replan`** | 1.9700 [1.7299, 2.2050] | -0.0800 [-0.1200, -0.0450] | `ablation_no_replan` improves on `adaptive_full` [0.0450, 0.1200] |
| **`ablation_no_difficulty_step`** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **`ablation_no_review`** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |
| **`ablation_no_remediation`** | 1.8900 [1.6499, 2.1200] | 0.0000 [0.0000, 0.0000] | no difference shown |

---

## 4. Paired Difference Tables & Claim Rule Application

Under the pre-registered claim rule:
- Difference $= \text{Arm}_1 - \text{Arm}_2$.
- Better only if 95% bootstrap CI excludes 0 and is strictly positive.

| Comparison | Mean Difference | Paired 95% Bootstrap CI | Claim Rule Assessment |
|---|---|---|---|
| **`adaptive_full - static_prerequisite_order`** | -0.0800 | [-0.1200, -0.0450] | **`static_prerequisite_order` improves on `adaptive_full`** (CI excludes zero, favoring baseline by [0.0450, 0.1200]) |
| **`adaptive_full - non_adaptive_greedy`** | -0.0800 | [-0.1200, -0.0450] | **`non_adaptive_greedy` improves on `adaptive_full`** (CI excludes zero, favoring baseline by [0.0450, 0.1200]) |
| **`non_adaptive_greedy - static_prerequisite_order`** | 0.0000 | [0.0000, 0.0000] | **no difference shown** (interval includes zero) |

---

## 5. Hard-Correctness Verification

Across all 8 arms evaluated on 200 learners over 5 days (8,000 learner-days evaluated):
- **Prerequisite Violations:** **0** (100% compliant across all arms).
- **Daily Budget Violations:** **0** (100% compliant across all arms).
- **Trace Coverage:** **100.0%** (1.0 trace coverage, 8,000 / 8,000 valid daily audit traces).

---

## 6. Retention Analysis for S1 & Scenario Variants Status

In `experiments/w5_final.yaml`, four scenarios were specified:
- **S0:** Default matched BKT generator (`MatchedBKTGenerator`).
- **S1:** Forgetting variant ($p_F = 0.05$) with delayed retention quiz.
- **S2:** Difficulty-sensitive variant ($k = 0.50$).
- **S3:** Mismatched PFA/logistic practice generator.

### Execution Status:
- **Scenario S0** was executed fully by the integrated evaluation harness (`src.evaluation.integrated`).
- **Scenarios S1, S2, and S3** were **not executed** in this integrated evaluation run. While B2 implemented the generator classes in `src/simulation/simulator.py` and the retention quiz in `src/evaluation/retention.py`, B1's integrated evaluation harness (`src/evaluation/integrated.py`) was implemented to run only the primary simulator (`MatchedBKTGenerator`) and does not support multi-scenario loop dispatching or retention quiz administration during `evaluate`.
- **Retained Recall Table for S1:** Not generated in the committed integrated evaluation outputs (`per_learner.csv` / `summary.md`). As required by protocol: *"Take every number from the committed outputs. Leave out any scenario whose generator is not merged, and write the reason in a comment. Do not write a stand-in."*

---

## 7. What Did Not Hold

1. **Adaptive Superiority Did Not Hold:**
   - In both primary comparisons (`adaptive_full` vs `static_prerequisite_order` and `adaptive_full` vs `non_adaptive_greedy`), the paired 95% bootstrap CI was $[-0.1200, -0.0450]$.
   - The adaptive arm **did not beat** either baseline. In fact, both static prerequisite ordering and non-adaptive greedy frontier packing achieved significantly higher mastery ($+0.0800$ concepts, CI $[0.0450, 0.1200]$) than `adaptive_full`.
   - **Root Cause:** In the simulation, dynamic replanning encountered `SCHEDULING_CONSTRAINTS_UNMET` on 800 replan instances (days 2–5) when trying to re-optimize within the tightly constrained 10-minute daily budget and remaining horizon, causing fallback candidate lists, whereas the static schedule reliably packed and executed content without replanning failure.

2. **Baseline Differentiation Did Not Hold:**
   - The comparison `non_adaptive_greedy - static_prerequisite_order` showed a mean difference of $0.0000$ and CI $[0.0000, 0.0000]$.
   - The interval includes zero (collapsing to exactly 0), meaning no difference was demonstrated between static topological order and greedy frontier packing on this curriculum and budget.

3. **Ablation Sensitivity Did Not Hold for 4 out of 5 Components:**
   - `ablation_no_diagnostic`: Difference $0.0000$ [0.0000, 0.0000] (no difference shown).
   - `ablation_no_difficulty_step`: Difference $0.0000$ [0.0000, 0.0000] (no difference shown).
   - `ablation_no_review`: Difference $0.0000$ [0.0000, 0.0000] (no difference shown).
   - `ablation_no_remediation`: Difference $0.0000$ [0.0000, 0.0000] (no difference shown).
   - **Reason:** Under the default simulator (`MatchedBKTGenerator`), difficulty stepping and spaced review do not affect latent mastery transitions because the default generator has zero forgetting ($p_F = 0$) and does not incorporate item difficulty.
   - Only `ablation_no_replan` differed from `adaptive_full` (Mean Diff: $-0.0800$ $[-0.1200, -0.0450]$), exactly matching the static baseline performance.
