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

The architecture consists of eight distinct modular components (M1 through M8):

| Module | Responsibility |
| --- | --- |
| M1: Curriculum Graph & Learner State | Validated DAG of concepts, BKT mastery tracking, and Beta belief state |
| M2: Diagnostic (CAT/IRT) | Cold-starts a new learner's initial mastery estimate via adaptive testing |
| M3: Path Planning Engine | Daily, time-budgeted scheduling (score-per-minute greedy & exact DP oracle) |
| M4: Difficulty Adaptation | Dynamically adjusts exercise difficulty based on learner performance |
| M5: Spaced Review & Remediation | Predicts HLR recall decay and schedules prerequisite remediation |
| M6: Dynamic Replanning & Infeasibility | Re-optimizes schedules on missed days or budget changes with infeasibility detection |
| M7: Explainability Layer | Produces structured JSON audit traces and verifies decision completeness |
| M8: Comparative Evaluation Suite | Compares planning policies against baselines across matched learner profiles |

## Repository Structure

```
src/
  curriculum/  - graph loader, topological validator, error types
  planning/    - static baseline, greedy scheduler, exact DP oracle, feasibility
  state/       - learner state model (BKT update, Beta variance proxy, classification)
  trace/       - decision audit trace schema, candidate universe, trace checker
config/        - BKT default parameters and learner profiles configuration
data/          - dataset documentation, processed logs, curriculum DAG definitions
decisions/     - architecture and methodology decision records (ADR-001 to ADR-009)
evaluation/    - baselines, benchmark results, metrics, configuration
tests/         - unit and acceptance test suites for M1-M8
weekly/        - dated weekly progress records and inputs
docs/          - problem boundary, data strategy, formal models, metrics, audits
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
