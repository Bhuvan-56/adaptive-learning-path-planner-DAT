# Data Directory

This directory holds dataset definitions, raw downloaded logs, and processed outputs used by the Adaptive Learning and Path-Planning Engine.

## Strategy Pointer
For complete theoretical documentation on dataset strategy, synthetic learner simulation, student-level train/dev/test splits (70/15/15), and missing field handling, see [`docs/DATA_STRATEGY.md`](../docs/DATA_STRATEGY.md).

## Datasets & Licensing

1. **Junyi Academy Learning Activity Dataset**
   - **Licensing:** Commercial use is strictly not permitted per published dataset authorization. Restricted to non-commercial, academic research.
   - **Used Fields:** Exercise ID, prerequisite relationships, topic metadata, correctness (`is_correct`), `time_done`, `time_taken` (seconds), attempts, hints, and proficiency.
   - **Primary Application:** Supplies the foundational Directed Acyclic Graph (DAG) for the curriculum (nodes, prerequisite edges), baseline activity durations ($L_c = \frac{\text{median}(time\_taken_c) \times N_c}{60}$), and empirical parameters for BKT, IRT, and HLR models.

2. **ASSISTments 2009–2010 Skill Builder Dataset**
   - **Licensing:** Free to use for research and educational purposes per the official ASSISTments data page.
   - **Used Fields:** Student ID, problem ID, correctness (`correct`), skill ID/name, opportunity count, attempts, hints, and response timing.
   - **Primary Application:** Used as an independent learner-response benchmark for BKT robustness evaluation and response modeling. No cross-dataset prerequisite edges are fabricated between ASSISTments and Junyi.

## Folder Conventions

- **`data/raw/`**: Storage location for original, untouched dataset downloads (e.g., Junyi CSVs, ASSISTments Skill Builder CSVs). Untouched raw data files are excluded from version control via `.gitignore`.
- **`data/processed/`**: Output directory for cleaned datasets, student-split logs (70% train, 15% dev, 15% test), extracted curriculum DAG JSON definitions, pre-calculated median durations, and fitted model weights.

## Dataset Provenance

For each dataset release used by the project, this file records:

- dataset name and exact release;
- download/acquisition source;
- acquisition date;
- content hash;
- field mapping;
- timing units;
- prerequisite information;
- access/usage terms.

Before use, the selected Junyi Academy and ASSISTments releases must be checked for the actual availability of prerequisite and timing fields.

If a required field is unavailable, its fallback must be explicitly labelled as one of:

- manual annotation;
- deterministic engineering assumption; or
- synthetic simulator value.

Such fields must not be presented as measured properties of the original dataset.

## ASSISTments 2009–2010 (used, Week 8 public-data extension)

- **File:** `data/raw/skill_builder_data_corrected_collapsed.csv`, the **corrected** Skill Builder release. Download it from the official page <https://sites.google.com/site/assistmentsdata/home/2009-2010-assistment-data/skill-builder-data-2009-2010> ("corrected version"; direct link <https://drive.google.com/file/d/1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE/view?usp=sharing>). Not committed.
- **Provenance:** `data/provenance/assistments_2009_2010.json` records:
  - source, link and acquisition date (2026-11-19);
  - SHA-256;
  - encoding (not valid UTF-8; read as latin-1);
  - field mapping and terms of use;
  - citation;
  - every cleaning step's counts;
  - the student split and per-skill counts.
- **Processed:** `scripts/assistments_prepare.py` writes `data/processed/assistments/{train,dev,test}.csv` (git-ignored; rebuilt by the script). Rules:
  - `original == 1`, skill present, single-skill rows, first attempt per (student, problem);
  - skills with ≥ 50 students and ≥ 500 rows;
  - split 70/15/15 by student, seed 20261119.
- **Prerequisite fields:** none in this dataset, so no curriculum edges are taken from it. **Timing:** `ms_first_response` is kept but unused.
- **Use:** per-skill BKT fit on train students only (`scripts/assistments_fit_bkt.py` → `config/bkt_assistments.yaml`) and simulator scenario S4. See `docs/w8/results_assistments.md`.
- **Junyi Academy:** not used.
