WEEK 7 PRE-REGISTRATION (addendum): adaptive deadlock fix

Written before any code change or run. Reverses decision D1 ("documented
limit", docs/beta/beta_report.md) after the Week 7 demo audit reproduced the
deadlock with scripted learners (an always-correct learner gets work on day 1
only; a learner who misses A once gets work on day 1 only).

Problem
1. replan never schedules a concept again once it is completed, unless it is
   Mastered (spaced review) or a remediation ancestor that is not completed.
   A completed concept that is still Uncertain (n < min_obs) or Weak keeps
   blocking every dependent (UNCERTAIN_NEEDS_ASSESSMENT / PREREQUISITE_UNMET),
   and no new evidence can arrive. adaptive_full: 4,000 / 5,000 no-plan days.
2. The adaptive loop in src/evaluation/integrated.py executes nothing on a day
   whose plan status is HEURISTIC_NO_PLAN, even when that plan lists work for
   the day.
3. In generate_static_plan and replan, a Weak prerequisite blocks its
   dependents for the whole horizon even when the Weak concept itself is
   scheduled on an earlier day of the same plan (the Weak check runs before
   the "planned on an earlier day" check).

Change
- New reason code PRACTICE_FOR_EVIDENCE (src/trace/schema.py), accepted as a
  SELECTED reason by src/trace/checker.py.
- replan, new step between remediation and planned work: every completed,
  not-Mastered concept in the target's candidate universe whose class is
  Uncertain or Weak and that is a direct prerequisite of remaining required
  work gets one practice block, in lexicographic topological order, on the
  first day it fits in the leftover budget (SELECTED, PRACTICE_FOR_EVIDENCE).
  Daily order becomes: remediation, practice for evidence, planned work,
  due reviews.
- replan and generate_static_plan: a prerequisite planned (or practised) on an
  earlier day of the same plan satisfies the gate conditionally
  (conditional = revalidate before execution), also when it is Weak. Same-day
  use of a Weak prerequisite stays blocked. The closed loop replans after
  every answer, so a dependent is only executed if the prerequisite passes the
  gate at that time.
- integrated.py adaptive arms: on a day whose plan is HEURISTIC_NO_PLAN with a
  list trace, the day's listed activities are executed. The no-plan-day metric
  definition is unchanged (a day counts as no-plan when the plan status is not
  FEASIBLE), so the number can only fall because plans become feasible.
- Not edited: static_prerequisite_order, non_adaptive_greedy(_best_singleton)
  arms, greedy.py, greedy_fallback.py, the classifier and its thresholds
  (min_obs 3, window 4), evaluation/results/w7/baseline/ and improvement/.

Workload (same as docs/w7/preregistration.md)
- Integrated S0, experiments/w7_improvement.yaml, seeds 42, 101, 2024, 777,
  999 x 200 learners = 1,000 paired learners, 5 days, 10-minute budget,
  1,000 paired bootstrap resamples. New outputs go to
  evaluation/results/w7/deadlock_fix/integrated_s0/.
- Scheduling benchmark: not rerun (no scheduling code changes).

Metrics and analysis
- Pooled with scripts/w7_pooled_s0.py: mastered concepts per arm with 95% CI,
  no-plan days, prerequisite and budget violations, trace coverage, runtime.
- Primary: paired mastered difference adaptive_full (fixed) minus
  adaptive_full (w7 improvement run), and adaptive_full (fixed) minus
  static_prerequisite_order, 95% CI.
- Secondary: no-plan days of adaptive_full; the same differences for the four
  replan ablations.

Claim rule (unchanged)
- Better only if the paired 95% CI excludes zero in the favourable direction.
  Otherwise "no difference shown". A loss is reported as a loss.
- Sanity: static_prerequisite_order, non_adaptive_greedy,
  non_adaptive_greedy_best_singleton and ablation_no_replan must reproduce the
  w7 improvement run exactly (all per-learner columns except runtime_ms).
- Hard constraints: 0 prerequisite violations, 0 budget violations, 100% trace
  coverage. Any violation is a failure of the fix, not a trade-off.

Expected before running
- adaptive_full no-plan days fall well below 4,000 / 5,000. The size is not
  predicted.
- Mastery direction against static is not predicted: adaptive_full now spends
  budget on repeated practice, so it may reach fewer new concepts in 5 days
  than static while practising each more.
- All claims are about simulator behaviour only.

Amendment after the first full run (2026-11-06; disclosed, not hidden)
- First run (code c5d1a8f): replan arms showed 40% trace coverage, failing the
  hard constraint above. Cause: the adaptive loop in integrated.py never passed
  past days' trace back to replan (replan returns past_trace + future trace),
  so every mid-horizon plan's trace missed days 1..d and failed check_trace;
  and a HEURISTIC_NO_PLAN list trace was validated with the dict-only
  check_no_plan_trace. Before the fix no mid-horizon plan was ever feasible,
  which hid both.
- Change: the loop carries each day's trace (as planned at the start of the
  day) into ReplanState.past_trace, and validates list traces with check_trace.
  Bookkeeping only: replan does not read past_trace when planning, so
  schedules and every per-learner column are unchanged (checked against the
  first run). Reported numbers come from the rerun.
