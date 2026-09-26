# Adaptive Learning and Path-Planning Engine

**Team:** Bhuvan (AI23BTECH11013), Abdur Rehman (AI23BTECH11015)
**Course:** CS5903 — Distributed AI Training (DAT)

## Overview

This project implements a backend recommendation, learner-state estimation, policy, and
path-planning service for structured quantitative subjects (Mathematics and Computer
Science). Given a learner's prior knowledge, target skill, deadline, and daily study-time
budget, the system estimates evolving skill mastery and generates a personalized,
prerequisite-respecting learning plan — including new material, spaced review, and
remediation — along with a machine-readable explanation of every scheduling decision.

**What this prototype does _not_ implement:** a Learning Management System (LMS)
interface, authoring of extensive educational curriculum content, natural-language
content-generation pipelines, or collection of private/proprietary student telemetry.
See `docs/PROBLEM_BOUNDARY.md` for the full scope statement and actor definitions.

## System Components

| Module               | Responsibility                                                           |
| -------------------- | ------------------------------------------------------------------------ |
| Curriculum Graph     | Validated DAG of concepts and mandatory prerequisites                    |
| Diagnostic (CAT/IRT) | Cold-starts a new learner's initial mastery estimate                     |
| Mastery Model (BKT)  | Continuously updates per-concept mastery from quiz/exercise evidence     |
| Planning Engine      | Daily, time-budgeted scheduling of new learning, review, and remediation |
| Spaced Review (HLR)  | Predicts recall decay and triggers reviews before forgetting             |
| Explainability Layer | Produces a structured JSON audit trace for every generated plan          |

## Repository Structure

```
/data          - dataset documentation, processed logs, curriculum DAG definitions
/models        - BKT, IRT, and HLR implementations
/diagnostic    - CAT item selection and calibration
/planner       - DAG validation, scheduling, infeasibility detection, optimization
/adaptation    - difficulty and remediation policies
/audit         - explainability and JSON trace generation
/simulators    - synthetic learner generation
/evaluation    - baselines, robustness experiments, ablations, metrics, config
/tests         - graph validation, planner, infeasibility, adaptation, trace tests
/decisions     - architecture and methodology decision records
/weekly        - dated weekly progress records
docs/          - problem boundary, assumptions, data strategy, formal models
ASSUMPTIONS.md - documented system assumptions
TRACEABILITY.md- requirement -> milestone -> acceptance test mapping
```

## Setup

> To be filled in as implementation begins (Week 2 onward): environment setup,
> dependency installation, and dataset download/preprocessing commands.

## Running the System

> To be filled in once an end-to-end vertical slice exists (Week 3 onward): the exact
> command(s) to generate a learning plan for a sample learner profile.

## Evaluation

Baselines, metrics, and reproducible experiment configuration live under `/evaluation`.
See `docs/METRICS.md` for the full list of initial metrics and `TRACEABILITY.md` for how
each milestone (M1-M8) maps to its acceptance tests.

## Documentation Index

- `docs/PROBLEM_BOUNDARY.md` — Actors, system boundary, in/out of scope
- `ASSUMPTIONS.md` — Documented assumptions and known limitations
- `docs/DATA_STRATEGY.md` — Dataset comparison, primary strategy, unavailable-field handling
- `docs/LITERATURE_REVIEW.md` — Comparative approach analysis (M1-M5 areas)
- `docs/FORMAL_MODELS.md` — Formal learner-state and curriculum graph models
- `docs/METRICS.md` — Initial evaluation metrics
- `TRACEABILITY.md` — Requirement -> Milestone -> Acceptance Test (TC-ID) register
- `/decisions` — Architecture/methodology decision records
