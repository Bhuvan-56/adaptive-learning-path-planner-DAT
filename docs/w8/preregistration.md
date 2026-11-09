WEEK 8 PRE-REGISTRATION: S1 daily forgetting and best-effort work on deadline-infeasible days

Written before any code change or run. Baseline: `main` at `7858dbd`, suite
266 passed, 1 xfailed (fresh run on branch `w8/final`).

Problem
1. S1 (open since Week 7). The integrated daily loop in
   src/evaluation/integrated.py never calls SimulatedLearner.advance_day, so
   under S1 (p_F = 0.05) forgetting is applied only by the retention quiz after
   the horizon, never between study days. Week 6 and Week 7 S1 results did not
   test forgetting during the horizon.
   Pinned by tests/test_w7_b1_s1_forgetting.py (strict xfail).
2. Deadline-infeasible idle (found in the Week 7 planner audit, not fixed).
   When the remaining required work no longer fits before the deadline
   (check_feasibility returns INFEASIBLE_PROVED / CAPACITY_EXCEEDED), replan
   returns a no-plan result with no future days, and the adaptive loop does no
   work for the rest of the horizon, although work that fits the daily budget
   is available. A scripted struggling learner idled from day 5.

Change
1. integrated.py: at the end of every simulated day (after the day's
   activities, for every arm: adaptive, static and greedy loops) call
   sim_learner.advance_day(1). With p_F = 0 (S0, S2) advance_day returns at
   once and draws no random numbers, so S0 and S2 per-learner results cannot
   change.
2. replan, CAPACITY_EXCEEDED only: keep status INFEASIBLE_PROVED, the no-plan
   dict trace and the feasibility_explanation (with its necessary fixes)
   exactly as now, and add two keys: best_effort_days and best_effort_trace.
   They are produced by the same day-filling rules replan uses for a feasible
   plan (remediation, practice for evidence, planned work in lexicographic
   topological order, due reviews), over the remaining days, with the same
   prerequisite gate and daily budget. No required node is dropped from the
   explanation; the plan simply does what fits. BLOCK_EXCEEDS_DAILY_BUDGET and
   remediation-block infeasibility are unchanged (no best-effort plan).
   The day-filling loop moves into a helper so both paths share it; the
   feasible path must give identical output (checked by the existing suite).
3. integrated.py adaptive arms: on a day whose plan is INFEASIBLE_PROVED with
   best_effort_days, run that day's listed activities. The day still counts as
   a no-plan day (status is not FEASIBLE), with the same reason code. The day
   counts as trace-valid only if the no-plan dict passes check_no_plan_trace
   and best_effort_trace passes check_trace.
- Not edited: generate_static_plan, check_feasibility, the classifier and its
  thresholds, the greedy arms, greedy.py, greedy_fallback.py, earlier results.

Workload
- Integrated S0 and S1, configs experiments/w8_final.yaml (S0) and
  experiments/w8_final_s1.yaml (S1), copies of
  experiments/w7_improvement.yaml with a scenario key; seeds 42,
  101, 2024, 777, 999 x 200 learners = 1,000 paired learners, 5 days,
  10-minute budget, 1,000 paired bootstrap resamples. Outputs:
  evaluation/results/w8/final/integrated_s0/ and .../integrated_s1/.
- S1 "before" run: same config at the pre-fix code, to
  evaluation/results/w8/before/integrated_s1/.
- Scheduling benchmark: not rerun (no scheduling code changes).

Metrics and analysis (pooled with scripts/w7_pooled_s0.py)
- Primary, S1: mastered concepts per arm with 95% CI, before vs after the fix;
  adaptive_full minus static_prerequisite_order after the fix. Secondary:
  retained recall per arm (S1 only).
- Primary, S0: per-learner equality with
  evaluation/results/w7/deadlock_fix/integrated_s0/ (all columns except
  runtime_ms). Any difference is reported and explained.
- Fix 2: scripted learners (new tests) and the INFEASIBLE_PROVED count in the
  no-plan reasons of S0 and S1.

Claim rule (unchanged)
- Better only if the paired 95% CI excludes zero in the favourable direction;
  otherwise "no difference shown". A loss is reported as a loss.
- Hard constraints: 0 prerequisite violations, 0 budget violations, 100% trace
  coverage, in every arm. Any violation is a failure of the fix.

Expected before running
- S0: identical to the Week 7 deadlock-fix run. In that run no day had the
  reason INFEASIBLE_PROVED (all 1,000 adaptive_full no-plan days are
  SCHEDULING_CONSTRAINTS_UNMET), so fix 2 is not expected to change S0.
- S1: mastered concepts fall in every arm compared with the S1 "before" run
  (forgetting now acts during the horizon). Direction of adaptive_full minus
  static is not predicted.
- Fix 2 may show no effect in the 4-concept S0/S1 runs; its effect is shown by
  the scripted-learner tests. This is reported as is.
- All claims are about simulator behaviour on synthetic learners only.

Addendum (before any code change; found while writing the tests)
- The adaptive loop only calls replan after an executed activity. If the
  first plan of the horizon (generate_static_plan) is already
  INFEASIBLE_PROVED, nothing is ever executed, so replan is never called and
  fix 2 could never apply. Change 3 is extended: when the first plan is
  INFEASIBLE_PROVED, the adaptive arms call replan once with
  changed_deadline(horizon_days) (same deadline, so no state change) to get
  the best-effort plan. generate_static_plan itself stays unchanged, so the
  static arms still do nothing on an infeasible request.
- Test for change 3: an integrated run with a 2-day horizon (30 minutes of
  work for a cold learner, 20 minutes of capacity), where adaptive_full
  currently executes nothing.
