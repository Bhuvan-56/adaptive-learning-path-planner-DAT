# Data Strategy

## Comparison: Public Datasets vs. Transparent Learner Simulator

Public educational datasets, specifically the Junyi Academy and ASSISTments 2009-2010
datasets, offer realistic learner-response evidence and authentic time-on-task metrics.
They supply structural curriculum data, including exercise identifiers, prerequisite
relationships, and topic metadata. However, public datasets lack visibility into a
learner's true latent mastery. They also do not naturally provide controlled edge cases
for mathematically infeasible deadlines or explicitly missed planning sessions.

Transparent synthetic learner simulators provide absolute visibility into true latent
mastery states, specific learning rates, and exact forgetting parameters. They enable
rigorous evaluation of controlled edge cases and ground-truth time-to-mastery tracking.
However, using simulators in isolation risks circular evaluation, where the planner is
simply rewarded for reproducing the exact assumptions built into its own implementation.

## Primary Strategy Selection

A hybrid data strategy will be implemented, combining public educational datasets for
empirical model fitting with transparent synthetic simulators for controlled policy
evaluation.

- The Junyi Academy dataset will supply the foundational Directed Acyclic Graph (DAG)
  for the curriculum, populating nodes with exercises and establishing mandatory
  prerequisite edges.
- Both the Junyi and ASSISTments datasets will be split by student (70% training, 15%
  development, 15% evaluation) to fit real-world parameter distributions for Bayesian
  Knowledge Tracing (BKT), Item Response Theory (IRT), and Half-Life Regression (HLR)
  models. The student-level split ensures no student's data is used for both fitting and
  evaluation, preventing leakage that would otherwise inflate calibration results.
- Synthetic learner simulators will handle the controlled testing of constraints and
  deadlines. To prevent evaluation bias, multiple mismatched simulator models (e.g.,
  PFA-style learning, alternative exponential or power-law forgetting curves) will be
  used. The parameters for these simulators will be sampled strictly from empirical
  distributions estimated from the public training logs.

## Handling Unavailable Fields

- **Missing Baseline Durations:** If a concept-level lesson lacks explicit total
  duration data, the baseline time will be derived using the dataset's median
  per-attempt timing multiplied by the configured number of practice items
  ($L_{c} = \frac{\text{median}(time\_taken_{c}) \times N_{c}}{60}$). If no reliable
  public timing data exists at all, synthetic durations will be used and explicitly
  marked as synthetic.

- **Unmapped Prerequisites:** Cross-dataset prerequisite relationships will not be
  fabricated if an ASSISTments skill cannot be directly mapped to the Junyi curriculum
  structure. In these cases, the ASSISTments data will remain an independent benchmark
  strictly for response modelling, without forcing unsupported graph edges.

- **Missing Review Histories:** For spaced review tracking, if a concept lacks a
  historical observation trail to establish a specific memory decay rate, the initial
  memory half-life ($H_{c,0}$) will be populated using a prior value ($H_{prior}$). This
  value represents the median half-life estimated from the broader HLR training
  population, preventing unseen concepts from receiving undefined recall estimates.
