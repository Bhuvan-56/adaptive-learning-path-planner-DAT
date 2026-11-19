# Project Report update: public-data extension (insert text for `docs/Project_Report.pdf`)

The PDF is built from LaTeX source that is not in this repository. This file lists, section by section, what to change so the PDF matches the Week 8 public-data extension. Every number is taken from a committed result file:
- `evaluation/results/w8/assistments_bkt/metrics.txt` (fit);
- `evaluation/results/w8/final_v2/s4_vs_s0.txt` and `pooled_integrated_s4.txt` (S4).

The full write-up is `docs/w8/results_assistments.md`, and the decision record is ADR-023.

---

## Title page / abstract

Replace "evaluated on synthetic learners only" (or similar) with:

> Planning outcomes are simulator behaviour on simulated learners. BKT was also fitted on the public ASSISTments 2009–2010 dataset and tested on 593 held-out students. Scenario S4 repeats the integrated evaluation on simulated learners whose parameters come from those fits.

## §2.3 Reused Open-Source Tools and data (add)

> **ASSISTments 2009–2010 Skill Builder (corrected)**, public dataset (Feng, Heffernan & Koedinger, 2009), used for research under its terms of use. It was used to fit BKT; no curriculum structure was taken from it.

## §3.8 Reproducibility and Provenance (add one sentence)

> Public data has its own provenance record (`data/provenance/assistments_2009_2010.json`): source, acquisition date, SHA-256, field mapping, terms of use, and the row, student and skill count after every cleaning step.

## §4.2 Simulated Learners: Table 8, add a row

| Scenario | Learner model | Bias |
|---|---|---|
| S4 calibrated | BKT; each (learner, concept) draws slip, guess and learn from one of 53 per-skill fits on ASSISTments 2009–2010 students (guess and slip < 0.5). The engine keeps its defaults | Learners differ from what the planner assumes; parameters come from real students; toy curriculum, no forgetting only |

## §4.5 How to Reproduce (add)

```
python scripts/assistments_prepare.py
python scripts/assistments_fit_bkt.py
python -m src.evaluation.integrated --config experiments/w8_s4_assistments.yaml --out out/s4
python scripts/w8_s4_compare.py
```

## §5 Results: new subsection "5.x Public Data: BKT on Real Students and Calibrated Learners (Q7)"

> **Data.** The ASSISTments 2009–2010 Skill Builder corrected file has 346,860 rows. It was cleaned to 196,143 first-attempt answers from 3,958 students in 56 skills: original questions only, single-skill rows, and skills with ≥ 50 students and ≥ 500 rows. It was split by student 70/15/15 (2,771 / 594 / 593).
>
> **Held-out prediction.** One BKT model per skill was fitted on the train students and scored on 27,665 answers from the 593 test students.

| Model | AUC | RMSE | Log loss | ECE |
|---|---|---|---|---|
| BKT fitted per skill | **0.7142** | **0.4411** | **0.5732** | 0.0169 |
| BKT, engine defaults (0.10 / 0.25 / 0.10, prior 0.5) | 0.6807 | 0.4565 | 0.6134 | 0.0694 |
| Per-skill training correct-rate | 0.6208 | 0.4644 | 0.6207 | 0.0087 |
| Majority class | 0.5000 | 0.5839 | 4.7102 | 0.3409 |

> Fitted minus default log loss per test student is −0.0288 [−0.0378, −0.0192], so fitted is better (paired bootstrap, B = 1,000). The fitted slip is about twice the assumed value (median 0.207 against 0.10), and the fitted guess is lower (0.140 against 0.25).
>
> **S4.** This is the toy S0 configuration with learners calibrated to the fits; 1,000 paired learners.

| Paired difference | S0 | S4 |
|---|---|---|
| adaptive − static (= − greedy), mastered | +0.0560 [0.0400, 0.0740] | **+0.0550 [0.0270, 0.0830]** |
| adaptive − static, retained recall | +0.0242 [0.0168, 0.0316] | **+0.0299 [0.0214, 0.0385]** |
| best-singleton − greedy, mastered | +0.0130 [0.0040, 0.0230] | −0.0030 [−0.0240, 0.0200] |
| adaptive − no-diagnostic, mastered | −0.0840 [−0.1110, −0.0580] | −0.0690 [−0.1030, −0.0360] |

> The adaptive advantage holds on calibrated learners. B12 holds too, so it is not an artifact of the matched simulator. The best-singleton integrated gain does not carry over. The engine's mastery calibration worsens (Brier 0.1607 against 0.1358). Hard constraints: 0 prerequisite and 0 budget violations; 100% trace coverage for the primary arms.

## §5.5 Calibration (Q5): add a row to the calibration table

| Run | adaptive_full Brier / ECE | ablation_no_diagnostic Brier / ECE |
|---|---|---|
| Toy S4 (calibrated learners) | 0.1607 [0.1539, 0.1681] / 0.1135 | 0.1817 [0.1747, 0.1891] / 0.1244 |

## §5.6 Hard Constraints (Q6): add "including S4"

## §7.3 Timeline: add a row

| Date | Event |
|---|---|
| 19 Nov 2026 | Public-data extension: ASSISTments 2009–2010 BKT fit with held-out test; scenario S4 (ADR-023) |

## §8 Table 19 (works / partial / missing)

- *Working:* add "BKT fitted on public data (ASSISTments) with held-out test; S4 calibrated-learner scenario".
- *Missing:* replace "Any real or public-data validation" with "real learners using the planner; fitted HLR half-lives; fitted parameters adopted by the engine".

## §8 Table 20: replace the "Validity" row

| ID | Defect / risk | Effect | Workaround |
|---|---|---|---|
| Validity | Simulated learners. S0 matches the planner; S3 favours practice; S4 (real-fit parameters) covers toy, no forgetting only. Hand-made curricula. Engine keeps default BKT parameters although fitted ones predict better | External validity for real learners unknown | Mismatched and calibrated runs; adopting fitted parameters in Section 9 |

## §9 Table 21: update P3 and add P6

| Prio. | Task | Starting point | Risk / dependency | Done when |
|---|---|---|---|---|
| P3 | ~~Validate on a public dataset: fit BKT~~ **done for BKT** (ADR-023); remaining: fit HLR, run S4 under forgetting and on the maths curriculum | `scripts/assistments_*.py`, `src/simulation/calibrated.py` | HLR needs repeated practice with timing | S4 results under S1 forgetting and on the maths curriculum; HLR held-out log loss against the fixed prior |
| P6 | Adopt fitted BKT parameters in the engine (map ASSISTments skills to concepts) | `config/bkt_assistments.yaml`, `config/bkt_params.yaml` | The mapping covers few concepts; changes headline results; must be pre-registered | Calibration under S4 improves; hard constraints unchanged |
