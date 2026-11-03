# Investigation Findings: 800 Adaptive No-Plan Days (Task Beta-A1)

## 1. Executive Summary

In the integrated benchmark run (`w5_final`, 200 synthetic learners over a 5-day horizon with 10-minute daily budget), the primary arm `adaptive_full` produces **800 no-plan days**, all categorized under `SCHEDULING_CONSTRAINTS_UNMET`. Under identical conditions, `static_prerequisite_order` and `non_adaptive_greedy` produce **0 no-plan days**.

This investigation reproduces the 800 no-plan days from configuration, tracks the exact state transitions for every learner-day, confirms the causal hypothesis, evaluates whether budget played any role, contrasts arguments for bug vs. design limit, and outlines the code paths implicated in potential remediation.

---

## 2. Hypothesis Evaluation

**Hypothesis:**
> After one practice observation the first concept is Uncertain (min_obs 3), replan treats an Uncertain prerequisite as unmet (`UNCERTAIN_NEEDS_ASSESSMENT`), and every downstream candidate is blocked on days 2 to 5 for all 200 learners.

**Result: CONFIRMED**

Detailed mechanism:
1. **Day 1 Execution:** On Day 1, initial static planning schedules concepts `A` (duration 5 min) and `B` (duration 5 min), filling the 10-minute daily budget. Both activities are executed by all 200 synthetic learners.
2. **Post-Observation State:** Following one practice response, each concept has observation count $n = 1$. The active policy defines `min_obs = 3` (`PolicyConfig.min_obs`, `config/bkt_params.yaml`). In `src/state/learner_state.py` (lines 178–179), the classification rule enforces:
   $$\sigma^2 > \sigma^2_{\max} \lor n < \text{min\_obs} \implies \text{Uncertain}$$
   Consequently, both `A` and `B` are classified as **Uncertain** for all 200 learners, regardless of response correctness.
3. **Prerequisite Gating in Replan:** On Day 2, dynamic replanning evaluates remaining curriculum nodes `C` (duration 10 min, prerequisite `A`) and `D` (duration 10 min, prerequisites `B` and `C`). In `src/planning/replan.py` (lines 509–520):
   ```python
   elif p in completed_nodes and p_class not in ("Weak", "Uncertain"):
       prereq_status[p] = True
       has_conditional_prereq = True
   else:
       prereq_status[p] = False
       prereqs_met = False
       if p_class == "Uncertain":
           uncertain_prereqs.append(p)
           assessment_candidates.add(p)
   ```
   Because `A` is completed but `Uncertain`, `C` fails the prerequisite gate with `ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT`. `D` similarly fails with `ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT` because `B` is `Uncertain`.
4. **Permanent Starvation on Days 2 to 5:**
   - Completed concepts `A` and `B` are excluded from `remaining_nodes` (uncompleted curriculum nodes).
   - They are not in `remed_queue` (remediation triggers exclusively for `Weak` concepts, lines 422–435).
   - They are not in `due_candidates` (spaced review triggers exclusively for `evidence_mastered` concepts, lines 576–578).
   - While `replan()` adds `A` and `B` to `assessment_candidates`, it contains no logic to schedule assessment or practice blocks for uncertain prerequisites.
   - As a result, `day_activities` remains empty ($\emptyset$), remaining budget stays at 10 minutes, and the planner returns `FeasibilityStatus.HEURISTIC_NO_PLAN` with reason code `InfeasibilityReason.SCHEDULING_CONSTRAINTS_UNMET`.
   - With 0 activities executed on Day 2, no new observations occur, cognitive states remain frozen, and Days 3, 4, and 5 repeat identically.
   - Exactly $200 \text{ learners} \times 4 \text{ days} = 800 \text{ no-plan days}$.

---

## 3. Grouped Constraint & State Breakdown (Summing to 800)

Every single one of the 800 no-plan learner-days exhibits an identical constraint and state configuration across the 200 learners:

| Day | Completed So Far | Prerequisite Observations ($n$) | Prerequisite Classes | Candidate Reason Codes | Remaining Budget | Feasibility Reason Code | Count |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2 | `{A, B}` | $n_A=1, n_B=1, n_C=0, n_D=0$ | $A$: Uncertain, $B$: Uncertain, $C$: Uncertain, $D$: Uncertain | $A$: COMPLETED<br>$B$: COMPLETED<br>$C$: UNCERTAIN_NEEDS_ASSESSMENT<br>$D$: UNCERTAIN_NEEDS_ASSESSMENT | 10 / 10 min | `SCHEDULING_CONSTRAINTS_UNMET` | 200 |
| 3 | `{A, B}` | $n_A=1, n_B=1, n_C=0, n_D=0$ | $A$: Uncertain, $B$: Uncertain, $C$: Uncertain, $D$: Uncertain | $A$: COMPLETED<br>$B$: COMPLETED<br>$C$: UNCERTAIN_NEEDS_ASSESSMENT<br>$D$: UNCERTAIN_NEEDS_ASSESSMENT | 10 / 10 min | `SCHEDULING_CONSTRAINTS_UNMET` | 200 |
| 4 | `{A, B}` | $n_A=1, n_B=1, n_C=0, n_D=0$ | $A$: Uncertain, $B$: Uncertain, $C$: Uncertain, $D$: Uncertain | $A$: COMPLETED<br>$B$: COMPLETED<br>$C$: UNCERTAIN_NEEDS_ASSESSMENT<br>$D$: UNCERTAIN_NEEDS_ASSESSMENT | 10 / 10 min | `SCHEDULING_CONSTRAINTS_UNMET` | 200 |
| 5 | `{A, B}` | $n_A=1, n_B=1, n_C=0, n_D=0$ | $A$: Uncertain, $B$: Uncertain, $C$: Uncertain, $D$: Uncertain | $A$: COMPLETED<br>$B$: COMPLETED<br>$C$: UNCERTAIN_NEEDS_ASSESSMENT<br>$D$: UNCERTAIN_NEEDS_ASSESSMENT | 10 / 10 min | `SCHEDULING_CONSTRAINTS_UNMET` | 200 |
| **Total** | | | | | | | **800** |

---

## 4. Assessment Scheduling & Budget Checks

1. **Does the planner ever schedule an assessment or practice activity for an Uncertain prerequisite?**
   **No.** `src/planning/replan.py` collects uncertain prerequisites into an internal set `assessment_candidates` and returns them in the plan dictionary (`result["assessment_candidates"] = sorted(list(assessment_candidates))`), but neither `replan.py` nor `src/evaluation/integrated.py` contains any logic to convert items in `assessment_candidates` into scheduled activities or diagnostic probes.
2. **Is any no-plan day caused by budget instead?**
   **No.** Across all 800 no-plan days:
   - Initial daily budget is 10 minutes.
   - Remaining daily budget at plan termination is exactly 10 minutes (0 minutes consumed).
   - Candidate `C` requires 10 minutes ($10 \le 10$).
   - Candidate `D` requires 10 minutes ($10 \le 10$).
   - Reason codes for candidate exclusion are strictly `ReasonCode.UNCERTAIN_NEEDS_ASSESSMENT` (0 candidates filtered for `BUDGET_EXCEEDED` or `BLOCK_EXCEEDS_DAILY_BUDGET`).
   - Feasibility status reason code is strictly `SCHEDULING_CONSTRAINTS_UNMET` (0 days marked `CAPACITY_EXCEEDED` or `BLOCK_EXCEEDS_DAILY_BUDGET`).

---

## 5. Perspectives: Bug vs. Design Limit

### Facts Supporting "Bug"
1. **Deadlock / Starvation State:** The system enters an unrecoverable livelock. A learner completes a prerequisite activity, the system identifies that more evidence is needed ($n < 3$), yet the planner schedules nothing to gather that evidence, halting the learner for 80% of their learning horizon while leaving 100% of their daily study budget unused.
2. **Inversion of Adaptive Value:** In `summary.md`, `static_prerequisite_order` and `non_adaptive_greedy` both achieve 1.9700 concepts mastered with 0 no-plan days, whereas `adaptive_full` achieves 1.8900 concepts mastered with 800 no-plan days. The paired difference shows static significantly outperforming adaptive ($[-0.1200, -0.0450]$). The adaptive component penalizes learners by freezing them.
3. **Asymmetry between Weakness and Uncertainty:** If a learner fails a prerequisite and is classified as `Weak`, the planner enqueues it for remediation (`remed_queue`), schedules practice, and enables progression. If a learner performs well on a prerequisite but only has 1 observation, it is classified as `Uncertain`, receives no remediation, no review, and no practice, making `Uncertain` more punitive than `Weak`.
4. **Dangling Output Contract:** `replan()` explicitly populates `assessment_candidates` and returns it in its dictionary, indicating an architectural intent for assessment resolution that was left unimplemented in both the planner and the evaluation harness.

### Facts Supporting "Design Limit"
1. **Strict Prerequisite Correctness Invariant:** The architecture explicitly enforces that downstream advanced content must not be presented to learners without confident prerequisite mastery evidence (`p in completed_nodes and p_class not in ("Weak", "Uncertain")`). Permitting a learner to advance when a prerequisite has $n=1 < 3$ would violate the invariant requiring statistical evidence before prerequisite clearance.
2. **Modular Boundary (Planner vs. Diagnostic Harness):** `src/planning/replan.py` is strictly a curriculum path planner, not an assessment delivery engine. Diagnostic testing is defined under Module M7 (`src/diagnostic`). The planner signals `UNCERTAIN_NEEDS_ASSESSMENT` and returns `assessment_candidates` to notify the orchestrator that diagnostic probing is required. That the closed-loop evaluation harness (`src/evaluation/integrated.py`) lacks a mid-horizon diagnostic probe mechanism is a harness constraint, not a planner logic error.
3. **Curriculum Topology & Discrete Activity Durations:** In `demo_curriculum.json`, concepts have single baseline exercise blocks (5 or 10 min). Given a 10-minute daily budget and 5-minute activities for A and B, a single day can only accommodate 1 observation each. Without a repeat-practice policy on mastered/developing concepts, reaching $n=3$ within a 5-day horizon for 4 sequential concepts under a 10-minute budget is mathematically capacity-constrained.

---

## 6. Code Paths Implicated in a Potential Fix

Depending on whether resolution is pursued via planner logic, policy thresholds, or harness orchestration:

1. **Planner Prerequisite Gate (`src/planning/replan.py` lines 509–520):**
   - Allow completed concepts with sufficient point estimate $p \ge \text{weak\_p}$ or non-weak status to satisfy prerequisite gates conditionally (e.g., treating them as conditional prerequisites rather than hard blockers).
   - Alternatively, treat $n < \text{min\_obs}$ as `Developing` rather than `Uncertain` if initial prior ability from diagnostic was sufficiently confident.
2. **Planner Scheduling of Assessment Candidates (`src/planning/replan.py` lines 476–550):**
   - Introduce an "Assessment / Probing" scheduling phase between Remediation and Curriculum work: if `assessment_candidates` is non-empty and `rem_budget >= dur`, schedule follow-up practice on `assessment_candidates` to raise observation count $n \ge \text{min\_obs}$.
   - Ensure completed nodes needing additional evidence remain in or are re-added to candidate evaluation.
3. **Policy Configuration (`src/state/policy.py` line 24, `config/bkt_params.yaml`):**
   - Adjust `min_obs` threshold (e.g., setting `min_obs = 1` or differentiating initial diagnostic evidence from practice evidence).
4. **Harness Closed-Loop Integration (`src/evaluation/integrated.py` lines 315–330):**
   - In `integrated.py`, when `active_plan["status"] == FeasibilityStatus.HEURISTIC_NO_PLAN` and `assessment_candidates` is non-empty, trigger targeted CAT diagnostic items to resolve uncertainty before falling back to empty days.

---

## 7. Decision

Decision D1 (repair, improvement, or documented limit): ______

