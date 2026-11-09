# Week 8 Results: S1 Daily Forgetting and Best-Effort Infeasible Days

Pre-registration: [`docs/w8/preregistration.md`](preregistration.md) (commit `ace6b00`, addendum `aad3c4d`). Fixes: `72b8f02` (S1), `840a12b` (best effort). All figures are simulator behaviour on synthetic learners: 1,000 paired learners (5 seeds × 200), 5 days, 10-minute budget, B = 1,000 paired bootstrap resamples.

| Run | Config | Code | Output |
|---|---|---|---|
| S1 before | `experiments/w8_final_s1.yaml` | `ace6b00` (pre-fix) | `evaluation/results/w8/before/integrated_s1/` |
| S1 after | `experiments/w8_final_s1.yaml` | `840a12b` | `evaluation/results/w8/final/integrated_s1/` |
| S0 after | `experiments/w8_final.yaml` | `840a12b` | `evaluation/results/w8/final/integrated_s0/` |

Commands: `python scripts/w7_pooled_s0.py <dir> adaptive_full:static_prerequisite_order adaptive_full:non_adaptive_greedy non_adaptive_greedy_best_singleton:non_adaptive_greedy` (per-arm figures) and `python scripts/w8_s1_compare.py <before> <after>` (paired before/after).

## 1. Hard constraints

0 prerequisite violations and 0 budget violations in every arm of all three runs. Trace coverage is 100% in every arm (per-seed `summary_seed_*.md`). **Passed.**

## 2. S0: unchanged, as predicted

All 9,000 rows of `evaluation/results/w8/final/integrated_s0/per_learner_seed_*.csv` are equal to `evaluation/results/w7/deadlock_fix/integrated_s0/`, every column except `runtime_ms`. With `p_F = 0`, `advance_day` returns at once and draws no random numbers. No S0 day had reason `INFEASIBLE_PROVED`, so the best-effort path never ran. The Week 7 S0 figures stand: adaptive_full 2.1760 [2.0800, 2.2680]; adaptive_full minus static_prerequisite_order +0.1400 [0.1110, 0.1690].

## 3. S1: forgetting now acts during the horizon

Before the fix, S1 mastered figures were identical to S0 in every arm (for example adaptive_full 2.1760 in both). This confirms the Week 7 correction: Week 6 and Week 7 S1 never tested forgetting during study.

Concepts mastered, paired after minus before (same learners):

| Arm | Before | After | After − before [95% CI] |
|---|---|---|---|
| adaptive_full | 2.1760 | 1.7300 | −0.4460 [−0.4940, −0.4000] |
| static_prerequisite_order | 2.0360 | 1.5870 | −0.4490 [−0.4940, −0.4020] |
| non_adaptive_greedy | 2.0360 | 1.5940 | −0.4420 [−0.4880, −0.3930] |
| non_adaptive_greedy_best_singleton | 2.0490 | 1.5900 | −0.4590 [−0.5071, −0.4100] |

The four replan ablations equal adaptive_full, and ablation_no_replan equals static_prerequisite_order, both before and after (section 5). As predicted, every arm loses mastery.

Arm comparisons after the fix (S1):

| Comparison | Concepts mastered [95% CI] | Retained recall [95% CI] | Claim |
|---|---|---|---|
| adaptive_full − static_prerequisite_order | +0.1430 [0.1000, 0.1830] | +0.0383 [0.0279, 0.0481] | adaptive_full better on both |
| adaptive_full − non_adaptive_greedy | +0.1360 [0.0860, 0.1830] | +0.0362 [0.0243, 0.0472] | adaptive_full better on both |
| best_singleton − non_adaptive_greedy | −0.0040 [−0.0190, 0.0130] | n/a | no difference shown |

Per arm after the fix:
- adaptive_full: 1.7300 [1.6490, 1.8190], retained recall 0.5542, 1,000 / 5,000 no-plan days (all `SCHEDULING_CONSTRAINTS_UNMET`);
- static_prerequisite_order: 1.5870 [1.5010, 1.6740], retained recall 0.5159;
- non_adaptive_greedy: 1.5940 [1.5050, 1.6820], retained recall 0.5180.

Two findings:
- **The adaptive advantage holds under forgetting.** It is about the same size as under S0 (+0.1430 against +0.1400), and adaptive_full also keeps more after the 7-day delay.
- **The best-singleton gain disappears under S1.** Under S0 the pooled gain was +0.0130 [0.0040, 0.0230]; under S1 it is −0.0040 [−0.0190, 0.0130], no difference shown. The Week 7 decision to keep it opt-in, not default, is supported.

## 4. Best-effort plan on deadline-infeasible days

- **Unit and integration tests** (`tests/test_w8_best_effort.py`, failing before the fix: `evaluation/results/w8_evidence/before_fix2_best_effort.txt`):
  - a capacity-infeasible request still reports `INFEASIBLE_PROVED` with its fixes, and now plans B on day 1 and C on day 2;
  - best-effort days never break a prerequisite;
  - a block longer than the budget still gets no partial plan;
  - in a 2-day integrated run (30 minutes of work, 20 of capacity), adaptive_full did no work at all before the fix and now works, with 0 violations and 100% trace coverage.
- **S0 and S1 runs:** no effect, as predicted. No day in either run had reason `INFEASIBLE_PROVED`, because the 5-day, 10-minute setting leaves enough capacity for 30 minutes of work. The effect is shown by the tests only.

## 5. Ablations, and a harness bug

Even under S1, all four replan ablations give the same per-learner results as adaptive_full. The reasons:

- **no_difficulty_step:** the generator ignores difficulty (k = 0 in S0 and S1).
- **no_review:** a review needs an evidence-Mastered concept with HLR recall below 0.85. With a 14-day half-life, that takes about 3.3 days since its last practice, so it rarely fits in a 5-day horizon. When it does fit, a review is a scored answer that does not change hidden mastery in the generator.
- **no_diagnostic:** cold-start and CAT priors led to the same schedules on this 4-concept curriculum.
- **no_remediation:** **harness bug.** No line in `src/` switches remediation off for this arm, so it runs the same code as adaptive_full. Remediation also never fires in the closed loop: `get_remediation_ancestors` skips completed ancestors, and every ancestor of a failing concept is already completed. Fixing the arm would therefore not change the numbers. It is listed as an open limitation and is the Track B change task (`docs/final/ownership_track_B.md`).

## 6. Deviations from the pre-registration (disclosed)

- **Implementation of change 2:** the pre-registration said the day-filling loop would move into a helper. Instead, the infeasibility check now stores the no-plan result, and the same loop runs below it, so the loop is not duplicated. The feasible path is unchanged; the full suite passes (271 passed).
- **"Before" manifest:** the S1 before run started on `ace6b00`. Python had loaded the code before the fixes were committed, but the run reads the git SHA when it finishes, so its `manifest.json` says `840a12b`. The run was repeated in a separate checkout pinned at `ace6b00`; the repeat's per-learner files are identical (all columns except `runtime_ms`) and its manifest records `ace6b00`. That repeat's manifest is saved as `evaluation/results/w8/before/integrated_s1/manifest_pinned_ace6b00.json`.

## Decision

Keep both fixes as the default behaviour. The hard constraints hold; S0 is unchanged; S1 now measures forgetting during study; and the adaptive advantage holds there on mastery and retained recall. The best-effort plan only adds work where the planner used to idle. The remediation ablation bug and the identical ablations are reported as limitations (`docs/final/LIMITATIONS.md`).
