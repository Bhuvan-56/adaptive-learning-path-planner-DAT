# Week 8 Results (public-data extension): ASSISTments 2009–2010 Fit and the S4 Scenario

This extension carries out the report's way-forward task P3, "validate on a public dataset: fit BKT … check calibration", for BKT. HLR was **not** fitted. Decision record: ADR-023 in [`docs/Architecture_Decision_Records.md`](../Architecture_Decision_Records.md).

**Not pre-registered.** The design was fixed before the S4 run and is written in the docstring of `src/simulation/calibrated.py`: the filter rule (guess < 0.5 and slip < 0.5), the engine's parameters left unchanged, and initial mastery from the harness. That design was not committed as a separate pre-registration. As with the other Week 8 final fixes, this is a disclosed deviation from ADR-013.

| Step | Code | Output |
|---|---|---|
| 1. Provenance record and cleaning | `scripts/assistments_prepare.py` | `data/provenance/assistments_2009_2010.json`; `data/processed/assistments/{train,dev,test}.csv` (git-ignored, rebuilt by the script) |
| 2. Per-skill BKT fit and held-out test | `scripts/assistments_fit_bkt.py` | `config/bkt_assistments.yaml`; `evaluation/results/w8/assistments_bkt/metrics.txt`, `per_skill.csv` |
| 3. Scenario S4: learners calibrated to the fits | `src/simulation/calibrated.py`; `src/evaluation/integrated.py` (`make_learner_generator`); `tests/test_w8_s4_calibrated.py` | `experiments/w8_s4_assistments.yaml` |
| 4. Integrated run and comparison with S0 | `python -m src.evaluation.integrated`; `scripts/w7_pooled_s0.py`; `scripts/w8_s4_compare.py` | `evaluation/results/w8/final_v2/integrated_s4/`, `pooled_integrated_s4.txt`, `s4_vs_s0.txt` |

## 1. Data

**Source.** ASSISTments 2009–2010 Skill Builder, **corrected** version, `skill_builder_data_corrected_collapsed.csv`, from the official data page <https://sites.google.com/site/assistmentsdata/home/2009-2010-assistment-data/skill-builder-data-2009-2010>. The page says the original release contains duplicate records. Acquired 19 November 2026. SHA-256 `162ef8d2…a6e5da`; the full hash is in the provenance record. Use is for research and education under the dataset's terms of use. Citation: Feng, Heffernan & Koedinger (2009). The raw file is not committed (`data/raw/` is git-ignored).

**Cleaning.** Each step's count is recorded in the provenance record:

| Step | Rows | Students | Skills |
|---|---|---|---|
| Raw file | 346,860 | 4,217 | – |
| `original == 1` (scaffolding sub-questions removed) | 275,458 | 4,217 | 101 |
| `skill_name` present | 251,405 | 4,151 | 101 |
| Single-skill rows only (the corrected file merges multi-skill problems into one id such as `1_13`) | 206,578 | 3,991 | 92 |
| First attempt per (student, problem) | 203,723 | 3,991 | 92 |
| Skills with ≥ 50 students and ≥ 500 rows | **196,143** | **3,958** | **56** |

- **Split:** by student, 70 / 15 / 15, seed 20261119. The splits hold 2,771 train, 594 dev and 593 test students, with 135,569, 32,909 and 27,665 rows. No student appears in two splits, and each learner's answers stay in time order (`order_id`).
- **Encoding:** the raw file is not valid UTF-8, so it is read as latin-1.
- **What the data does not have:** prerequisite fields. No curriculum edges come from this dataset; both project curricula stay hand-made. The timing field (`ms_first_response`) is kept but not used.

## 2. BKT fitted on real students

Standard 4-parameter BKT, one model per skill, fitted with pyBKT (EM, 5 restarts, seed 20261119, forgetting off) on **train students only**. It is scored on the 593 **test** students with the BKT forward pass: p(correct) is predicted before each answer from that learner's earlier answers. Source: `evaluation/results/w8/assistments_bkt/metrics.txt`.

| Model, 27,665 test answers | AUC | RMSE | Accuracy | Log loss | ECE |
|---|---|---|---|---|---|
| **BKT, fitted per skill** | **0.7142** | **0.4411** | **0.7072** | **0.5732** | 0.0169 |
| BKT, engine defaults (`p_S` 0.10, `p_G` 0.25, `p_T` 0.10, prior 0.5) | 0.6807 | 0.4565 | 0.6959 | 0.6134 | 0.0694 |
| Each skill's training correct-rate (no learning) | 0.6208 | 0.4644 | 0.6624 | 0.6207 | 0.0087 |
| Training majority class | 0.5000 | 0.5839 | 0.6591 | 4.7102 | 0.3409 |

- **Fitted beats the engine's defaults** on held-out log loss, per test student: **−0.0288 [−0.0378, −0.0192]**, fitted better (paired bootstrap over 593 students, B = 1,000). This is exactly the ADR-001 revisit trigger; ADR-023 records what was decided.
- **Fitted beats the per-skill average** on AUC, RMSE, accuracy and log loss. Its RMSE is lower in 48 of 56 skills (`per_skill.csv`).
- **Calibration:** the fitted model's ECE (0.0169) is much lower than the engine defaults' (0.0694). The per-skill average has the lowest ECE (0.0087), because a constant equal to the training mean is close to calibrated by construction; it discriminates poorly (AUC 0.6208).
- **Scale:** an AUC around 0.71 is in the range usually reported for plain BKT on this dataset. This figure is from this split only.

**Fitted parameters against what the project assumed** (median [min, max] over 56 skills):

| Parameter | Fitted on ASSISTments | Engine and simulator S0 |
|---|---|---|
| Slip `p_S` | 0.207 [0.040, 0.494] | 0.10 |
| Guess `p_G` | 0.140 [0.000, 0.720] | 0.25 |
| Learn `p_T` | 0.117 [0.000, 0.858] | 0.10 |
| Prior | 0.685 [0.328, 0.993] | 0.5 (cold start) |

Real students in this data slip about twice as often as assumed, guess less, and vary widely between skills; the simulator used one value for every concept. A few fits are poorly identified, for example guess 0.72 for *Ordering Integers* or learn 0.86 for *Write Linear Equation from Situation*. This is a known weakness of BKT's EM fit.

## 3. Scenario S4: learners calibrated to real students

**Generator.** `CalibratedBKTGenerator` uses S0's response and learning rule (k = 0, no forgetting). Each (learner, concept) pair draws its own slip, guess and learn triple from the 53 skill fits with guess < 0.5 and slip < 0.5; three fits are excluded. The draw depends only on (learner seed, concept), through its own random-number generator, so:
- every arm sees identical learners, and the paired design holds;
- the learner's response stream is unchanged.

**Unchanged on purpose.**
- *The engine's BKT parameters* (0.10 / 0.25 / 0.10). S4 tests the planner on learners whose dynamics differ from what it assumes.
- *Initial latent mastery* (θ* ≥ b_c, as in S0). The ASSISTments prior describes students already taught in class, not this scenario.
- *Everything else in the configuration.* `experiments/w8_s4_assistments.yaml` is `experiments/w8_final.yaml` (final_v2 S0) with only the active scenario changed: toy curriculum, 5 seeds × 200 learners, 5 days × 10 minutes, target D.

### 3.1 Hard constraints: passed

0 prerequisite violations and 0 budget violations in all 9 arms. Trace coverage is 100% for the four primary arms in all five per-seed summaries (`evaluation/results/w8/final_v2/s4_vs_s0.txt`).

### 3.2 Results (`evaluation/results/w8/final_v2/s4_vs_s0.txt`, `pooled_integrated_s4.txt`)

Paired differences *within* each run (1,000 learners, B = 1,000):

| Paired difference | Metric | S0 (final_v2) | **S4** | Claim |
|---|---|---|---|---|
| adaptive_full − static_prerequisite_order | mastered | +0.0560 [0.0400, 0.0740] | **+0.0550 [0.0270, 0.0830]** | adaptive better in both |
| adaptive_full − static_prerequisite_order | retained recall | +0.0242 [0.0168, 0.0316] | **+0.0299 [0.0214, 0.0385]** | adaptive better in both |
| adaptive_full − non_adaptive_greedy | mastered / recall | identical to the static row | identical to the static row | adaptive better in both |
| best_singleton − greedy | mastered | +0.0130 [0.0040, 0.0230] | **−0.0030 [−0.0240, 0.0200]** | better → **no difference shown** |
| adaptive_full − ablation_no_diagnostic | mastered | −0.0840 [−0.1110, −0.0580] | **−0.0690 [−0.1030, −0.0360]** | no-diagnostic better in both (B12) |
| adaptive_full − ablation_no_diagnostic | retained recall | −0.0381 [−0.0476, −0.0283] | −0.0240 [−0.0345, −0.0130] | no-diagnostic better in both |
| adaptive_full − ablation_no_review | mastered | −0.0010 [−0.0030, 0.0000] | 0.0000 [0.0000, 0.0000] | no difference shown |

Per arm:

| Arm | Mastered S0 → S4 | Retained recall S0 → S4 | No-plan days S0 → S4 | Mastery Brier / ECE, S0 → S4 |
|---|---|---|---|---|
| adaptive_full | 2.0920 → 2.2470 | 0.6604 → 0.5922 | 623 → 734 / 5,000 | 0.1358 / 0.0821 → **0.1607 [0.1539, 0.1681] / 0.1135** |
| static_prerequisite_order | 2.0360 → 2.1920 | 0.6362 → 0.5624 | 0 → 0 | not applicable |
| non_adaptive_greedy | 2.0360 → 2.1920 | 0.6362 → 0.5624 | 0 → 0 | not applicable |
| non_adaptive_greedy_best_singleton | 2.0490 → 2.1890 | 0.6382 → 0.5651 | 0 → 0 | not applicable |
| ablation_no_diagnostic | 2.1760 → 2.3160 | 0.6985 → 0.6163 | 1,000 → 1,000 | 0.1462 / 0.0641 → 0.1817 [0.1747, 0.1891] / 0.1244 |

### 3.3 Observations

1. **The headline claim survives calibrated learners.** adaptive_full beats both baselines on mastery and on retained recall, by almost the same amount as in S0. The interval is wider because S4 learners differ from each other.
2. **B12 is not an artifact of the matched simulator.** The cold-start ablation still beats adaptive_full.
3. **The engine's mastery estimates are less calibrated** when learners do not behave as it assumes. adaptive_full's Brier score rises from 0.1358 to 0.1607 and ECE from 0.0821 to 0.1135. This is the expected cost of keeping the default parameters (ADR-023).
4. **The best-singleton fallback's integrated gain does not carry over.** Under S0 it was +0.0130; under S4, as under S1, it shows no difference. Its scheduling-benchmark gain (§4.1 of the final report) is unaffected.
5. **The review ablation equals adaptive_full on mastery.** This is expected, because S4 has no forgetting, like S0.
6. **Not comparable across the two columns:** absolute levels and runtimes. S0 and S4 learners are different people, so only the within-run differences are paired. Runtimes were about 4× higher in the S4 run (`pooled_integrated_s4.txt`), from one run on a laptop under other load; they are not a measurement of S4.

## 4. What this does and does not support

- **Supported:**
  - the engine's model family (BKT) predicts real students' held-out answers better than simple baselines;
  - fitted parameters predict better than the engine's defaults;
  - the adaptive arm's advantage holds on simulated learners whose parameters come from real-student fits.
- **Not supported:**
  - any claim about real learners using the planner (no learner used it);
  - curriculum structure from data (ASSISTments has no prerequisites);
  - fitted HLR half-lives (not attempted);
  - anything about the maths curriculum or S1 under calibrated learners (S4 was run on the toy curriculum without forgetting only).

## 5. Reproduce

```bash
# raw file in data/raw/skill_builder_data_corrected_collapsed.csv (see data/README.md)
python scripts/assistments_prepare.py
python scripts/assistments_fit_bkt.py                  # resumable; --max-seconds N stops early
python -m pytest tests/test_w8_s4_calibrated.py -q
python -m src.evaluation.integrated --config experiments/w8_s4_assistments.yaml --out out/s4
python scripts/w7_pooled_s0.py out/s4 adaptive_full:static_prerequisite_order adaptive_full:non_adaptive_greedy non_adaptive_greedy_best_singleton:non_adaptive_greedy adaptive_full:ablation_no_diagnostic adaptive_full:ablation_no_review
python scripts/w8_s4_compare.py
```

The fit was run under Linux Python 3.10 with the project's pyBKT 1.4.3 copy (`parallel=False`, which the script sets); the integrated S4 run used the project's Windows `.venv`. Per-learner CSVs should match `evaluation/results/w8/final_v2/integrated_s4/` on all columns except `runtime_ms`. **Checked:** S4 was run twice, first under the config's earlier name, then as `experiments/w8_s4_assistments.yaml`. All five per-seed CSVs are identical in every column except `runtime_ms`. The second run is the canonical `integrated_s4/`; the first is kept in `integrated_s4_first_run/` with a README.
