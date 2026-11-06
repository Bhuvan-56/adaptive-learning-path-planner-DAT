# Week 7 Baseline (Phase 0)

All figures are simulator behaviour on synthetic learners. Nothing here is calibrated on real learners.

## Code state

- Code SHA for both runs: `d8cec16db7ee4028d82202a40618fbe854a7f3b2` (from both manifests, `git.commit_sha` / `git_sha`). This is the pre-rewrite SHA; the same commit is now `2a1603c` (see `docs/w7/sha_map.md`).
- Interpreter: `.venv_w2/Scripts/python.exe` (Python 3.11.4, from `scheduling/manifest.json`).
- Both runs were produced by an earlier session that stopped partway through Phase 0. They were not rerun.

## Dirty flag

manifest dirty = true because get_git_info counts untracked files, including the output folder being written; tracked tree was clean.

`src/provenance.py:60` `get_git_info()` runs `git status --porcelain`, which lists untracked files.
Tracked-tree check, run in this session before committing this file:

```
$ git status --porcelain --untracked-files=no
(empty output)
```

The only untracked path at that point was `evaluation/results/w7/` (this baseline folder).

## Commands

Scheduling benchmark (default config `experiments/w2_scheduling_benchmark.yaml`):

```
.venv_w2/Scripts/python.exe -c "from src.planning.benchmark import run_benchmark; run_benchmark(output_dir='evaluation/results/w7/baseline/scheduling')"
```

Integrated evaluation (scenario resolved by `resolve_scenario_name` in `src/evaluation/integrated.py`; `experiments/w5_final.yaml` sets no scenario, so it resolves to `S0`):

```
.venv_w2/Scripts/python.exe -m src.cli evaluate --config experiments/w5_final.yaml --out evaluation/results/w7/baseline/integrated_s0 --require-clean
```

## Config hashes

| Run | Config | Config hash | Source |
|---|---|---|---|
| Scheduling | `experiments/w2_scheduling_benchmark.yaml` | `70e78c7e7ff24d27fd25808a266ceda28c1ac04ad0e7737720cd11e5649c6505` | `scheduling/manifest.json`, `scheduling/config_hash.txt` |
| Integrated S0 | `experiments/w5_final.yaml` (file sha256 `00e2ba276953abd7568f2b246315065ffd2211cc52d3bdb62029f10789c1eda5`) | `8a4ace116675cd2e24c5252e9c26dd6aea2d2facaf861c7b4682510c4aeefdf7` | `integrated_s0/manifest.json` |

Integrated seeds: 42, 101, 2024, 777, 999 (`integrated_s0/manifest.json`). Scheduling seeds: 7, 17, 27, 37, 47 (`scheduling/manifest.json`).

## Runtimes

Wall-clock time for the two runs was not captured by the interrupted session, and the runs were not repeated. Manifest timestamps: scheduling 2026-11-06T11:56:14Z, integrated 2026-11-06T11:59:01Z. Per-call runtimes from the outputs:

| Item | Value | Source |
|---|---|---|
| Greedy scheduler, mean per instance | 0.0252 ms | `scheduling/w3_summary.md` |
| Exact DP oracle, mean per instance | 0.0609 ms | `scheduling/w3_summary.md` |
| adaptive_full planning p50 / p95 (1,000 learners) | 6.664 / 12.912 ms | `integrated_s0/per_learner_seed_*.csv`, `runtime_ms` |
| static_prerequisite_order p50 / p95 | 0.704 / 1.465 ms | same |
| non_adaptive_greedy p50 / p95 | 0.020 / 0.037 ms | same |

## Scheduling baseline (250 instances)

| Metric | Value | Source |
|---|---|---|
| Mean greedy/oracle ratio | 0.9737 | `scheduling/w3_summary.md` |
| 5th percentile ratio | 0.8270 | same |
| Minimum ratio | 0.2143 (seed 47, instance 215: budget 5, 11 items, greedy 3, oracle 14) | same; `scheduling/w2_greedy_vs_oracle.csv` |
| Count below 0.95 | 35 / 250 | same |
| 12/18 case | greedy 12, oracle 18 | same |

## Integrated S0 table (five seeds, 1,000 learners)

Summary quirk: the "Arm" table in `integrated_s0/summary.md` (section 2) and `per_learner.csv` show seed 42 only. `per_learner.csv` is byte-identical to `per_learner_seed_42.csv` (same sha256 `87fd241f...` in the manifest). The five-seed figures below were computed from the concatenation of the five `per_learner_seed_<s>.csv` files (8,000 rows) with `compute_paired_bootstrap_ci` from `src/evaluation/compare.py` (B = 1000, seed 42).

| Arm | Mastered [95% CI] | No-plan days | Prereq viol. | Budget viol. |
|---|---|---|---|---|
| adaptive_full | 1.9340 [1.8309, 2.0380] | 4,000 / 5,000 | 0 | 0 |
| static_prerequisite_order | 2.0360 [1.9360, 2.1400] | 0 / 5,000 | 0 | 0 |
| non_adaptive_greedy | 2.0360 [1.9360, 2.1400] | 0 / 5,000 | 0 | 0 |

Paired adaptive_full minus static_prerequisite_order: -0.1020 [-0.1210, -0.0830].
Paired non_adaptive_greedy minus static_prerequisite_order: 0.0000 [0.0000, 0.0000].
Trace coverage 100.0% for all three arms in every per-seed summary (`integrated_s0/summary_seed_*.md`).

Per-seed means (from the multi-seed table in `integrated_s0/summary.md`): adaptive_full 1.8900, 1.8950, 1.9700, 1.7950, 2.1200; static 1.9700, 1.9700, 2.1150, 1.8700, 2.2550 for seeds 42, 101, 2024, 777, 999.

Seed 42 cross-check: every column of `per_learner.csv` except `runtime_ms` equals the committed `evaluation/results/w5/final/per_learner.csv` (pandas `DataFrame.equals` on the shared columns: True).

## Comparison with the Week 6 report (`docs/beta/beta_report.md`, `docs/beta/b2_scenarios.md`)

| Quantity | Week 6 | This baseline | Result |
|---|---|---|---|
| adaptive_full mean mastered | 1.9340 | 1.9340 | match |
| static_prerequisite_order mean mastered | 2.0360 | 2.0360 | match |
| Paired difference | -0.1020 | -0.1020 | match |
| Paired difference CI | [-0.1200, -0.0840] | [-0.1210, -0.0830] | mismatch in the third decimal |
| adaptive no-plan days | 4,000 / 5,000 | 4,000 / 5,000 | match |

The CI mismatch: no script in the repository produces the pooled five-seed CI, so the Week 6 resampling method (bootstrap seed or ordering) cannot be reproduced. Both intervals exclude zero on the same side. The CI above uses B = 1000, seed 42, learners concatenated in seed order 42, 101, 2024, 777, 999.

## Test suite at baseline

See the Phase 0 row in `weekly/W7_AI_LOG.md`.
