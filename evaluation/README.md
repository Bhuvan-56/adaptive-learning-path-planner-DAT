# Evaluation Framework

This directory contains the comparative evaluation suite, baseline models, robustness simulation drivers, ablation configurations, and experiment metrics for the Adaptive Learning and Path-Planning Engine.

## Evaluation Strategy Overview

To evaluate adaptive path planning fairly and avoid circular evaluation (where a simulator merely rewards an engine for reproducing its own assumptions), the evaluation pipeline compares the proposed engine against pre-declared baseline strategies across both empirical datasets and multiple synthetic learner simulator families.

For detailed metric definitions, mathematical formulas, and acceptance criteria, see [`docs/METRICS.md`](../docs/METRICS.md) and [`TRACEABILITY.md`](../TRACEABILITY.md).

## Baseline Models

1. **Static Prerequisite Order Baseline:**
   - Traverses the validated curriculum Directed Acyclic Graph (DAG) using a fixed topological ordering.
   - Schedules activities strictly in prerequisite order without dynamic mastery updates (BKT), difficulty adaptation, or spaced review prioritization.

2. **Non-Adaptive Greedy Baseline:**
   - Selects activities using a fixed score-per-minute heuristic ($\frac{\text{Score}_i}{L_i}$).
   - Operates without Bayesian Knowledge Tracing (BKT) adaptation, spaced repetition decay modeling (HLR), or computerized adaptive testing (CAT).

## Planned Ablation Study

Per the system proposal, component ablation studies will be conducted to isolate the individual contributions of adaptive sub-modules:
- **Ablation 1 (No Spaced Review):** Removes Half-Life Regression (HLR) memory decay scoring and review scheduling ($w_1 = 0$), forcing the system to perform pure new-learning path generation.
- **Ablation 2 (No Difficulty Adaptation):** Fixes exercise difficulty at baseline ($d_{c,t} = d_{c,0}$), disabling stepwise difficulty adjustments ($\pm 0.10$).

## Synthetic Simulator Families

- **Matched Simulator:** Uses BKT-like transitions to verify engine performance under intended design assumptions.
- **Robustness Simulators:** Deliberately mismatch engine assumptions to test generalization:
  1. Performance Factor Analysis (PFA)-style learning dynamics;
  2. Item Response Theory (IRT)-based response generation with stochastic learning transitions;
  3. Alternative exponential or power-law forgetting curves;
  4. Heterogeneous slip, guess, and learning rate parameter distributions.

## Preserved Experiment Configurations

All random seeds, learner profile initializations, and model evaluation parameters are version-controlled under [`/evaluation/config/`](config/):

- [`evaluation/config/profiles.yaml`](config/profiles.yaml): Preserves definitions and time budgets for the four standard learner profiles (Profile 1: 5 min, Profile 2: 10 min, Profile 3: 15 min, Profile 4: 30 min).
- [`evaluation/config/seeds.yaml`](config/seeds.yaml): Versioned random seeds (`seeds: [42, 101, 2024, 777, 999]`) for evaluation reproducibility across 200 synthetic learners.
