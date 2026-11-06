WEEK 7 PRE-REGISTRATION: best-singleton fallback

Change
- New module src/planning/greedy_fallback.py:
  best_single_score(items, budget, mastered_set=None, g=None) -> float
    highest score of one item admissible with an empty selected set; 0.0 if none
  run_greedy_best_singleton(items, budget, mastered_set=None, g=None) -> float
    max(run_greedy_scheduler(...), best_single_score(...))
  best_singleton_fallback(greedy_picks, items, budget) -> list[str]
    [best single node_id] if its score is strictly greater than the summed
    score of greedy_picks, else greedy_picks unchanged; ties keep greedy
- New opt-in integrated arm non_adaptive_greedy_best_singleton: the existing
  inline greedy packing, then best_singleton_fallback on each day's picks.
- Not edited: greedy.py, replan.py, service.py, behaviour of every existing arm,
  evaluation/results/w7/baseline/.

Workloads (identical for both policies)
- Scheduling benchmark: experiments/w2_scheduling_benchmark.yaml,
  seeds 7, 17, 27, 37, 47, 50 instances each = 250 instances.
- Saved bad cases: 12/18 (budget 10; items (6,12), (5,9), (5,9)) and the
  worst benchmark instance (seed 47, instance 215).
- Integrated: S0, seeds 42, 101, 2024, 777, 999, 200 learners each (1,000),
  5 days, 10-minute budget, 1,000 paired bootstrap resamples. S1 and S2 are
  excluded because of the open S1 defect.

Metrics
- Score ratio against the exact oracle per instance (1.0 when the oracle
  scores 0): mean, 5th percentile, minimum, count below 0.95.
- Paired per-instance ratio difference, new minus greedy, 95% CI.
- Integrated mastered concepts (latent, evaluator only): paired difference
  non_adaptive_greedy_best_singleton minus non_adaptive_greedy, 95% CI.
- No-plan days, prerequisite and budget violations, trace coverage.
- Runtime p50 and p95 in ms, same machine, same run. Reported as a
  trade-off; no claim is made on runtime.

Claim rule
- Better only if the paired 95% CI excludes zero in the favourable
  direction (higher ratio, higher mastery, fewer no-plan days).
- Otherwise "no difference shown". A loss is reported as a loss.
- Sanity: adaptive_full, static and non_adaptive_greedy must reproduce the
  w7-baseline values exactly.

Expected before running
- 12/18 stays at 12 (ratio 0.667): the best single item also scores 12.
- The new ratio is never below greedy by construction, so the question is
  whether any gain is distinguishable from zero and what it costs in runtime.
- Integrated mastery: likely "no difference shown".
- All claims are about simulator behaviour only. No parameter is calibrated
  on real learners.
