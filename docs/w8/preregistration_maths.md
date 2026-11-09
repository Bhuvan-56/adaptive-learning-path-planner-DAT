WEEK 8 PRE-REGISTRATION (addendum 2): larger curriculum and mismatched simulator

Written before any code change or run. Baseline: `main` at `be04323`; suite 274 passed.

Question
Every result so far uses the 4-concept toy curriculum and a simulator that
matches the planner's own model (matched BKT, S0/S1). Does the adaptive arm's
advantage over the static and greedy baselines hold
  (a) on a larger, branching curriculum, and
  (b) when simulated learners do not follow the planner's model?
And with more structure, do any replan ablations now differ from adaptive_full?

Design: 2 x 2, curriculum x simulator
| Run | Curriculum | Simulator | Status |
|---|---|---|---|
| toy-S0 | demo_curriculum.json (4) | matched BKT | exists: evaluation/results/w8/final/integrated_s0/ |
| toy-S3 | demo_curriculum.json (4) | mismatched PFA | new |
| maths-S0 | maths_curriculum.json (16) | matched BKT | new |
| maths-S3 | maths_curriculum.json (16) | mismatched PFA | new |
Toy runs: 5 days, 10-minute budget, target D (as before).
Maths runs: 10 days, 30-minute budget, target INT (12 of 16 concepts needed,
190 minutes from scratch, 300 minutes of capacity).
All runs: seeds 42, 101, 2024, 777, 999 x 200 learners = 1,000 paired learners,
the same nine arms as experiments/w8_final.yaml, B = 1,000 paired bootstrap.

Changes (harness only; no planner, state or diagnostic logic changes)
1. integrated.py reads optional config keys `curriculum_path`, `qmatrix_path`
   and `concept_difficulties` for any curriculum. When absent, the toy files
   are used exactly as now (toy-S0 must reproduce byte-for-byte on every
   per-learner column except runtime_ms).
2. Maths diagnostic: the existing 24-item bank is reused. A new
   data/processed/q_matrix_maths.csv maps items 1-8 to ARITH, 9-16 to VARS,
   17-24 to LIN (the toy Q-matrix probes A, B, C the same way). Unprobed
   concepts cold-start, as concept D does today (ADR-009).
3. Maths learner truth: latent mastery = theta* >= b_c with
   b_c = 2.5 x (base_difficulty_c - 0.3), rounded to 3 decimals (ARITH -0.375
   ... INT 1.375). Every prerequisite has b <= its dependent's b, so initial
   truth never violates the graph.
4. Scenario S3 (mismatched): MismatchedPFAOrLogisticGenerator, gamma 0.40,
   rho 0.10, difficulty_weight 1.0, mastered_p 0.75, p_F 0 (the values in
   experiments/w5_final.yaml), with one change: the concept intercept is
   per learner, beta_c = (theta* - b_c) + logit(0.75). As configured today
   the intercepts ignore the learner, so every learner would be the same
   apart from noise; with this rule ability matters and the initial mastered
   set equals S0's (theta* >= b_c) exactly. Unlike S0, S3 responds to item
   difficulty, so difficulty stepping can matter.
5. Pooling: scripts/w7_pooled_s0.py takes the horizon as an optional argument
   (default 5, unchanged output) so learner-days are counted correctly for 10
   days.
- Not edited: replan, generate_static_plan, feasibility, greedy, the
  classifier and thresholds, CAT, the existing results.
- Known, unchanged: ablation_no_remediation does not switch remediation off
  (docs/final/LIMITATIONS.md B1), so it cannot differ from adaptive_full by
  construction; it is reported but not interpreted.

Metrics
- Primary: concepts truly mastered at the end (evaluator), paired
  adaptive_full - static_prerequisite_order and adaptive_full -
  non_adaptive_greedy, per run, 95% CI.
- Secondary: each replan ablation - adaptive_full; no-plan days and reasons;
  retained recall; runtime p50/p95.
- Hard constraints, every arm and run: 0 prerequisite violations, 0 budget
  violations, 100% trace coverage. Any violation is a failure, not a trade-off.

Claim rule (unchanged): better only if the paired 95% CI excludes zero in the
favourable direction; otherwise "no difference shown". Losses are reported.

Expected before running (not tuned afterwards)
- toy-S3 and maths-S3: the planner's model is wrong for these learners. The
  adaptive advantage may shrink, vanish or reverse; the direction is not
  predicted.
- maths-S0: adaptive_full still better than static (as on toy-S0); size not
  predicted.
- Ablations: at least one replan ablation differs from adaptive_full on the
  maths curriculum (difficulty under S3 is the most likely). If none does,
  that is reported as is.

Runtime rule (fixed now): if one maths seed takes more than 45 minutes, the
maths runs use 100 learners per seed (500 paired learners) instead, and this
is reported. No other change is allowed for runtime reasons.

All claims are about simulator behaviour on synthetic learners only.
