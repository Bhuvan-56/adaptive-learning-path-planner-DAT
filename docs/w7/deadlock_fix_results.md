# Week 7 Results: adaptive deadlock fix

Pre-registration: `docs/w7/preregistration_deadlock_fix.md` (commit `0a0ae92`, before any code change; one disclosed amendment after the first run).
Code: `c5d1a8f` (fix) and `963c71c` (trace bookkeeping in the loop). Reverses decision D1 ("documented limit", `docs/beta/beta_report.md`).
All results describe simulator behaviour on synthetic learners only (S0, `MatchedBKTGenerator`).

## What was wrong

A concept studied once stays Uncertain (`min_obs` 3), and Mastered needs a full window of 4 answers. `replan` never scheduled a completed concept again unless it was Mastered (spaced review), yet a completed Uncertain or Weak concept kept blocking every dependent. No new evidence could arrive, so the adaptive plan stalled after day 1 for every learner: 4,000 of 5,000 adaptive days were no-plan days.

## What changed

1. `replan`: a completed prerequisite that is still Uncertain or Weak and blocks remaining work gets one practice block (new reason code `PRACTICE_FOR_EVIDENCE`). Daily order: remediation, practice for evidence, planned work, due reviews.
2. `replan` and `generate_static_plan`: a prerequisite planned or practised on an earlier day of the same plan satisfies the gate conditionally (revalidated before execution), also when it is Weak. Same-day use of a Weak or just-practised prerequisite stays blocked.
3. `src/evaluation/integrated.py` adaptive loop: runs the work a `HEURISTIC_NO_PLAN` plan lists for the day, carries each day's trace into `ReplanState.past_trace`, and validates list traces with `check_trace`. The no-plan-day metric definition is unchanged.

## Integrated S0 (5 seeds × 200 learners = 1,000, 5 days, 10-minute budget, B = 1000)

Figures from `scripts/w7_deadlock_fix_compare.py evaluation/results/w7/improvement/integrated_s0 evaluation/results/w7/deadlock_fix/integrated_s0` (method of `scripts/w7_pooled_s0.py`).

| Arm | Mastered [95% CI] | No-plan days | Prereq viol. | Budget viol. | Trace coverage | Before fix: mastered / no-plan |
|---|---|---|---|---|---|---|
| adaptive_full | 2.1760 [2.0800, 2.2680] | 1,000 / 5,000 | 0 | 0 | 100.0% | 1.9340 / 4,000 |
| static_prerequisite_order | 2.0360 [1.9360, 2.1400] | 0 / 5,000 | 0 | 0 | 100.0% | identical |
| non_adaptive_greedy | 2.0360 [1.9360, 2.1400] | 0 / 5,000 | 0 | 0 | 100.0% | identical |
| non_adaptive_greedy_best_singleton | 2.0490 [1.9510, 2.1510] | 0 / 5,000 | 0 | 0 | 100.0% | identical |
| ablation_no_diagnostic | 2.1760 [2.0800, 2.2680] | 1,000 / 5,000 | 0 | 0 | 100.0% | 1.9340 / 4,000 |
| ablation_no_replan | 2.0360 [1.9360, 2.1400] | 0 / 5,000 | 0 | 0 | 100.0% | identical |
| ablation_no_difficulty_step | 2.1760 [2.0800, 2.2680] | 1,000 / 5,000 | 0 | 0 | 100.0% | 1.9340 / 4,000 |
| ablation_no_review | 2.1760 [2.0800, 2.2680] | 1,000 / 5,000 | 0 | 0 | 100.0% | 1.9340 / 4,000 |
| ablation_no_remediation | 2.1760 [2.0800, 2.2680] | 1,000 / 5,000 | 0 | 0 | 100.0% | 1.9340 / 4,000 |

Source: `evaluation/results/w7/deadlock_fix/integrated_s0/per_learner_seed_*.csv`; trace coverage from `summary_seed_*.md` (100.0% for every arm in all five seeds); "before" from `evaluation/results/w7/improvement/integrated_s0/`.

Paired mastered differences (1,000 learners):

| Comparison | Difference [95% CI] | Learners changed | Claim |
|---|---|---|---|
| adaptive_full fixed − before | +0.2420 [0.2110, 0.2740] | 204 (+204 / −0) | better |
| adaptive_full (fixed) − static_prerequisite_order | +0.1400 [0.1110, 0.1690] | 194 (+156 / −38) | better |
| adaptive_full (fixed) − non_adaptive_greedy | +0.1400 [0.1110, 0.1690] | 194 (+156 / −38) | better |

Before the fix, adaptive_full − static was −0.1020 [−0.1210, −0.0830] (static better). The four replan ablations change exactly as adaptive_full does (+0.2420 [0.2110, 0.2740], 204 learners each).

Sanity (pre-registered): static_prerequisite_order, non_adaptive_greedy, non_adaptive_greedy_best_singleton and ablation_no_replan equal the W7 improvement run in every per-learner column except `runtime_ms` (checked by the compare script).

## Against the pre-registered expectations

| Expectation | Result | Matched? |
|---|---|---|
| adaptive_full no-plan days well below 4,000 / 5,000 | 1,000 / 5,000: exactly one per learner, the last day, when the remaining concepts no longer fit (`SCHEDULING_CONSTRAINTS_UNMET`); that day's listed work is still done | yes |
| Mastery direction against static not predicted | adaptive_full better than static: +0.1400 [0.1110, 0.1690] | (no prediction) |
| Hard constraints: 0 prerequisite, 0 budget violations, 100% trace coverage | met in the reported run; the first run had 40% trace coverage (see the amendment) | yes, after the disclosed loop bookkeeping fix |

## Runtime (trade-off, no claim)

adaptive_full per learner over 5 days, p50 / p95: 21.44 / 45.69 ms (this run) against 13.35 ms p50 in the W7 improvement run (`docs/w7/comparison.md`). The planner now replans many more non-empty days. Runtime moves a lot between runs; only within-run comparisons are meaningful.

## Limits and open points

- Synthetic learners only; S0 only. The S1 forgetting defect (`tests/test_w7_b1_s1_forgetting.py`, strict xfail) is still open.
- All four replan ablations give results identical to adaptive_full, before and after the fix. For difficulty and review this is the known simulator property (it ignores difficulty and has no forgetting). For `ablation_no_diagnostic` and `ablation_no_remediation` it means the diagnostic priors and remediation never change a schedule on this 4-concept curriculum. This is not caused by the fix and should be checked with the larger curriculum.
- When the remaining work no longer fits before the deadline, the planner returns `INFEASIBLE_PROVED` with no work for the day (a scripted struggling learner idled on day 5). Unchanged here; it is part of the capacity rule.
- The static planner fills days in a fixed topological order and can miss a plan that exists (3 of 3,000 random demo requests). Unchanged.

Decision: keep the fix as the default behaviour of `replan`; D1 is reversed. Update the website and any Week 7 summary that quotes adaptive_full to these numbers.
