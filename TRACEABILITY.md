# Requirements Traceability Matrix (M1-M8) and Objective Acceptance Tests

The following maps the system's core modules (M1-M8) to objective, testable acceptance
criteria, using the TC-ID register format that will later be frozen per the course
evaluation framework (see Appendix D, Milestone Acceptance-Test Register).

| TC-ID  | Milestone                                   | Scenario / Input                                                                                           | Expected Result                                                                                                                                                                                              |
| ------ | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TC-1.1 | M1: Curriculum Graph & Learner State Models | A plan is generated for a target concept with an unmet mandatory prerequisite                              | The plan contains no lesson for that target before the prerequisite is explicitly Mastered                                                                                                                   |
| TC-1.2 | M1: Curriculum Graph & Learner State Models | A curriculum DAG is submitted to the validator before planning                                             | The DAG passes all 5 automated checks (existing prerequisite nodes, positive durations, difficulty bounds in [0.05, 0.95], no self-loops, no cyclic components via Tarjan's SCC)                             |
| TC-2.1 | M2: Adaptive Diagnostic Policy              | Learner answers a diagnostic item incorrectly                                                              | The relevant concept's mastery estimate decreases, and the next item is selected via maximum Fisher information given the updated ability estimate                                                           |
| TC-2.2 | M2: Adaptive Diagnostic Policy              | Diagnostic is in progress                                                                                  | Calibration terminates immediately once ability variance <= 0.15, or at exactly 10 questions, whichever comes first                                                                                          |
| TC-3.1 | M3: Path Planning Optimization              | A daily plan is generated under a configured budget (5, 10, 15, or 30 minutes)                             | Total scheduled duration for the day never exceeds the configured budget                                                                                                                                     |
| TC-3.2 | M3: Path Planning Optimization              | Greedy scheduler is run on small benchmark instances with a known DP-optimal solution                      | Greedy scheduler achieves >= 95% of the optimal total score                                                                                                                                                  |
| TC-4.1 | M4: Difficulty Adaptation                   | Learner answers one exercise incorrectly                                                                   | Next exercise difficulty for that concept decreases by 0.10, floored at 0.05                                                                                                                                 |
| TC-4.2 | M4: Difficulty Adaptation                   | Learner answers two consecutive exercises correctly at the current difficulty                              | Next exercise difficulty increases by 0.10, capped at 0.95                                                                                                                                                   |
| TC-5.1 | M5: Spaced Review and Remediation           | Learner fails two mastery assessments for the same concept within one episode                              | The lowest-mastery unmet prerequisite is scheduled for remediation before any dependent advanced material is unlocked                                                                                        |
| TC-5.2 | M5: Spaced Review and Remediation           | An already-Mastered concept's HLR-predicted recall probability drops below 0.85                            | A review activity for that concept is scheduled                                                                                                                                                              |
| TC-6.1 | M6: Dynamic Replanning & Infeasibility      | Learner misses a scheduled day                                                                             | The remaining schedule is dynamically replanned without deleting or overwriting already-completed progress                                                                                                   |
| TC-6.2 | M6: Dynamic Replanning & Infeasibility      | Daily budget is reduced mid-plan                                                                           | System outputs either a still-valid compressed plan, or an explicit capacity-infeasibility trace with computed alternatives (extend deadline by X days, raise budget by Y minutes, or reduce optional scope) |
| TC-7.1 | M7: Explainability Framework                | Any daily plan is generated                                                                                | Output includes a structured JSON trace showing observable learner state, applied time/budget constraints, and explicit policy score contributions for every decision                                        |
| TC-7.2 | M7: Explainability Framework                | A highly skilled learner encounters already-mastered material                                              | That material is skipped, accompanied by a JSON audit trace entry with a valid machine-readable reason code                                                                                                  |
| TC-7.3 | M7: Explainability Framework                | Automated trace-completeness check is run on a generated plan                                              | Test hard-fails if any frontier candidate is absent, duplicated, or filtered without a valid reason code                                                                                                     |
| TC-8.1 | M8: Comparative Evaluation Strategy         | Two synthetic learners with distinctly different prior mastery profiles request a plan for the same target | The two generated plans are mathematically and structurally different                                                                                                                                        |

## Learner Profiles for Acceptance Testing

To ensure robust evaluation across different constraints and initial states, the
acceptance tests above are evaluated against four distinct learner profiles:

- **Profile 1 (Beginner, High Time Constraint):** Complete novice — latent mastery
  approaches 0 for all foundational nodes. Daily budget: 5 minutes. Targets TC-6.2
  (capacity infeasibility) and TC-3.1 (block-size scheduling feasibility) when single
  lessons exceed the 5-minute budget.

- **Profile 2 (Intermediate, Moderate Time Constraint):** Partial foundational mastery —
  diagnostic flags prerequisite nodes as Mastered but downstream nodes as Developing or
  Uncertain. Daily budget: 10 minutes. Targets TC-2.1/TC-2.2 (diagnostic -> planner
  state propagation), validating the learner skips mastered prerequisites and moves
  directly into intermediate material.

- **Profile 3 (Advanced/Refresher, Flexible Time):** Historical mastery of the full
  curriculum, with significant elapsed time since last review. Daily budget: 15
  minutes. Targets TC-5.2 (spaced repetition) — high $p_c$ but low $R_c$ should produce
  a schedule dominated by HLR-prioritized reviews rather than new lessons.

- **Profile 4 (Mixed Knowledge, High Capacity):** Sporadic knowledge gaps — high mastery
  in some advanced topics, deep foundational gaps triggering Uncertain state. Daily
  budget: 30 minutes. Targets TC-5.1 (remediation) and TC-7.1/TC-7.2 (explainability) —
  the larger budget allows multiple items per day, testing the greedy heuristic's
  balance of new learning against dynamically triggered remediation.
