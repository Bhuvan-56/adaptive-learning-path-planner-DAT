# Project website (Week 7)

Static site for the final presentation: four pages with Week 7 results and two live demos that run the project's own
Python code (`src/`) in the browser through [Pyodide](https://pyodide.org) 0.26.4.

Made by: Bhuvan and Abdur

| Page | File | Data |
|---|---|---|
| Overview | `index.html` | headline numbers from `data/scheduling.json`, `data/s0_pooled.json` |
| Curriculum | `curriculum.html` | `../data/curricula/demo_curriculum.json` (read directly) |
| Scheduling benchmark | `scheduling.html` | `data/scheduling.json` ← `evaluation/results/w7/improvement/scheduling/`, `tests/fixtures/w7/bad_cases.json` |
| Integrated S0 | `results.html` | `data/s0_pooled.json` ← the five `evaluation/results/w7/improvement/integrated_s0/per_learner_seed_*.csv` |
| Live demos | `demos.html` | Pyodide + `py/demo_api.py` + the `src/` files listed in `assets/pyrunner.js`; fallback `data/fallback.json` |

All results come from a simulator with synthetic learners.

## Run locally

From the **repository root** (not from `site/`), so the pages can also fetch `src/`, `data/` and `evaluation/`:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000/site/>. Opening the HTML files directly (`file://`) does not work: the pages use
`fetch()`.

The live demos need internet access once to download Pyodide from `cdn.jsdelivr.net` (about 10 MB; the browser caches
it). Without it the demos page says so and shows the saved outputs of every preset instead. To test that mode on
purpose, open `demos.html?fallback`.

## Rebuild the data files

`site/data/*.json` are generated; rebuild after any change to the results, fixtures or `src/`:

```bash
.venv_w2/Scripts/python.exe site/build_data.py
```

The script

- computes the pooled S0 table with `compute_paired_bootstrap_ci` exactly as `scripts/w7_pooled_s0.py` does (seed order
  42, 101, 2024, 777, 999; B = 1000, seed 42; paired rows sorted by learner seed) and stops unless the numbers equal
  `docs/w7/comparison.md`;
- recomputes the scheduling summary from `per_instance.csv` and stops unless it equals `summary.md`;
- runs every demo preset through `site/py/demo_api.py` natively and saves the outputs as the offline fallback, checking
  the two bad cases reproduce the fixture scores (12 / 18 and 3 / 14);
- checks that no file the site fetches would be dropped by GitHub Pages' Jekyll build (no path part starting with `_` or
  `.`, no YAML front matter).

## How the live demos use the project code

`assets/pyrunner.js` loads Pyodide, installs `networkx` and `pyyaml` (numpy is not needed by the modules used), copies
the listed `src/` files plus `data/curricula/demo_curriculum.json`, `config/adaptive.yaml` and
`experiments/m8_learner_eval.yaml` into Pyodide's file system, and imports `site/py/demo_api.py`. That module only
converts JSON in and out:

- Demo A calls `run_greedy_scheduler`, `run_greedy_best_singleton`, `best_singleton_fallback` and
  `run_exhaustive_oracle`. Those return scores only, so the picks shown are (a) greedy: recorded from the
  `is_admissible` calls greedy makes, (b) best-singleton: `best_singleton_fallback`'s return value, (c) oracle: one
  optimal set found by calling the oracle with items removed one at a time.
- Demo B builds each concept's `ConceptState` from a cold start plus the typed answers (`ConceptState.update`), calls
  `plan_request` (→ `generate_static_plan`), and for an optional event calls `replan` with the event factories from
  `src/planning/replan.py`.

Only the fallback differs from a live run in one known way: `offending_nodes` for `BLOCK_EXCEEDS_DAILY_BUDGET` comes from
a Python set, so its order can differ between runs (same members).

## Hosting

GitHub Pages builds the repository root of `main` with Jekyll. Once this branch is merged, the site is at
`https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/`. No `.nojekyll` is needed: none of the files
the site uses starts with `_` (the `src/` folders it imports have no `__init__.py`; Python treats them as namespace
packages), and the HTML files have no front matter, so Jekyll copies them unchanged.

## 5-minute run-sheet

Before the talk (at least 5 minutes early, on the presentation machine and network):

1. Open `…/site/demos.html` once and wait for the green "Live" line (about 10 s on first load). This caches Pyodide.
   Leave that tab open; open the Overview in a second tab.
2. If the line turns red (offline / CDN blocked), carry on: the presets show saved outputs from the same code.

| Time | Page | What to show and say |
|---|---|---|
| 0:00–1:00 | Overview | The four steps: diagnostic → learner state → prerequisite-safe daily plan within a budget → replan. "Made by: Bhuvan and Abdur". The Week 7 change in one line: greedy plus a best-single-item fallback. Point at the two headline numbers and say they come from a simulator with synthetic learners. (Optional 10 s: Curriculum page, A → B, C → D.) |
| 1:00–3:00 | Live demos, tab A | Preset **12/18 counterexample**: greedy takes item_1 (best score per minute) and scores 12; the oracle takes item_2 + item_3 for 18; best-singleton does not help here (still 12). Then preset **Seed 47, instance 215**: greedy 3, best-singleton and oracle 14. Change one score or the budget, press "Run the three policies" to show it is live. Mention: on 250 instances the paired gain is +0.0077 [0.0018, 0.0159] (Scheduling page). |
| 3:00–5:00 | Live demos, tab B | Preset **Cold start**: day-by-day plan for D with trace reason codes (SELECTED, BUDGET_EXCEEDED, UNCERTAIN_NEEDS_ASSESSMENT). Type `1111` for A: A becomes Mastered and drops out (ALREADY_MASTERED). Preset **Budget 8**: INFEASIBLE_PROVED, BLOCK_EXCEEDS_DAILY_BUDGET, "raise daily budget to at least 10 minutes". Preset **2 days**: CAPACITY_EXCEEDED with the necessary fixes. If time is left: **Replan: B answered 1111**: B becomes Mastered and drops out, C and D move up a day, and A and B come back on days 4 and 5 as *review* sessions (recall below 0.85). Avoid **B weak (no plan)** unless asked: the planner will not build on a Weak concept, so D is never placed (HEURISTIC_NO_PLAN, explained on the page). |
