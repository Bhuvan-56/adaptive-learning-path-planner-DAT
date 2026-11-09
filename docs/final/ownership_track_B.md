# Code Explanation and Change Task: Track B (evaluation harness, simulator, retention)

Week 8 replaces `docs/beta/ownership_B.md` (Week 6). That pack names files and signatures that do not exist (`src/diagnostic/cat.py`, `bkt_update(...)`, `SimulatedLearner.generate_response`), and it predates the Week 7 and Week 8 fixes. Everything below matches the code on `main` after Week 8.

**Owner:** Abdur Rehman (AI23BTECH11015), Track B since the start of the project · **Other track (Bhuvan Chandra):** [ownership_track_A.md](ownership_track_A.md)

---

## 1. What one integrated run does

Entry point: `python -m src.evaluation.integrated --config experiments/w8_final.yaml --out <dir>` → `run_integrated_evaluation` → `_evaluate_single_seed` for each seed (`src/evaluation/integrated.py`).

| Step | File | Function | What it does |
|---|---|---|---|
| 1 | `src/evaluation/compare.py` | `generate_synthetic_learners(n, seed, ...)` | θ* ~ N(0, 1) per learner. True starting mastery is `θ* ≥ b_concept` (A −0.20, B −0.20, C 0.15, D 0.50). Diagnostic answers are pre-generated, so every arm sees the same learner. |
| 2 | `src/evaluation/integrated.py` | `make_learner_generator(scenario)` | S0: matched BKT (`p_S 0.10, p_G 0.25, p_T 0.10`). S1: S0 plus forgetting `p_F = 0.05` per day. S2: S0 plus difficulty sensitivity `k = 0.50`. |
| 3 | `src/simulation/simulator.py` | `SimulatedLearner.respond`, `.advance_day`, `.evaluator_view` | `respond` returns only a 0/1 score and may move hidden mastery from 0 to 1 with `p_T`. `advance_day` applies forgetting (no-op, no random draws, when `p_F = 0`). `EvaluatorView` is the only way to read hidden mastery. |
| 4 | `src/evaluation/integrated.py` | arm loops | Adaptive arms (`adaptive_full` and four ablations) call `replan` after every answer. Static arms run one fixed plan. Greedy arms pick each day by score per minute. **Week 8:** every loop calls `advance_day(1)` at the end of each day. |
| 5 | same | `recount_plan_violations` | Recounts prerequisite and budget violations from the executed days, without trusting the planner. |
| 6 | `src/evaluation/retention.py` | `administer_retention_quiz` | After the horizon: advance 7 days, then ask 5 items per studied concept at difficulty 0.5. Gives the retained-recall share. |
| 7 | `src/evaluation/compare.py` | `compute_paired_bootstrap_ci` | Percentile bootstrap, B = 1,000, fixed seed. Paired differences are taken learner by learner. |
| 8 | `src/provenance.py` | `get_git_info`, `resolved_config_hash`, `compute_file_sha256` | `manifest.json`: git SHA, dirty flag, config hash, input and output checksums. |

**Outputs per run:** `per_learner.csv` (one row per learner and arm), `per_learner_seed_<s>.csv`, `summary.md` and `summary_seed_<s>.md`, and `manifest.json`. Five-seed pooled figures come from `scripts/w7_pooled_s0.py <dir> arm_a:arm_b ...`; the summary tables hold seed 42 only.

**Claim rule:** an arm is "better" only if the paired 95% interval of the difference excludes zero. Otherwise the result is "no difference shown".

## 2. Arms

| Arm | Starting state | Planner | Difficulty steps | Replan | Review / remediation |
|---|---|---|---|---|---|
| `adaptive_full` | CAT priors | `replan` | yes | yes | yes / yes |
| `static_prerequisite_order` | CAT priors | `generate_static_plan` | no | no | no |
| `non_adaptive_greedy` | Mastered set only | score per minute | no | daily | no |
| `non_adaptive_greedy_best_singleton` | same | greedy + best single item | no | daily | no |
| `ablation_no_diagnostic` | cold start p = 0.5 | `replan` | yes | yes | yes / yes |
| `ablation_no_replan` | CAT priors | static plan | yes | no | no |
| `ablation_no_difficulty_step` | CAT priors | `replan` | no | yes | yes / yes |
| `ablation_no_review` | CAT priors | `replan` | yes | yes | no / yes |
| `ablation_no_remediation` | CAT priors | `replan` | yes | yes | yes / **yes (bug, see section 5)** |

## 3. Reading order

1. `src/simulation/simulator.py`: `MatchedBKTGenerator`, `SimulatedLearner`, `EvaluatorView`
2. `src/evaluation/compare.py`: `generate_synthetic_learners`, `compute_paired_bootstrap_ci`
3. `src/evaluation/integrated.py`: `_evaluate_single_seed` (arm loops), `recount_plan_violations`, `_build_summary_markdown`
4. `src/evaluation/retention.py`
5. `src/provenance.py`, `scripts/w7_pooled_s0.py`, `scripts/clean_run.ps1`

## 4. Likely questions

**Q1. Why was S1 not a real forgetting test before Week 8?**
The daily loop never called `advance_day`, so forgetting only happened in the retention quiz after the horizon. Week 8 calls it at the end of every day in every arm. The S0 and S2 results cannot change from this: with `p_F = 0` the call draws no random numbers. Test: `tests/test_w7_b1_s1_forgetting.py`.

**Q2. How do you know arms are compared on the same learners?**
Each learner gets a fixed seed (`seed × 1000 + index`) and pre-generated diagnostic answers. Each arm builds a fresh `SimulatedLearner` from that seed. Differences are paired by learner.

**Q3. Why are the ablations identical to `adaptive_full`?**
Three separate reasons.
- Difficulty and review cannot change hidden mastery under S0: the generator ignores difficulty and has no forgetting.
- Remediation never fires in the loop. `get_remediation_ancestors` skips completed ancestors, and in this loop every ancestor of a failing concept has already been completed.
- `ablation_no_remediation` does not switch remediation off at all (section 5).
`ablation_no_diagnostic` differs only in its priors. On the 4-concept curriculum that never changed a schedule.

**Q4. How is cheating (reading hidden mastery) prevented?**
Planning, state and diagnostic code never import `src/simulation` or `src/evaluation`; source-scanning tests check this (`tests/test_simulation.py`). Hidden mastery is read once per learner, at the end, through `EvaluatorView`.

**Q5. What counts as a no-plan day, and what is trace coverage?**
A no-plan day is one whose active plan status is not FEASIBLE at the start of the day; its reason code is recorded. Since Week 7 and Week 8, work listed by a `HEURISTIC_NO_PLAN` plan or a best-effort plan is still executed. A day is trace-valid when its trace passes `check_trace` (and `check_no_plan_trace` for an infeasible plan). Coverage is the share of trace-valid days.

**Q6. How do you reproduce a number?**
Run the config named in the results doc with the command above. Compare `per_learner.csv` with the committed file (all columns except `runtime_ms`). Check the git SHA and config hash in `manifest.json`.

## 5. Change task (do it live, about 30 minutes)

**Task:** make `ablation_no_remediation` actually disable remediation. Today it runs exactly the same code as `adaptive_full`: no line in `src/` checks the arm name except the shared list of adaptive arms.

- `src/planning/replan.py`: add `remediation_enabled: bool = True` to `ReplanState` and read it in `_extract_state` (both branches). When it is False, skip the k-failures trigger, so `remediation_ancestors` stays empty.
- `src/evaluation/integrated.py`: build `ReplanState` with `remediation_enabled=(arm != "ablation_no_remediation")`.
- New test `tests/test_remediation_ablation.py`, with two parts:
  1. `replan` on the demo curriculum: A not completed and not Mastered, B failed twice. With remediation on, A is SELECTED with `REMEDIATION_TRIGGERED`. With `remediation_enabled=False`, no entry has that reason.
  2. A spy on `get_remediation_ancestors` during a 3-learner integrated run shows zero calls for the `ablation_no_remediation` arm.
- Done when the new test passes and the full suite still passes. Then re-run integrated S0 and check `ablation_no_remediation` against the committed `evaluation/results/w8/final/integrated_s0/`. Expect no change, because of Q3; say so.

What to explain while doing it:

- why the arm was identical before the change;
- why the numbers still do not move afterwards;
- what a curriculum or event sequence would need for remediation to matter (an ancestor that is not completed when a dependent fails twice, for example after a missed or skipped prerequisite).
