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
