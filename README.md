# Adaptive Learning and Path-Planning Engine

**Team:** Bhuvan Chandra (AI23BTECH11013), Abdur Rehman (AI23BTECH11015)
**Course:** CS5903 — Distributed AI Training (DAT) · **Project 03 · Group 11**

## Status and Final Submission

- **Status:** milestones M1–M8 are implemented and evaluated on synthetic learners only (no real learner data). 20 of 21 acceptance groups pass; M4-a (infeasibility repair for `HEURISTIC_NO_PLAN`) is partial, as agreed with the mentor. The full test suite reports **299 passed**.
- **Final revision:** tag [`cs5903-final-2026`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/tree/cs5903-final-2026).
- **Deliverable A, Project Report:** [`docs/Project_Report.pdf`](docs/Project_Report.pdf)
- **Deliverable B, Architecture Decision Records:** [`docs/Architecture_Decision_Records.md`](docs/Architecture_Decision_Records.md)
- **Demo:** <https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/> (see [Operational Handover](#operational-handover))
- **Known limitations and open defects:** [`docs/final/LIMITATIONS.md`](docs/final/LIMITATIONS.md)

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

## Final Deliverables (Week 8)

| Document | Contents |
| --- | --- |
| [`docs/Project_Report.pdf`](docs/Project_Report.pdf) | **Final project report (submission deliverable A)** |
| [`docs/Architecture_Decision_Records.md`](docs/Architecture_Decision_Records.md) | **Decision log ADR-001 to ADR-022, incl. the methodology record ADR-010 (deliverable B)** |
| [`docs/final/FINAL_REPORT.md`](docs/final/FINAL_REPORT.md) | Markdown summary of the final results and reproduction commands (the PDF is the full report) |
| [`docs/final/LIMITATIONS.md`](docs/final/LIMITATIONS.md) | What the evidence cannot support; open defects |
| [`docs/final/DEMO.md`](docs/final/DEMO.md) | Final demo script (website and live demos) |
| [`docs/final/ownership_track_A.md`](docs/final/ownership_track_A.md), [`ownership_track_B.md`](docs/final/ownership_track_B.md) | Code explanation and live change task per track |
| [`docs/w8/results.md`](docs/w8/results.md) | Week 8 fixes: S1 daily forgetting, best-effort plan on infeasible days |
| [`weekly/W8.md`](weekly/W8.md) | Week 8 report |

Project website: <https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/> (source in `site/`).

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

**Environment variables and secrets:** none. The project needs no API keys, accounts, database or environment variables, so there is no `.env` file. All data is synthetic and committed under `data/`. The only network access is optional: the website's live demos download Pyodide from `cdn.jsdelivr.net` once.

## Running Tests

Run the full pytest suite:

```bash
pytest
```

**Expected outcome:** `299 passed` (Windows, Python 3.11, at the final tag). Note that `tests/test_m7_explainability.py` rewrites `evaluation/results/sample_trace_normal.json`; restore it with `git checkout -- evaluation/results/sample_trace_normal.json` if you want a clean tree afterwards.

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

The application provides a unified CLI entry point via `python -m src.cli` supporting four primary subcommands: `demo`, `plan`, `slice`, and `evaluate`.

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
python -m src.cli plan --curriculum data/curricula/demo_curriculum.json --target D --budget 10 --deadline-days 3 --out out/plan_demo
```

**Example input and expected output.** The command above plans the 4-concept demo curriculum (A → B → C → D) for a cold-start learner, target D, 10 minutes a day for 3 days. It prints:

```text
Plan request succeeded. Target: D, Status: FEASIBLE
Policy: using declared default (.../config/bkt_params.yaml)
Artifacts written to 'out/plan_demo'.
```

and writes `out/plan_demo/plan.json` with day 1 = A, B; day 2 = C; day 3 = D (10 of 10 minutes each day; C listed as an assessment candidate), plus `out/plan_demo/trace.json` with 12 entries (4 candidates × 3 days), each with a reason code. With `--budget 8` instead, it prints `Status: INFEASIBLE_PROVED`, and `plan.json` holds the proof instead of days: reason `BLOCK_EXCEEDS_DAILY_BUDGET`, offending concepts C and D, and the minimum fix "raise daily budget to at least 10 minutes" (extra days cannot help).

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

### 4. Integrated Evaluation (`evaluate`)

Run the closed-loop integrated evaluation pipeline:

```bash
python -m src.cli evaluate --config experiments/w8_final.yaml --out out/eval_run --learners 10
```

Options:
- `--config <yaml>`: Path to evaluation YAML configuration (default: `experiments/w5_integrated.yaml`).
- `--out <dir>`: Output directory for `per_learner.csv`, `summary.md`, and `manifest.json` (required).
- `--learners <int>`: Optional override for synthetic learner cohort size.
- `--require-clean`: Optional flag enforcing clean git status on tracked tree (default: enabled when `--out` is under `evaluation/results`, disabled otherwise).

This executes:
1. Validates configuration schema and required benchmark sections.
2. Runs closed-loop integrated evaluation across all primary and ablation planner arms.
3. Records simulated learner histories, prerequisite checks, and budget compliance.
4. Computes paired bootstrap confidence intervals and statistical claim comparisons.
5. Emits `per_learner.csv`, `summary.md`, and SHA-256 `manifest.json`.
6. Prints a concise execution summary reading back from generated output files.



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

## Operational Handover

**Starting and stopping.** There are no services to keep running. The engine is a command-line program (`python -m src.cli ...`) that exits when done. To view the website locally, serve the repository root and open `/site/`:

```bash
python -m http.server 8000      # from the repository root; stop with Ctrl+C
# then open http://localhost:8000/site/
```

Pages read files with `fetch()`, so opening the HTML files directly from disk does not work. The published copy is <https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/> (GitHub Pages builds `main`). `site/build_data.py` regenerates the website's result data from `evaluation/results/w8/final_v2/` and stops if any number differs from the committed result files.

**Where outputs and logs go.** There are no log files; every command prints to the terminal.
- `plan`, `demo`, `slice`: `plan.json`, `trace.json` and the other artifacts in the `--out` folder.
- `evaluate` and `python -m src.evaluation.integrated`: `per_learner.csv`, `summary.md` and `manifest.json` (git SHA, dirty flag, SHA-256 config hash, input paths, output checksums) in the `--out` folder.
- Committed results used in the report: `evaluation/results/` (final runs in `evaluation/results/w8/final_v2/`).

**Resetting.** Delete your own output folders (for example `out/`). Committed results are never overwritten by the examples above. `git checkout -- evaluation/results/` restores any committed result file you changed.

**Common failures.**

| Symptom | Cause | Fix |
|---|---|---|
| `Error: Tracked git tree is dirty and --require-clean is active.` | Output folder is under `evaluation/results/` and a tracked file is modified | Commit or restore your changes, or write to a folder outside `evaluation/results/` (e.g. `out/`), where the clean-tree check is off by default |
| Demos page shows a red "Python engine unavailable" banner and "Saved output" notes | Pyodide could not be downloaded from `cdn.jsdelivr.net` (offline or blocked) | Allow the CDN, or use the saved outputs (`demos.html?fallback`); presets still show real engine output |
| Website pages are empty when opened from disk | Browsers block `fetch()` on `file://` | Serve the repository root with `python -m http.server` as above |
| `ModuleNotFoundError` (e.g. `catsim`, `pyBKT`) | Dependencies not installed in the active environment | `pip install -r requirements.txt` in a Python 3.11 environment |
| `git status` shows `evaluation/results/sample_trace_normal.json` modified after tests | The test suite rewrites this sample trace | `git checkout -- evaluation/results/sample_trace_normal.json` |

**External services and costs.** None required. GitHub Pages hosts the website for free; the Pyodide CDN is used only by the live demos. The clean-clone audit `scripts/clean_run.ps1 -Sha <commit>` is a PowerShell (Windows) script.

## Documentation Index

- `docs/Project_Report.pdf` — Final project report (deliverable A)
- `docs/Architecture_Decision_Records.md` — Decision log, ADR-001 to ADR-022 (deliverable B)

- `docs/PROBLEM_BOUNDARY.md` — Actors, system boundary, in/out of scope
- `ASSUMPTIONS.md` — Documented assumptions and known limitations
- `docs/DATA_STRATEGY.md` — Dataset comparison, primary strategy, unavailable-field handling
- `docs/LITERATURE_REVIEW.md` — Comparative approach analysis (M1-M5 areas)
- `docs/FORMAL_MODELS.md` — Formal learner-state and curriculum graph models
- `docs/METRICS.md` — Initial evaluation metrics
- `TRACEABILITY.md` — Requirement -> Milestone -> Acceptance Test (TC-ID) register
- `/decisions` — Architecture/methodology decision records
