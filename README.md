# Adaptive Learning and Path-Planning Engine

**Team:** Bhuvan Chandra (AI23BTECH11013), Abdur Rehman (AI23BTECH11015)
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

1. Ensure Python 3.11 is installed.
2. Install pinned dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

Run the full pytest suite:

```bash
pytest
```

Run specific test modules:

```bash
# Graph loader & validator tests (TC-1.2)
pytest tests/test_m1_curriculum_graph.py

# Learner state model tests (M1)
pytest tests/test_m1_learner_state.py

# Path planning & infeasibility tests (TC-3.1, TC-3.2)
pytest tests/test_m3_path_planning.py

# Explainability & trace checker tests (TC-7.1, TC-7.2, TC-7.3)
pytest tests/test_m7_explainability.py
```

## Running the Benchmark

Run the 250-instance Greedy vs. Exact DP Oracle optimality benchmark:

```bash
python -m src.planning.benchmark
```

This generates:
- `evaluation/results/w2_greedy_vs_oracle.csv` (per-instance benchmark results)
- `evaluation/results/w2_summary.md` (summary statistics: mean, 5th percentile, worst-case, runtimes)


## Documentation Index

- `docs/PROBLEM_BOUNDARY.md` — Actors, system boundary, in/out of scope
- `ASSUMPTIONS.md` — Documented assumptions and known limitations
- `docs/DATA_STRATEGY.md` — Dataset comparison, primary strategy, unavailable-field handling
- `docs/LITERATURE_REVIEW.md` — Comparative approach analysis (M1-M5 areas)
- `docs/FORMAL_MODELS.md` — Formal learner-state and curriculum graph models
- `docs/METRICS.md` — Initial evaluation metrics
- `TRACEABILITY.md` — Requirement -> Milestone -> Acceptance Test (TC-ID) register
- `/decisions` — Architecture/methodology decision records
