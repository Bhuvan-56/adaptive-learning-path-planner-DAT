# Week 7 Comparison: greedy vs greedy + best-singleton fallback

Pre-registration: `docs/w7/preregistration.md` (commit `d8cec16`). Baseline: `evaluation/results/w7/baseline/BASELINE.md` (commit `408be9a`).
Every number below is followed by the file it comes from. All results describe simulator behaviour on synthetic instances and synthetic learners only.

Claim rule (pre-registered): a policy is called better only if the paired 95% CI excludes zero in the favourable direction (higher ratio, higher mastery, fewer no-plan days). Otherwise "no difference shown". A loss is reported as a loss.

## 1. Scheduling benchmark (250 instances, oracle once per instance)

Config `experiments/w2_scheduling_benchmark.yaml`, config hash `70e78c7e...c6505`, seeds 7, 17, 27, 37, 47 × 50 instances. Code SHA `0ec795c` (`evaluation/results/w7/improvement/scheduling/manifest.json`).

| Policy | Mean ratio | 5th pct | Min | Count < 0.95 | Source |
|---|---|---|---|---|---|
| greedy (`run_greedy_scheduler`) | 0.9737 | 0.8270 | 0.2143 | 35 / 250 | `evaluation/results/w7/improvement/scheduling/summary.md` |
| greedy_best_singleton (`run_greedy_best_singleton`) | 0.9814 | 0.8548 | 0.5000 | 25 / 250 | `evaluation/results/w7/improvement/scheduling/summary.md` |

Paired ratio difference, new minus greedy: **+0.0077 [0.0018, 0.0159]** (`evaluation/results/w7/improvement/scheduling/summary.md`).
**Claim: greedy_best_singleton better (higher ratio).** The CI excludes zero on the favourable side.

Changed instances: 10 / 250 (`evaluation/results/w7/improvement/scheduling/per_instance.csv`, rows where `greedy_best_singleton_score != greedy_score`). In all 10 the new score equals the oracle score. No instance is lower than greedy (0 / 250, same file). 10 instances move from below 0.95 to at least 0.95 (same file).

Greedy column check: all 250 `greedy_ratio` values equal `ratio` in `evaluation/results/w7/baseline/scheduling/w2_greedy_vs_oracle.csv` exactly.

## 2. Saved bad cases

Fixture: `tests/fixtures/w7/bad_cases.json`. Scores from `evaluation/results/w7/improvement/scheduling/summary.md` (fixture rows, not in the statistics above).

| Case | Budget | Items | Oracle | Greedy | Greedy ratio | Best-singleton | New ratio | Source |
|---|---|---|---|---|---|---|---|---|
| 12/18 counterexample | 10 | 3 | 18 | 12 | 0.6667 | 12 | 0.6667 | `evaluation/results/w7/improvement/scheduling/summary.md` |
| Seed 47, instance 215 | 5 | 11 | 14 | 3 | 0.2143 | 14 | 1.0000 | `evaluation/results/w7/improvement/scheduling/summary.md` |

Instance 215 was regenerated with `src.planning.benchmark.generate_benchmark_instance`; greedy 3 and oracle 14 equal the row in `evaluation/results/w2_greedy_vs_oracle.csv` (`tests/test_w7_b1_bad_cases.py`).

## 3. Integrated S0 (5 seeds × 200 learners = 1,000, 5 days, 10-minute budget, B = 1000)

Config `experiments/w7_improvement.yaml` (= `experiments/w5_final.yaml` plus the new arm), config hash `3e563d39...0f9e`, code SHA `1998685` (`evaluation/results/w7/improvement/integrated_s0/manifest.json`).
Figures pooled over the five `per_learner_seed_<s>.csv` files with `scripts/w7_pooled_s0.py` (`compute_paired_bootstrap_ci`, seed 42, rows sorted by learner seed), because `per_learner.csv` and the arm table in `summary.md` hold seed 42 only.

| Arm | Mastered [95% CI] | No-plan days | Prereq viol. | Budget viol. | Trace coverage | Source |
|---|---|---|---|---|---|---|
| adaptive_full (unchanged) | 1.9340 [1.8309, 2.0380] | 4,000 / 5,000 | 0 | 0 | 100.0% | `evaluation/results/w7/improvement/integrated_s0/per_learner_seed_*.csv`; coverage `summary_seed_*.md` |
| static_prerequisite_order (unchanged) | 2.0360 [1.9360, 2.1400] | 0 / 5,000 | 0 | 0 | 100.0% | same |
| non_adaptive_greedy | 2.0360 [1.9360, 2.1400] | 0 / 5,000 | 0 | 0 | 100.0% | same |
| non_adaptive_greedy_best_singleton | 2.0490 [1.9510, 2.1510] | 0 / 5,000 | 0 | 0 | 100.0% | same |

Paired mastered difference, non_adaptive_greedy_best_singleton minus non_adaptive_greedy, 1,000 learners: **+0.0130 [0.0040, 0.0230]**; 23 learners differ (18 higher, 5 lower) (`evaluation/results/w7/improvement/integrated_s0/per_learner_seed_*.csv` via `scripts/w7_pooled_s0.py`).
**Claim: non_adaptive_greedy_best_singleton better (higher mastery) on the pooled 1,000-learner analysis.**

Sensitivity of that CI: with rows in file order (no sort) the same script gives [0.0040, 0.0240]; it still excludes zero. Per seed (200 learners each, `evaluation/results/w7/improvement/integrated_s0/summary_seed_<s>.md`), all five seeds report "no difference shown": 42 +0.0100 [-0.0100, 0.0300], 101 +0.0050 [-0.0150, 0.0250], 2024 +0.0150 [0.0000, 0.0350], 777 +0.0250 [0.0000, 0.0550], 999 +0.0100 [-0.0100, 0.0300]. The gain is small and is only resolved when the five seeds are pooled.

No-plan days: 0 / 5,000 for both greedy arms, so there is no no-plan claim to make (difference 0).

Identity check: existing arms' per-learner values (all columns except `runtime_ms`) in `evaluation/results/w7/improvement/integrated_s0/per_learner.csv` and all five `per_learner_seed_<s>.csv` equal `evaluation/results/w7/baseline/integrated_s0/` exactly. adaptive_full minus static is -0.1020 [-0.1210, -0.0830] in both runs, identical to `evaluation/results/w7/baseline/BASELINE.md`.

## 4. Runtime (trade-off only; no claim)

| Measure | greedy | greedy + best-singleton | Source |
|---|---|---|---|
| Scheduling, per instance, p50 / p95 (ms) | 0.0219 / 0.0657 | 0.0266 / 0.0730 | `evaluation/results/w7/improvement/scheduling/summary.md` |
| Integrated, per learner over 5 days, p50 / p95 (ms) | 0.0204 / 0.0638 | 0.0427 / 0.1541 | `evaluation/results/w7/improvement/integrated_s0/per_learner_seed_*.csv` via `scripts/w7_pooled_s0.py` |
| Integrated evaluate command, wall clock | 267 s for all 9 arms × 1,000 learners | | this session's run, logged in `weekly/W7_AI_LOG.md` |

`run_greedy_best_singleton` calls `run_greedy_scheduler` and then scans single items, so its time includes greedy's. Both policies were timed on the same machine in the same run. Between runs, timings move a lot: adaptive_full p50 was 6.664 ms in the baseline run and 13.354 ms in this run with identical outputs (`BASELINE.md`; this run via `scripts/w7_pooled_s0.py`). Only within-run runtime comparisons are meaningful.

## 5. Against the pre-registered expectations

| Expectation (`docs/w7/preregistration.md`) | Result | Matched? |
|---|---|---|
| 12/18 stays at 12 (ratio 0.667) | 12, ratio 0.6667 | yes |
| New ratio never below greedy | 0 / 250 instances below, 0 / 2 fixtures | yes |
| Question: is the scheduling gain distinguishable from zero? | +0.0077 [0.0018, 0.0159], better | answered: yes |
| Integrated mastery: likely "no difference shown" | Pooled +0.0130 [0.0040, 0.0230], better; each single seed "no difference shown" | no (pooled); yes (per seed) |
| Sanity: adaptive_full, static, non_adaptive_greedy reproduce w7-baseline exactly | equal in all six per-learner CSVs | yes |

## 6. Limits

- Synthetic learners only. Learner responses come from `MatchedBKTGenerator`; nothing is calibrated on real learners.
- S0 only. S1 and S2 were excluded by pre-registration.
- The S1 defect is open: the integrated daily loop never calls `advance_day` (`tests/test_w7_b1_s1_forgetting.py`, evidence `evaluation/results/w7_evidence/before_b1_s1_forgetting.txt`), so forgetting is applied only before the retention quiz.
- The D1 limit leaves adaptive_full starved: 4,000 of 5,000 adaptive days are no-plan days, so adaptive_full is not a fair competitor to either greedy arm here.
- The integrated gain comes from 23 of 1,000 learners and is only resolved when the five seeds are pooled. The pooled analysis is done by `scripts/w7_pooled_s0.py`, not by the evaluate command.
- The scheduling benchmark uses random DAG instances from one generator configuration.

## 7. Recomputed from the CSVs

```
$ awk -F, 'NR>1 && $3=="False"{s+=$13; n++} END{printf "%.4f %d\n", s/n, n}' evaluation/results/w7/improvement/scheduling/per_instance.csv
0.9814 250
```
Matches the greedy_best_singleton mean ratio 0.9814 in section 1.

```
$ awk -F, 'NR>1 && $3=="non_adaptive_greedy_best_singleton"{s+=$6; n++} END{printf "%.4f %d\n", s/n, n}' evaluation/results/w7/improvement/integrated_s0/per_learner_seed_{42,101,2024,777,999}.csv
2.0490 1000
```
Matches the non_adaptive_greedy_best_singleton mean mastered 2.0490 in section 3.

Decision: ______
