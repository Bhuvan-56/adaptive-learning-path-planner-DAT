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
  curriculum/  - graph loader, topological validator, error types (Module M1)
  diagnostic/  - computerized adaptive testing (CAT / IRT) diagnostic engine (Module M2)
  planning/    - static baseline, greedy scheduler, exact DP oracle, feasibility, difficulty stepping, replanning (Modules M3, M4, M5, M6)
  state/       - learner state model (BKT update, Beta variance proxy, policy classification) (Module M1)
  trace/       - decision audit trace schema, candidate universe, trace contract checker (Module M7)
  simulation/  - synthetic learner simulator with Matched BKT generator and EvaluatorView (Module M8)
  evaluation/  - comparative evaluation pipeline across diagnostic and planner arms (Module M8)
  cli.py       - unified CLI entry point supporting demo, plan, and slice subcommands (Module M8)
  provenance.py- deterministic configuration hashing and execution manifest generation
config/        - BKT default parameters, profiles, and adaptive stepping configuration
data/          - dataset documentation, synthetic item bank, Q-matrix, curriculum DAGs
decisions/     - architecture and methodology decision records (ADR-001 to ADR-009)
evaluation/    - baselines, benchmark results, metrics, comparative evaluation outputs
experiments/   - benchmark configurations and evaluation definitions
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

# Horizontal slice & adversarial matrix tests (Week 4 T2)
pytest tests/test_w4_t2_slice.py
```

## Running the Benchmark

Run the 250-instance Greedy vs. Exact DP Oracle optimality benchmark:

```bash
python -m src.planning.benchmark
```

This generates:
- `evaluation/results/w2_greedy_vs_oracle.csv` (per-instance benchmark results)
- `evaluation/results/w2_summary.md` (summary statistics: mean, 5th percentile, worst-case, runtimes)

## Command-Line Interface (CLI)

The application provides a unified CLI entry point via `python -m src.cli` supporting three primary subcommands: `demo`, `plan`, and `slice`.

### 1. End-to-End Demo (`demo`)

Run the multi-scenario end-to-end demonstration:

```bash
python -m src.cli demo --out evaluation/results/w3/demo --seed 20261012 --budget 10
```

This executes:
- Validates curriculum DAG (`data/curricula/demo_curriculum.json`).
- Generates Day 1 plans for Novice and Intermediate learners.
- Simulates dynamic assessment responses and replanning (Passed vs. Failed scenarios).
- Simulates a missed day and subsequent budget reduction proving block infeasibility.
- Writes 14 artifacts (plans, traces, `response_updates.json`, and `manifest.json`) to `--out`.

### 2. Single Plan Request (`plan`)

Generate and trace a single plan request from input data:

```bash
python -m src.cli plan --curriculum data/curricula/demo_curriculum.json --target D --budget 10 --deadline-days 3 --out evaluation/results/plan_run
```

Options:
- `--curriculum <file>`: Path to curriculum DAG JSON definition (required).
- `--target <id>`: Target concept node ID (required).
- `--budget <int>`: Daily study budget in minutes (required).
- `--deadline-days <int>`: Horizon in days (required).
- `--policy <yaml>`: Optional path to BKT/classification policy YAML file.
- `--states <json>`: Optional path to initial learner states JSON file.
- `--out <dir>`: Output directory for `plan.json` and `trace.json` (required).

### 3. Horizontal Slice Demonstration (`slice`)

Run the complete Week 4 horizontal slice pipeline demonstrating all 8 integrated subsystems:

```bash
python -m src.cli slice --out evaluation/results/w4/slice --seed 20261024 --budget 10
```

Options:
- `--out <dir>`: Output directory for all 21 slice artifacts (required).
- `--seed <int>`: Deterministic random seed (default: `20261024`).
- `--budget <int>`: Daily study time budget in minutes (default: `10`).
- `--target <id>`: Target concept node ID (default: `D`).
- `--curriculum <file>`: Curriculum DAG JSON path (default: `data/curricula/demo_curriculum.json`).
- `--item-bank <csv>`: Synthetic item bank CSV path (default: `data/processed/item_bank_synthetic.csv`).
- `--q-matrix <csv>`: Synthetic Q-matrix CSV path (default: `data/processed/q_matrix_synthetic.csv`).
- `--policy <yaml>`: Policy configuration YAML (default: declared default policy).

This executes:
1. Loads and validates curriculum, item bank, and Q-matrix via `plan_request`.
2. Creates two simulated learners expanded through groups; latent state strictly hidden.
3. Runs adaptive CAT diagnostics via injected responses, computes initial priors, writes `diagnostic_record.json`.
4. Plans Day 1, applies assessment with simulated responses, steps difficulty, gates dependent concepts on evidence Mastered.
5. Advances days, schedules timestamped spaced review in leftover budget (`REVIEW_DUE`), triggers prerequisite remediation on repeated failures (`REMEDIATION_TRIGGERED`).
6. Executes missed day, reduced budget, and shortened deadline while preserving completed progress.
7. Validates and writes all 21 artifacts (plans, traces, `response_updates.json`, `diagnostic_record.json`, and SHA-256 `manifest.json`).
8. Prints an evidence-backed summary derived from emitted traces.



## Bayesian Knowledge Tracing (pyBKT) Integration

The engine supports offline parameter estimation using `pyBKT` and proves exact mathematical equivalence with the project's online sequential BKT adapter (`src/state/bkt_adapter.py`).

### 1. Fit the pyBKT Model

Fit pyBKT on student training responses and write fitted parameters to `config/bkt_fitted.yaml`:

```bash
python examples/pybkt_fit_predict.py
```

This outputs fitted parameters (`prior`, `p_T`, `p_G`, `p_S`, `forget=0.0`) and evaluates prediction on a held-out student.

### 2. Run the BKT Parity Test

Verify that the online BKT adapter matches pyBKT's predictions step-by-step to within $10^{-6}$:

```bash
pytest tests/test_m1_bkt_parity.py -v
```

## Documentation Index

- `docs/PROBLEM_BOUNDARY.md` — Actors, system boundary, in/out of scope
- `ASSUMPTIONS.md` — Documented assumptions and known limitations
- `docs/DATA_STRATEGY.md` — Dataset comparison, primary strategy, unavailable-field handling
- `docs/LITERATURE_REVIEW.md` — Comparative approach analysis (M1-M5 areas)
- `docs/FORMAL_MODELS.md` — Formal learner-state and curriculum graph models
- `docs/METRICS.md` — Initial evaluation metrics
- `TRACEABILITY.md` — Requirement -> Milestone -> Acceptance Test (TC-ID) register
- `/decisions` — Architecture/methodology decision records
