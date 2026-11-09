# Code Explanation and Change Task: Track A (planning, learner state, diagnostic, traces)

Week 8 replaces `docs/beta/ownership_A.md` (Week 6). That pack predates the Week 7 deadlock fix and the Week 8 best-effort plan, and lists one old signature (`ability_to_prior` now takes only `theta`). Everything below matches the code on `main` after Week 8.

**Owner:** Bhuvan Chandra (AI23BTECH11013), Track A since the start of the project · **Other track (Abdur Rehman):** [ownership_track_B.md](ownership_track_B.md)

---

## 1. What happens from request to plan

| Step | File | Function | What it does |
|---|---|---|---|
| 1 | `src/curriculum/graph.py` | `load_graph`, `validate_graph` | Loads the curriculum JSON into a `networkx.DiGraph` (node `baseline_duration`, `base_difficulty`; edge `importance`) and returns error codes for cycles, self-loops, missing nodes, non-positive durations, difficulty outside [0.05, 0.95] and non-finite values. |
| 2 | `src/diagnostic/diagnostic.py` | `run_adaptive_diagnostic` → `AdaptiveDiagnostic.run` | CAT on the 24-item synthetic bank: picks the item with the most Fisher information, re-estimates θ̂, stops at `Var(θ̂) ≤ stopping_variance` or the item cap (10). |
| 2b | same | `ability_to_prior(theta)` | Maps θ̂ to a starting mastery `p0` for each concept; the result is a `ConceptState` per concept. |
| 3 | `src/state/learner_state.py` | `ConceptState.update`, `.classify` | BKT posterior update plus learning transition. `kappa` and `n` rise by 1 per answer. Four classes in fixed order: Uncertain, Mastered, Weak, Developing. |
| 3b | `src/state/policy.py` | `PolicyConfig`, `default_policy` | Thresholds: `p_S 0.10, p_G 0.25, p_T 0.10, mastered_p 0.85, weak_p 0.40, sigma2_max 0.05, min_obs 3, window 4`. |
| 4 | `src/trace/universe.py` | `get_candidate_universe(g, target)` | The target plus all its ancestors. Every trace day must list exactly these nodes. |
| 4b | `src/planning/feasibility.py` | `check_feasibility` | Two proofs of infeasibility: one block longer than the daily budget (`BLOCK_EXCEEDS_DAILY_BUDGET`), or total work above `days × budget` (`CAPACITY_EXCEEDED`, with necessary but not sufficient fixes). Otherwise `CAPACITY_CHECK_PASSED`. |
| 5 | `src/planning/service.py` → `static_baseline.py` | `plan_request` → `generate_static_plan` | First plan: required nodes in lexicographic topological order, packed day by day. |
| 5b | `src/planning/replan.py` | `replan(state, event)` | Handles one event (`assessment_result`, `missed_day`, `changed_budget`, `changed_deadline`), then re-plans the remaining days (rule below). |
| 5c | `src/planning/difficulty.py`, `review.py` | `step_difficulty`, `is_review_eligible`, `get_remediation_ancestors` | 2-up/1-down difficulty stepping; spaced review when HLR recall < 0.85; remediation after k = 2 consecutive failures. |
| 6 | `src/trace/schema.py`, `checker.py` | `TraceEntry`, `ReasonCode`, `check_trace`, `check_no_plan_trace` | Every candidate on every day gets one entry: SELECTED or FILTERED with a reason. The checker rejects missing days, duplicates, wrong reasons and out-of-range values. |

**Daily rule inside `replan`** (`src/planning/replan.py`, the loop after the feasibility check):

1. remediation ancestors first;
2. one **practice-for-evidence** block for each completed prerequisite that is still Uncertain or Weak and blocks remaining work (Week 7 deadlock fix);
3. planned work in topological order;
4. due reviews fill the leftover budget, lowest recall first.

A prerequisite planned or practised on an earlier day of the same plan satisfies the gate *conditionally*: it is marked `revalidate_before_execution`. This applies even when the prerequisite is Weak.

**Week 8 change:** when the only problem is total capacity (`CAPACITY_EXCEEDED`), `replan` still returns `INFEASIBLE_PROVED` with the same explanation and no-plan trace. It also returns `best_effort_days` and `best_effort_trace`, built by the same loop, so the learner keeps working instead of idling. A block longer than the budget still has no best-effort plan. Tests: `tests/test_w8_best_effort.py`.

## 2. p versus σ² (worked example)

`p` is the BKT mastery probability. `σ² = p(1−p)/(κ+1)` is a Beta variance used as an evidence proxy. It is not a calibrated credible interval. Starting from cold start (`A = B = 1`):

```
python -c "from src.state.learner_state import ConceptState as C; from src.state.policy import default_policy as d; P,_=d(); s=C.cold_start(); print(round(s.p,4), round(s.sigma2,4), s.n, s.classify(P)); [s.update(1,policy=P) for _ in range(4)]; print(round(s.p,4), round(s.sigma2,4), s.n, s.classify(P))"
```

The first line is Uncertain (n = 0). After four correct answers the state reaches Mastered: p ≥ 0.85, σ² ≤ 0.05, n ≥ 3, and the window quorum is met. Run the command to see the exact numbers.

## 3. Reading order

1. `src/curriculum/graph.py`
2. `src/state/policy.py`, `src/state/learner_state.py`
3. `src/trace/schema.py`, `src/trace/universe.py`, `src/trace/checker.py`
4. `src/planning/feasibility.py`, `src/planning/static_baseline.py`, `src/planning/service.py`
5. `src/planning/replan.py`, then `difficulty.py` and `review.py`
6. `src/planning/greedy.py`, `greedy_fallback.py`, `oracle.py` (scheduling benchmark)
7. `src/diagnostic/diagnostic.py`

## 4. Likely questions

**Q1. Why did the adaptive planner stall before Week 7?**
A completed prerequisite that was still Uncertain was never scheduled again, but it kept blocking its dependents. 4,000 of 5,000 adaptive days had no plan. The fix is `PRACTICE_FOR_EVIDENCE` in `replan`, together with the conditional gate for prerequisites planned on an earlier day. See `docs/w7/deadlock_fix_results.md`.

**Q2. What happens when the deadline can no longer be met?**
`check_feasibility` proves `CAPACITY_EXCEEDED` and gives the extra days or minutes that would be needed. Since Week 8 `replan` also returns a best-effort plan of what fits (`best_effort_days`), and the adaptive loop runs it. That day is still counted as a no-plan day.

**Q3. Can the planner ever break a prerequisite?**
Not in the evaluated runs. Every executed day is recounted independently by `recount_plan_violations` in `src/evaluation/integrated.py`, which found 0 prerequisite and 0 budget violations in every arm. Within a plan, a dependent can only follow a prerequisite that was completed, evidence-Mastered, or planned on an earlier day. A dependent can sit on the same day as its prerequisite only when the prerequisite is not Weak and is not being practised that day.

**Q4. Why is greedy score-per-minute not optimal, and what does the fallback fix?**
Counterexample 12/18: budget 10, items (6 min, score 12), (5 min, 9), (5 min, 9). Greedy takes the densest item first (12/6 = 2.0), and then neither 5-minute item fits, so it scores 12. The oracle takes the two 5-minute items (18). `best_singleton_fallback` returns the best single item that fits when it beats the greedy pack. That fixes cases like benchmark seed 47, instance 215 (greedy 3, fallback 14, oracle 14), but **not** 12/18 (fallback still 12). Both cases are in `tests/fixtures/w7/bad_cases.json`. On the benchmark the fallback raised the mean ratio to the oracle by +0.0077 [0.0018, 0.0159]; see `docs/w7/comparison.md`.

**Q5. Why can planning code never see true mastery?**
`src/planning`, `src/state` and `src/diagnostic` do not import `src/simulation` or `src/evaluation`. Source-scanning tests check this, for example `tests/test_simulation.py` (forbidden import patterns) and `tests/test_w4_b2_provenance_profiles.py`. Planners receive only scored answers. True mastery is read through `EvaluatorView` at the end of the horizon.

**Q6. What does a trace prove?**
That every candidate concept was considered on every day, and why it was selected or filtered. `check_trace` raises on any gap.

## 5. Change task (do it live, about 30 minutes)

**Task:** add a per-day cap on practice-for-evidence blocks to `replan`.

- Add `max_practice_per_day: Optional[int] = None` to `ReplanState` (`src/planning/replan.py`) and read it in `_extract_state` (both branches).
- In the practice step (Part 1b of the day loop), stop adding practice blocks on a day once the cap is reached. The default `None` means no cap, so behaviour is unchanged.
- Add a test in a new file `tests/test_practice_cap.py`. Use the demo curriculum with two completed Uncertain prerequisites that both block remaining work (completed A and B, target D), budget 10 and cap 1. Assert that no day has more than one `PRACTICE_FOR_EVIDENCE` entry, and that `check_trace` still passes.
- Done when the new test passes and the full suite still passes. A good answer is a diff of about 10 lines plus the test.

What to explain while doing it:

- where Part 1b sits in the daily order;
- why a capped practice block shows up on a later day rather than disappearing;
- why the default must leave every existing test unchanged.
