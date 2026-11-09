# Limitations (final, Week 8)

What the project does **not** show, and known defects that are still open at the end of Week 8. Each item names where the evidence is. Fixed items are listed at the end so the history is complete.

## A. What the evidence can and cannot support

1. **Synthetic learners only.** Every outcome comes from a simulator. No real learner data was collected (scope: `docs/PROBLEM_BOUNDARY.md`). No claim about real learning gains is made.
2. **The simulator matches the planner's own model.** S0 and S1 use a BKT generator with the same `p_S`, `p_G` and `p_T` as the learner-state model (`src/evaluation/integrated.py`, `make_learner_generator`). The planner is therefore tested on learners that behave exactly as it assumes, which is the most favourable case. The mismatched PFA generator (S3 in `experiments/w5_final.yaml`) was specified but never run in the integrated harness.
3. **Small curriculum.** All integrated results use the 4-concept demo curriculum (A, B, C, D), 5 days and a 10-minute budget. Several mechanisms (remediation, diagnostic priors, best-effort plans) never change a schedule at this size (section B). The larger curriculum planned for the final demo was not built.
4. **S2 (difficulty-sensitive) is not verified.** It was not rerun after the Week 7 and Week 8 fixes. Week 6 S2 tables show S0 figures; whether difficulty sensitivity reaches the outcome was never checked (`weekly/W7.md`, correction to the Week 6 record).
5. **σ² is a proxy.** `σ² = p(1−p)/(κ+1)` counts evidence. It is not a calibrated Bayesian credible interval (`decisions/ADR-005-uncertainty-representation.md`).
6. **HLR half-life is a fixed prior** (14 days, `experiments/m8_learner_eval.yaml`, read by `src/planning/review.py`), not fitted to data.
7. **Runtimes** come from one Windows laptop and one run per configuration.

## B. Known open defects and behaviours

| # | Item | Effect | Evidence |
|---|---|---|---|
| B1 | `ablation_no_remediation` does not disable remediation: no code checks the arm name | That ablation measures nothing; it equals adaptive_full by construction | `docs/w8/results.md` §5; change task in `docs/final/ownership_track_B.md` |
| B2 | Remediation never fires in the closed loop: `get_remediation_ancestors` skips completed ancestors, and every ancestor of a failing concept is completed | Remediation is tested only by unit tests, never in an integrated run | `src/planning/review.py`; `docs/w8/results.md` §5 |
| B3 | All four replan ablations equal adaptive_full under S0 and S1 | No component of the adaptive arm can be credited separately; only the whole arm against the baselines | `docs/w8/results.md` §5; `docs/w7/deadlock_fix_results.md` |
| B4 | adaptive_full still has 1,000 / 5,000 no-plan days (`SCHEDULING_CONSTRAINTS_UNMET`) in S0 and S1 | The listed work is still executed, so the count says how often the plan could not reach the target by the deadline, not idle days | `evaluation/results/w8/final/` summaries |
| B5 | The CAT stopping rule `Var(θ̂) ≤ 0.15` never fires with the 24-item bank; every diagnostic uses all 10 items | The stopping code is effectively dead; diagnostic length is fixed | `docs/beta/a3_cat_stopping.md` |
| B6 | `generate_static_plan` fills days in a fixed topological order and can miss a plan that exists | 3 of 3,000 random demo requests | `docs/w7/deadlock_fix_results.md` |
| B7 | `generate_static_plan` has no best-effort plan: an infeasible first request gives the static arms no work | Only the adaptive arms use the Week 8 best-effort plan; by design, so the baseline stays unchanged | `docs/w8/preregistration.md` |
| B8 | Greedy score-per-minute is not optimal; the best-singleton fallback does not fix every case (12/18 stays 12) | Scheduling ratio to the oracle below 1 on some instances; the fallback's integrated gain under S0 (+0.0130) is gone under S1 | `tests/fixtures/w7/bad_cases.json`; `docs/w8/results.md` §3 |
| B9 | Under S1 the planner does not model forgetting: a concept is not re-planned because of time passing, only through spaced review | Mastery lost between days is only recovered if a review happens to be due | `src/planning/replan.py`; `docs/w8/results.md` §3 |

## C. Fixed during the project (for the record)

| Item | Fixed in | Evidence |
|---|---|---|
| Adaptive deadlock on Uncertain/Weak completed prerequisites (4,000 / 5,000 no-plan days) | Week 7 | `docs/w7/deadlock_fix_results.md` |
| Weak prerequisite planned earlier still blocked dependents | Week 7 | same |
| Multi-seed harness ran seed 42 only | Week 6 | `docs/beta/beta_report.md` |
| S1 never applied daily forgetting in the study loop | Week 8 | `docs/w8/results.md` §3 |
| Planner idled when the deadline could no longer be met | Week 8 | `docs/w8/results.md` §4 |
