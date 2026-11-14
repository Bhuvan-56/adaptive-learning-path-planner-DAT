# Architecture Decision Records

**Project:** Adaptive Learning, Diagnostic Assessment and Personalized Path-Planning Engine (Project 03, Group 11)
**Team:** Bhuvan Chandra (AI23BTECH11013), Abdur Rehman (AI23BTECH11015)
**Log compiled:** 14 November 2026, at evidence revision [`d974503`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/d974503)
**Companion documents:** [Project report](Project_Report.pdf) · [Limitations](final/LIMITATIONS.md) · [Acceptance groups](ACCEPTANCE_GROUPS.md)

This is the single decision log required by the submission guide (§3). It has one record per material architecture, data, evaluation or methodology decision, in the guide's template. ADR-001 to ADR-009 were first written in [`decisions/`](../decisions/) between 26 September and 12 October 2026; those original files are kept unchanged, and the records below restate them in the template and add what happened afterwards. ADR-010 is the mandatory methodology record. ADR-011 to ADR-022 record later decisions that previously lived only in weekly reports and pre-registrations. Superseded records are kept, not deleted.

All outcome numbers are simulator behaviour on synthetic learners. "Measured" means a number from a committed result file; "judgment" means a design choice that was not tested against alternatives.

## Index

| ADR | Title | Date | Status | Milestones |
|---|---|---|---|---|
| [001](#adr-001) | BKT, not DKT, for mastery estimation | 2026-09-25 | Accepted (fitting route superseded by ADR-010) | M1, M7 |
| [002](#adr-002) | CAT with 2PL IRT for the cold-start diagnostic | 2026-09-25 | Accepted | M2 |
| [003](#adr-003) | Explicit DAG scheduling, not neural sequence recommendation | 2026-09-25 | Accepted | M1, M3, M6, M7 |
| [004](#adr-004) | Half-Life Regression for spaced review | 2026-09-25 | Accepted in part; unified score superseded by ADR-020 | M5 |
| [005](#adr-005) | Uncertainty as an evidence-count proxy | 2026-10-12 | Accepted | M1, M7 |
| [006](#adr-006) | Lesson duration as a scheduling proxy | 2026-10-12 | Accepted | M3, M6 |
| [007](#adr-007) | Conflict-sensitive evidence window | 2026-10-12 | Accepted | M1 |
| [008](#adr-008) | Bounded self-learning policy | 2026-10-03 | Proposed; not implemented (no-go, Week 7) | M3, M6 |
| [009](#adr-009) | Cold-start prior and ability-to-mastery mapping | 2026-10-10 | Accepted; rule 2 superseded by ADR-019 | M1, M2 |
| [010](#adr-010) | **Methodology record: simulator-first data route (CHANGED)** | 2026-10-12 (record written 2026-11-14) | Accepted | All |
| [011](#adr-011) | Feasibility protocol with witness plans and proofs | 2026-10-12 | Accepted | M3, M6 |
| [012](#adr-012) | Evaluator-only latent state (trust boundary) | 2026-10-12 | Accepted | M8 |
| [013](#adr-013) | Paired-bootstrap claim rule, pre-registration, frozen baselines | 2026-10-12 | Accepted | M8 |
| [014](#adr-014) | Run provenance and clean-tree enforcement | 2026-10-24 | Accepted | M8 |
| [015](#adr-015) | Best-singleton fallback as an opt-in arm | 2026-11-06 | Accepted | M3 |
| [016](#adr-016) | Practice-for-evidence to break the adaptive deadlock | 2026-11-06 | Accepted; supersedes decision D1 | M3, M6 |
| [017](#adr-017) | Best-effort plan on deadline-infeasible days | 2026-11-09 | Accepted | M6 |
| [018](#adr-018) | Robustness runs: larger curriculum and mismatched simulator | 2026-11-09 | Accepted | M8 |
| [019](#adr-019) | Diagnostic answers count as evidence | 2026-11-13 | Accepted; open consequence (B12) | M1, M2 |
| [020](#adr-020) | Review priority = forgetting risk × prerequisite importance | 2026-11-13 | Accepted | M5 |
| [021](#adr-021) | Demonstration interface: static site running the engine in the browser | 2026-11-06 | Accepted | M7, M8 |
| [022](#adr-022) | Keep the diagnostic in the delivered configuration | 2026-11-14 | Accepted | M2, M8 |

---

<a id="adr-001"></a>
## ADR-001 — Bayesian Knowledge Tracing, not Deep Knowledge Tracing, for mastery estimation

**Date, status & scope.** Decided 2026-09-25 (proposal), first committed 2026-09-26 ([`002eb51`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/002eb51)). Accepted. The original plan to fit BKT on Junyi/ASSISTments is superseded by ADR-010. Scope: M1 learner state, M7 trace. Original record: [`decisions/ADR-001-bkt-vs-dkt.md`](../decisions/ADR-001-bkt-vs-dkt.md).

**Context & decision drivers.** The planner must gate prerequisites on an explicit mastery value and explain each decision in a machine-readable trace. Drivers: interpretable per-concept state, a usable uncertainty signal, cheap CPU updates, and no dependence on large training sets.

**Options considered.**
1. *Deep Knowledge Tracing* (Piech et al., 2015): strong predictive accuracy on large logs, but the state is a hidden RNN vector, so it cannot give a per-concept mastery threshold or uncertainty for a trace.
2. *Performance Factor Analysis*: logistic model over success/failure counts; simple, but no online posterior or belief variance.
3. *BKT* (Corbett and Anderson, 1994; pyBKT): four parameters per concept, closed-form Bayesian update, directly usable for gating.

**Decision & rationale.** BKT, implemented in our own code with pyBKT as a parity reference. Judgment: interpretability and traceability outweigh the accuracy DKT might give on data we do not have.

**Consequences & trade-offs.** Every concept carries `p`, which feeds the classifier (ADR-005, ADR-007) and every trace entry. We accept that BKT ignores cross-concept transfer and that its parameters (slip 0.10, guess 0.25, learn 0.10, [`config/bkt_params.yaml`](../config/bkt_params.yaml)) are declared defaults, not fitted (ADR-010). Note: the methodology record of 12 October lists guess 0.20 and learn 0.15; the code and every reported run use 0.10 / 0.25 / 0.10.

**Evidence & validation.** Posterior parity with pyBKT 1.4.3 below 10⁻⁴ on canonical sequences ([`tests/test_m1_bkt_parity.py`](../tests/test_m1_bkt_parity.py), commit [`2025da5`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/2025da5)). Calibration of `p` against latent mastery is measured in the final runs (Brier 0.136, ECE 0.082 on toy S0; [`evaluation/results/w8/final_v2/integrated_s0/summary.md`](../evaluation/results/w8/final_v2/integrated_s0/summary.md)).

**Revisit trigger.** A real-data fit where DKT (or fitted BKT) beats default BKT on held-out log loss by a margin whose paired CI excludes zero, or a calibration ECE above 0.20 on the matched simulator.

---

<a id="adr-002"></a>
## ADR-002 — Computerized adaptive testing with 2PL IRT for the cold-start diagnostic

**Date, status & scope.** Decided 2026-09-25, committed 2026-09-26 ([`002eb51`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/002eb51)). Accepted. Implemented in Week 4 ([`339711c`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/339711c)). Scope: M2. Original: [`decisions/ADR-002-cat-vs-fixed-random-diagnostics.md`](../decisions/ADR-002-cat-vs-fixed-random-diagnostics.md).

**Context & decision drivers.** A new learner needs a starting estimate within a short, bounded test. Drivers: accuracy per item, a hard length cap, an explicit stopping rule, and a measurable comparison with simple diagnostics.

**Options considered.** (1) *Fixed-order* test: simple, inefficient for uneven learners. (2) *Random items*: no design effort, noisy. (3) *CAT with 2PL IRT*, maximum Fisher information selection, stop at Var(θ̂) ≤ 0.15 or 10 items.

**Decision & rationale.** CAT, using catsim components and a synthetic 24-item 2PL bank with a Q-matrix ([`data/processed/`](../data/processed/)). Fixed and random are kept as measured baselines. The literature predicts higher accuracy per item; whether that holds here was left to measurement.

**Consequences & trade-offs.** Adds catsim and SciPy dependencies. The bank is synthetic, so item parameters are not calibrated on real learners (ADR-010). With 24 items the variance stop never fires, so every diagnostic uses all 10 items (LIMITATIONS B5): the "shorter test" benefit is not realised. CAT gives one overall ability θ̂, not per-concept estimates (see ADR-019).

**Evidence & validation.** Measured, 1,000 paired learners, 10-item cap: CAT is better than fixed order on |θ̂ − θ*| (−0.064 [−0.092, −0.038]) and log loss, and better than random on all three metrics; Brier against fixed shows no difference ([`evaluation/results/w8/diagnostic_comparison/summary.md`](../evaluation/results/w8/diagnostic_comparison/summary.md), [`b2994f6`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/b2994f6)). Stopping analysis: [`docs/beta/a3_cat_stopping.md`](beta/a3_cat_stopping.md).

**Revisit trigger.** A larger item bank where the stop rule fires, or a comparison in which fixed or random matches CAT on all three metrics.

---

<a id="adr-003"></a>
## ADR-003 — Explicit precedence-constrained DAG scheduling, not neural sequence recommendation

**Date, status & scope.** Decided 2026-09-25, committed 2026-09-26. Accepted. Scope: M1 graph, M3 planning, M6 replanning, M7 trace. Original: [`decisions/ADR-003-dag-scheduling-vs-set-to-sequence.md`](../decisions/ADR-003-dag-scheduling-vs-set-to-sequence.md).

**Context & decision drivers.** Hard requirements: zero prerequisite violations, zero budget violations, provable infeasibility where possible, and a reason for every candidate every day.

**Options considered.** (1) *Neural set-to-sequence* (Chen et al., 2023): expressive, but no hard guarantee and no exact infeasibility explanation. (2) *Unconstrained greedy knapsack*: ignores prerequisites. (3) *Validated DAG + precedence-constrained knapsack*: greedy score per minute, measured against an exact oracle.

**Decision & rationale.** Option 3, on NetworkX: a validated DAG, a greedy daily planner and an exhaustive oracle over precedence-closed subsets (N ≤ 20). Hard constraints are enforced by construction rather than learned.

**Consequences & trade-offs.** Guarantees hold only for validated graphs (six checks after Week 4: missing nodes, durations > 0, difficulty bounds, non-finite node and edge values, self-loops, cycles). Greedy is not optimal (worst benchmark ratio 0.214; 12/18 counterexample 0.667), so the original "≥ 95% optimal" claim was withdrawn and replaced by a distribution target (ADR-010 table, item 3). No learned ranking.

**Evidence & validation.** Measured: 0 prerequisite and 0 budget violations in 45,000 final learner-runs; greedy mean ratio 0.9737 over 250 instances ([`evaluation/results/w3/w3_summary.md`](../evaluation/results/w3/w3_summary.md)); oracle order-invariance repaired in Week 3 ([`324c9d9`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/324c9d9)). Tests: [`tests/test_m3_path_planning.py`](../tests/test_m3_path_planning.py), [`tests/test_m3_oracle_order.py`](../tests/test_m3_oracle_order.py).

**Revisit trigger.** Curricula above the oracle cap (N > 20) where quality can no longer be checked, or a mean ratio below 0.95 on a new benchmark.

---

<a id="adr-004"></a>
## ADR-004 — Half-Life Regression for spaced review

**Date, status & scope.** Decided 2026-09-25, committed 2026-09-26. Accepted in part: HLR recall decay and the 0.85 review threshold are implemented (Week 4, [`0e2cb58`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/0e2cb58)); the planned unified review score with fitted weights w₁…w₄ and fitted half-lives was not built and is superseded by ADR-020. Scope: M5. Original: [`decisions/ADR-004-hlr-for-spaced-repetition.md`](../decisions/ADR-004-hlr-for-spaced-repetition.md).

**Context & decision drivers.** Mastered concepts decay; review must compete for the same daily minutes as new learning, and must be explainable.

**Options considered.** (1) *Fixed intervals* (Leitner/SM-2): simple, ignores the budget and concept differences. (2) *Threshold-only rule*: forces rigid overrides. (3) *HLR* (Settles and Meeder, 2016): recall R = 2^(−Δt/H), review when R < 0.85.

**Decision & rationale.** HLR recall with a declared prior half-life H = 14 days, used because no review logs exist to fit H (ADR-010). Reviews use only leftover minutes in the final design.

**Consequences & trade-offs.** H is not fitted (LIMITATIONS A6). The planner does not model forgetting directly; lost mastery is recovered only when a review is due (B9). In the integrated runs the review ablation equals adaptive_full under S0 and is slightly better under S1 (−0.017 [−0.033, −0.001]), so review is not credited with a gain.

**Evidence & validation.** [`tests/test_m5_spaced_review_remediation.py`](../tests/test_m5_spaced_review_remediation.py); review ablation results in [`evaluation/results/w8/final_v2/before_after.txt`](../evaluation/results/w8/final_v2/before_after.txt).

**Revisit trigger.** Access to review logs (fit H per concept), or an integrated run where the review ablation differs from adaptive_full with a CI that excludes zero.

---

<a id="adr-005"></a>
## ADR-005 — Uncertainty represented as an evidence-count proxy

**Date, status & scope.** Decided and committed 2026-10-12 ([`d049e9e`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/d049e9e)). Accepted. Scope: M1 classifier, M7 trace. Original: [`decisions/ADR-005-uncertainty-representation.md`](../decisions/ADR-005-uncertainty-representation.md).

**Context & decision drivers.** BKT gives a point estimate `p`, but the planner must not trust a high `p` backed by little evidence (mentor feedback W1-R1, W1-R2).

**Options considered.** (1) *Point estimate only*: no evidence gate. (2) *Full Bayesian posterior over BKT parameters*: principled, costly and not needed for gating. (3) *Beta proxy*: Beta(A, B) matched to `p`, κ = A + B, σ² = p(1−p)/(κ+1).

**Decision & rationale.** Option 3, declared as a heuristic evidence count, not a calibrated interval. Because κ ≥ 4 already gives σ² ≤ 0.05, the observation count n ≥ 3 is the effective gate.

**Consequences & trade-offs.** Simple and traceable; σ² must never be reported as a credible interval. Calibration of `p` itself is measured instead (ADR-001 evidence).

**Evidence & validation.** [`tests/test_m1_learner_state.py`](../tests/test_m1_learner_state.py) (boundary and bound tests, 0 ≤ σ² ≤ p(1−p)).

**Revisit trigger.** If σ² is to be used as an interval in any claim, or calibration shows confident concepts (p ≥ 0.85) mastered less than 85% of the time.

---

<a id="adr-006"></a>
## ADR-006 — Lesson duration as a scheduling proxy

**Date, status & scope.** Decided and committed 2026-10-12. Accepted. Scope: M3, M6. Original: [`decisions/ADR-006-duration-proxy.md`](../decisions/ADR-006-duration-proxy.md).

**Context & decision drivers.** Budget packing needs a duration per lesson; public datasets record response times but not lesson durations.

**Options considered.** (1) *Measured lesson durations*: not available. (2) *Median response time × practice count*: possible only with real logs. (3) *Declared integer-minute proxies*, labelled synthetic.

**Decision & rationale.** Integer-minute proxies per concept in the curriculum JSON, labelled synthetic. With the simulator-first route (ADR-010) the response-time formula was never applied.

**Consequences & trade-offs.** Budget guarantees are exact with respect to the proxy, not to real study time. Indivisible blocks make packing bin-packing-like (ADR-011).

**Evidence & validation.** Curricula in [`data/curricula/`](../data/curricula/); budget tests at 5/10/15/30 minutes in [`tests/test_m3_path_planning.py`](../tests/test_m3_path_planning.py).

**Revisit trigger.** Any deployment with real learners, or a dataset with lesson-level timing.

---

<a id="adr-007"></a>
## ADR-007 — Conflict-sensitive evidence window before Mastered or Weak

**Date, status & scope.** Decided and committed 2026-10-12. Accepted. Scope: M1 classifier. Original: [`decisions/ADR-007-conflict-evidence-gate.md`](../decisions/ADR-007-conflict-evidence-gate.md).

**Context & decision drivers.** With realistic BKT parameters, alternating answers (1, 0, 1, 0) pushed σ² below 0.05 and `p` below 0.40, labelling a learner Weak on mixed evidence (mentor feedback W1-R4). An earlier workaround set the learn rate to 0.

**Options considered.** (1) *Learn rate 0*: hides learning; rejected. (2) *Point thresholds only*: premature labels. (3) *Window gate*: keep the last W = 4 answers; Mastered or Weak requires a full window with at least 3 of 4 agreeing.

**Decision & rationale.** Option 3, with realistic parameters kept. Classification order: Uncertain (n < 3 or σ² > 0.05), Mastered (p ≥ 0.85, window full, ≥ 3 of 4 correct), Weak (p < 0.40, window full, ≥ 3 of 4 incorrect), otherwise Developing.

**Consequences & trade-offs.** Mastered and Weak need at least four answers on a concept; mixed evidence stays Developing. W = 4 and the 3-of-4 quorum are not fitted.

**Evidence & validation.** [`tests/test_m1_learner_state.py`](../tests/test_m1_learner_state.py) (alternating sequence stays Developing; configurable window from Week 3 defect 5).

**Revisit trigger.** Sensitivity runs showing results change materially for W ∈ {3, 5}, or real logs to fit the window.

---

<a id="adr-008"></a>
## ADR-008 — Bounded self-learning policy

**Date, status & scope.** Proposed 2026-10-03 ([`275c430`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/275c430)). Not implemented: no-go recorded in Week 7. Scope: M3, M6 (optional extension). Original: [`decisions/ADR-008-bounded-self-learning-policy.md`](../decisions/ADR-008-bounded-self-learning-policy.md).

**Context & decision drivers.** A contextual bandit could personalise choices, but must never override prerequisites, budgets or remediation, and must not learn from simulator latent state.

**Options considered.** (1) *Deterministic policy only* (keep existing). (2) *Bandit inside an admissibility layer*, frozen before held-out evaluation, with a deterministic fallback.

**Decision & rationale.** Option 2 was allowed if time permitted. In Week 7 the team chose option 1: the time went to the pre-registered improvement (ADR-015) and the deadlock fix (ADR-016), and a bandit would have been tuned on a simulator with open defects ([`weekly/W7.md`](../weekly/W7.md)).

**Consequences & trade-offs.** The delivered policy is fully deterministic; no exploration cost and no learned component to evaluate.

**Evidence & validation.** Week 7 report, "Bandit: no-go".

**Revisit trigger.** A validated simulator (or real data) and a component whose ablation shows a measurable gain that a learned policy could tune.

---

<a id="adr-009"></a>
## ADR-009 — Cold-start prior and CAT ability-to-mastery mapping

**Date, status & scope.** Decided 2026-10-10, committed 2026-10-12. Accepted; rule 2 (probed concepts start with n = 0) superseded on 2026-11-13 by ADR-019. Scope: M1, M2. Original (with its Week 8 amendment): [`decisions/ADR-009-cold-start-prior-and-ability-mapping.md`](../decisions/ADR-009-cold-start-prior-and-ability-mapping.md).

**Context & decision drivers.** CAT produces θ̂ on an unbounded scale; BKT needs p ∈ (0, 1). Unprobed concepts must not be promoted without evidence.

**Options considered.** (1) *Uniform prior* for all concepts: ignores the diagnostic. (2) *Linear mapping*: needs arbitrary truncation. (3) *Logistic mapping* p = sigmoid(θ̂), clamped to [0.01, 0.99], with Beta(1, 1) for unprobed concepts.

**Decision & rationale.** Option 3. Unprobed concepts: p = 0.5, κ = 2, n = 0, so always Uncertain. Probed concepts: logistic p with κ = 2 and n = 0 ("no invented observations").

**Consequences & trade-offs.** With n = 0, every probed concept was also Uncertain, so the CAT result never changed the planner's classes and `ablation_no_diagnostic` equalled adaptive_full (LIMITATIONS B10). This is what ADR-019 changed.

**Evidence & validation.** [`tests/test_w4_b3_diagnostic.py`](../tests/test_w4_b3_diagnostic.py); pre-B10 results in [`evaluation/results/w8/final/`](../evaluation/results/w8/final/).

**Revisit trigger.** Superseded in part; see ADR-019.

---

<a id="adr-010"></a>
## ADR-010 — Methodology record: simulator-first data route (CHANGED)

**Date, status & scope.** **The approach was CHANGED.** The change was recorded in the methodology freeze record dated **12 October 2026** ([`decisions/METHODOLOGY_RECORD.md`](../decisions/METHODOLOGY_RECORD.md), commit [`bd3cfa5`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/bd3cfa5)), three days after the 9 October 2026, 11:59 PM IST deadline. That record's decision line ("REAFFIRMED / CHANGED, strike one") and "Decided by" field were left blank. **This ADR is the team's explicit decision record and was written on 14 November 2026; it is not backdated.** No documented mentor approval of the change exists in the repository. Status: Accepted. Scope: all milestones; directly ADR-001, 002, 004, 006, M8.

**Context & decision drivers.** The Week 1 plan fitted BKT, IRT and HLR on Junyi Academy and ASSISTments 2009–2010 with 70/15/15 student splits, and evaluated planning on those logs.

**Old approach → new evidence.** During Weeks 2–3 the team found that the public logs cannot evaluate a planner: they have no latent ground truth to score mastery against, no counterfactual outcomes for alternative plans or missed days, no prerequisite DAG annotations and no lesson durations; ASSISTments also had schema and licence hurdles ([`docs/DATA_STRATEGY.md`](DATA_STRATEGY.md)).

**Options considered.** (1) *Real data only*: fit models, but no way to compare plans. (2) *Hybrid*: fit on real logs, evaluate planning in a simulator calibrated to them. (3) *Simulator first*: a transparent simulator with evaluator-only latent state (ADR-012); public data as optional secondary validation.

**Decision & rationale.** Option 3. Judgment: the brief allows "a public educational dataset and/or a transparent learner simulator", and only a simulator gives the ground truth needed for paired plan comparisons. Option 2 was preferred in principle but not feasible in the time available.

**Consequences & impact on milestones and tests.**
- All outcome claims are limited to synthetic learners; no real learning gain is claimed.
- BKT parameters, IRT item parameters, HLR half-life and durations are declared, not fitted (ADR-001, 002, 004, 006).
- M8-d retained recall is measured by a simulated delayed quiz; its mismatched-simulator half was delivered with the PFA generator in Week 8 (ADR-018).
- The same record also withdrew the universal "greedy ≥ 95% optimal" claim (replaced by the 250-instance distribution target, M3-b), added n < 3 to Uncertain (ADR-005), added the window gate (ADR-007), split feasibility into proved and heuristic outcomes (ADR-011) and fixed the oracle's order dependence. Its 13-row old-vs-new table is the full list.
- Revised plan: real-data validation moved to the way forward (report §9, task P3).

**Evidence & validation.** [`decisions/METHODOLOGY_RECORD.md`](../decisions/METHODOLOGY_RECORD.md) §2 (13 changes with file citations); simulator commit [`b02177c`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/b02177c).

**Revisit trigger.** Access to a dataset with prerequisite structure and per-learner timing, or any claim intended for real learners.

---

<a id="adr-011"></a>
## ADR-011 — Feasibility protocol: witness plans, proved infeasibility and heuristic failure

**Date, status & scope.** 2026-10-12 (Week 3 defect 4, [`c4c298f`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/c4c298f)). Accepted. Scope: M3, M6, acceptance group M4-a.

**Context & decision drivers.** The original binary feasible/infeasible check could report FEASIBLE when only the capacity test passed. Indivisible blocks make day-by-day packing bin-packing-like, so infeasibility cannot always be decided exactly (mentor feedback W1-R9).

**Options considered.** (1) *Binary capacity check* (keep existing): overstates feasibility. (2) *Exact decision procedure*: intractable in general. (3) *Three outcomes*: FEASIBLE only with a witness plan; INFEASIBLE_PROVED only for proved cases (a block longer than B, or required work > D × B), with minimum fixes; otherwise HEURISTIC_NO_PLAN.

**Decision & rationale.** Option 3: never claim more than is proved.

**Consequences & trade-offs.** Honest outputs and actionable fixes for the proved cases. No repair synthesis for HEURISTIC_NO_PLAN, so M4-a stays partial (agreed with the mentor in Week 4).

**Evidence & validation.** [`tests/test_m3_states_feasibility.py`](../tests/test_m3_states_feasibility.py), [`tests/test_m3_path_planning.py`](../tests/test_m3_path_planning.py); [`src/planning/feasibility.py`](../src/planning/feasibility.py).

**Revisit trigger.** Frequent HEURISTIC_NO_PLAN results in practice, which would justify a repair search.

---

<a id="adr-012"></a>
## ADR-012 — Evaluator-only latent state (trust boundary)

**Date, status & scope.** 2026-10-12 ([`b02177c`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/b02177c)); import boundary hardened in Week 7. Accepted. Scope: M8, acceptance group M8-c.

**Context & decision drivers.** If the planner could read the simulator's true mastery, evaluation would be circular.

**Options considered.** (1) *Shared learner object*: simple, easy to leak. (2) *Separate `EvaluatorView`*: latent state is held by the evaluator; the planner sees only answers.

**Decision & rationale.** Option 2, enforced by tests that check planner and state modules cannot import the latent state.

**Consequences & trade-offs.** Slightly more plumbing; outcome metrics (concepts mastered, Brier/ECE) are computed only in the evaluation step.

**Evidence & validation.** [`tests/test_simulation.py`](../tests/test_simulation.py), [`tests/test_w8_calibration.py`](../tests/test_w8_calibration.py) (boundary checks).

**Revisit trigger.** Any new component that needs learner information; it must go through observable answers.

---

<a id="adr-013"></a>
## ADR-013 — Claim rule, pre-registration and frozen baselines

**Date, status & scope.** Protocol frozen 2026-10-12 ([`docs/EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md)); pre-registration used from Week 7. Accepted. Scope: M8.

**Context & decision drivers.** Differences between arms are small and noisy; with several arms and scenarios it is easy to report favourable noise.

**Options considered.** (1) *Compare means* (keep simple). (2) *Unpaired tests per arm*. (3) *Paired bootstrap* by learner (B = 1,000), claim only if the 95% CI excludes zero; pre-register each change; keep baseline arms unchanged.

**Decision & rationale.** Option 3. Learners are paired across arms by seed, so paired differences remove learner variance. Pre-registration fixes the claim before the run.

**Consequences & trade-offs.** Results that got worse are reported as losses (e.g. adaptive − static was −0.102 before ADR-016, and fell from +0.140 to +0.056 after ADR-019). Baseline arms keep their pre-Week-8 diagnostic priors (B13), so the adaptive arm receives diagnostic evidence the baselines do not. The four final fixes of 13 November followed the test-first process but were not pre-registered; this is disclosed in [`weekly/W8.md`](../weekly/W8.md).

**Evidence & validation.** Pre-registrations: [`docs/w7/`](w7/), [`docs/w8/preregistration.md`](w8/preregistration.md), [`docs/w8/preregistration_maths.md`](w8/preregistration_maths.md); before/after evidence in [`evaluation/results/w8_evidence/`](../evaluation/results/w8_evidence/).

**Revisit trigger.** Many simultaneous comparisons on new scenarios (consider a multiple-comparison correction).

---

<a id="adr-014"></a>
## ADR-014 — Run provenance and clean-tree enforcement

**Date, status & scope.** 2026-10-12 (Week 3 defect 10), hash precision fixed 2026-10-24 ([`c671057`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/c671057)). Accepted. Scope: M8-b, reproducibility (mentor feedback W1-R10, FB006).

**Context & decision drivers.** Results must be traceable to exact code, configuration and inputs.

**Options considered.** (1) *Manual notes* (keep existing). (2) *Manifest per run*: git SHA and dirty flag, Python version, SHA-256 of the resolved configuration, input paths and output checksums; refuse to write under `evaluation/results/` from a dirty tree; clean-clone audit script.

**Decision & rationale.** Option 2 ([`src/provenance.py`](../src/provenance.py), [`scripts/clean_run.ps1`](../scripts/clean_run.ps1)).

**Consequences & trade-offs.** Every committed result has a manifest; runs on a dirty tree must write elsewhere. The clean-run script is PowerShell-only (Windows).

**Evidence & validation.** [`tests/test_provenance.py`](../tests/test_provenance.py); clean run PASS in [`evaluation/results/w8_evidence/clean_run_final.txt`](../evaluation/results/w8_evidence/clean_run_final.txt).

**Revisit trigger.** Supporting Linux/macOS evaluators (port the clean-run script).

---

<a id="adr-015"></a>
## ADR-015 — Best-singleton fallback for the greedy scheduler, as an opt-in arm

**Date, status & scope.** Pre-registered and implemented 2026-11-06 ([`2a1603c`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/2a1603c), [`d7e1ea2`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/d7e1ea2)). Accepted. Scope: M3; the planned Week 7 "one measured improvement".

**Context & decision drivers.** Greedy score per minute can be far from optimal (12/18 counterexample, instance 215 at 0.214).

**Options considered.** (1) *Keep greedy* unchanged. (2) *Dependency-aware lookahead*: more effort and risk. (3) *Best-singleton fallback*: also evaluate the best single admissible item and keep the higher score, the classic knapsack fix.

**Decision & rationale.** Option 3, added as a new module and a new opt-in arm; existing planners and arms untouched, so earlier results stay reproducible.

**Consequences & trade-offs.** Never lowers a score by construction; small runtime cost (p50 0.027 vs 0.022 ms). The 12/18 case is not fixed (12 stays 12). Its integrated gain under S0 (+0.0130, pooled only) disappears under S1 (−0.004, no difference).

**Evidence & validation.** Measured: mean ratio 0.9737 → 0.9814, paired +0.0077 [0.0018, 0.0159]; 10 instances improved, none lowered ([`docs/w7/comparison.md`](w7/comparison.md), [`evaluation/results/w7/improvement/scheduling/summary.md`](../evaluation/results/w7/improvement/scheduling/summary.md)).

**Revisit trigger.** Curricula where greedy ratios below 0.95 become common, which would justify lookahead.

---

<a id="adr-016"></a>
## ADR-016 — Practice-for-evidence to break the adaptive deadlock

**Date, status & scope.** Pre-registered and implemented 2026-11-06 ([`0a0ae92`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/0a0ae92), [`c5d1a8f`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/c5d1a8f)). Accepted. **Supersedes decision D1** of the Week 6 beta report (2026-11-03, [`dfa065c`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/dfa065c)), which kept the behaviour as a "documented limit". Scope: M3, M6, M7.

**Context & decision drivers.** A completed prerequisite that was still Uncertain or Weak blocked every dependent, and no new evidence could arrive: adaptive_full had 4,000 of 5,000 no-plan days and lost to static (−0.102). A Week 7 demo audit reproduced it with scripted learners.

**Options considered.** (1) *Keep as documented limit* (D1). (2) *Relax the gate* (let Uncertain prerequisites unlock): breaks the zero-violation guarantee. (3) *Practice for evidence*: give each completed, unproven, blocking prerequisite one practice block (new reason code PRACTICE_FOR_EVIDENCE); let a prerequisite planned earlier in the same plan satisfy the gate conditionally; run listed work on HEURISTIC_NO_PLAN days.

**Decision & rationale.** Option 3: it produces the missing evidence while keeping the gate.

**Consequences & trade-offs.** New reason code accepted by the trace checker. Measured: adaptive − static went from −0.102 to +0.140 [0.111, 0.169] on S0; no-plan days 4,000 → 1,000 of 5,000. Baseline arms unchanged.

**Evidence & validation.** [`docs/w7/deadlock_fix_results.md`](w7/deadlock_fix_results.md), [`tests/test_w7_deadlock_fix.py`](../tests/test_w7_deadlock_fix.py).

**Revisit trigger.** If practice blocks crowd out new learning (e.g. no-plan days rise again on larger curricula).

---

<a id="adr-017"></a>
## ADR-017 — Best-effort plan on deadline-infeasible days

**Date, status & scope.** Pre-registered and implemented 2026-11-09 ([`ace6b00`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/ace6b00), [`840a12b`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/840a12b)). Accepted. Scope: M6.

**Context & decision drivers.** When remaining required work no longer fits before the deadline (INFEASIBLE_PROVED, capacity exceeded), replan returned no future days and the learner idled, although useful work fit the daily budget.

**Options considered.** (1) *Keep idling* with the proof. (2) *Drop required nodes* to make a "feasible" plan: hides infeasibility. (3) *Keep the proof and add a best-effort plan* built with the same day-filling rules and gates.

**Decision & rationale.** Option 3: the learner keeps working and the infeasibility explanation and necessary fixes stay exactly as before.

**Consequences & trade-offs.** Such days still count as no-plan days (status is not FEASIBLE): 623 of 5,000 on toy S0 and 5,751 of 10,000 on maths S0 in the final runs. Static baseline has no best-effort plan (B7), by design.

**Evidence & validation.** [`docs/w8/results.md`](w8/results.md), [`tests/test_w8_best_effort.py`](../tests/test_w8_best_effort.py).

**Revisit trigger.** Requests for automatic deadline or budget negotiation, which would need a new interface.

---

<a id="adr-018"></a>
## ADR-018 — Robustness runs: larger curriculum and mismatched simulator

**Date, status & scope.** Pre-registered and implemented 2026-11-09 ([`315d4f9`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/315d4f9), [`9b50338`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/9b50338)). Accepted. Scope: M8, acceptance group M8-d.

**Context & decision drivers.** All results used a 4-concept toy curriculum and a simulator matching the planner's own BKT model, the most favourable case.

**Options considered.** (1) *Report toy matched results only*. (2) *2 × 2 design*: toy vs 16-concept maths curriculum, matched BKT (S0) vs mismatched PFA (S3, learning from practice counts), harness changes only. (3) *Real-data validation*: not available (ADR-010).

**Decision & rationale.** Option 2, with the curriculum and simulator read from config so existing runs reproduce byte-for-byte.

**Consequences & trade-offs.** Measured: adaptive beats static in all four cells (toy S3 +0.117, maths S0 +0.094, maths S3 +0.727; final_v2). S3 rewards practice attempts, which favours the adaptive arm, so it is a different simulator, not a neutral one. Both curricula are hand-made.

**Evidence & validation.** [`docs/w8/results_maths.md`](w8/results_maths.md); [`evaluation/results/w8/final_v2/`](../evaluation/results/w8/final_v2/); [`tests/test_w8_maths_eval.py`](../tests/test_w8_maths_eval.py).

**Revisit trigger.** A third simulator family, or real data, giving a different sign.

---

<a id="adr-019"></a>
## ADR-019 — Diagnostic answers count as evidence in concept priors

**Date, status & scope.** 2026-11-13 ([`70183b7`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/70183b7)). Accepted, with an open negative consequence (LIMITATIONS B12). Supersedes ADR-009 rule 2. Scope: M1, M2. Not pre-registered.

**Context & decision drivers.** Under ADR-009 the CAT result never reached the planner's classes (B10): M2's output had no effect on M3.

**Options considered.** (1) *Keep n = 0* (diagnostic has no effect). (2) *n = k*: a concept with k diagnostic items loading on it starts with n = k, κ = 2 + k and those answers in its window; p stays sigmoid(θ̂). (3) *Per-concept BKT updates* on each concept's own diagnostic answers.

**Decision & rationale.** Option 2: the smallest change that makes the diagnostic's evidence count, consistent with ADR-005 and ADR-007. Option 3 was not attempted in the time left.

**Consequences & trade-offs.** Measured: switching the diagnostic off now beats adaptive_full on mastery in all five final runs (−0.084 to −0.237 concepts), and adaptive − static fell from +0.140 to +0.056 on toy S0 (still above zero). Observed mechanism, not separately tested: one θ̂ sets the same p for every probed concept and cannot reach 0.85, so probed concepts start Developing or Weak instead of Uncertain and lose the practice-for-evidence blocks of ADR-016. Baselines keep the old priors (B13).

**Evidence & validation.** [`tests/test_w8_diagnostic_prior.py`](../tests/test_w8_diagnostic_prior.py); [`evaluation/results/w8/final_v2/before_after.txt`](../evaluation/results/w8/final_v2/before_after.txt).

**Revisit trigger.** Implementing option 3 (report §9, P1); done when adaptive_full − ablation_no_diagnostic has a CI ≥ 0 on toy S0 and S1.

---

<a id="adr-020"></a>
## ADR-020 — Review priority = forgetting risk × prerequisite importance

**Date, status & scope.** 2026-11-13 ([`edde468`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/edde468)). Accepted. Supersedes the unbuilt unified review score of ADR-004. Scope: M5. Not pre-registered.

**Context & decision drivers.** The brief requires review scheduled by forgetting risk, prerequisite importance and the remaining budget; edge `importance` was validated but never read (B11).

**Options considered.** (1) *Recall only* (keep existing). (2) *Unified score* with fitted weights w₁…w₄ (ADR-004): no data to fit. (3) *Priority (1 − R) × w*, w = the largest importance from the concept to a not-yet-Mastered dependent (default 1.0), packed into leftover minutes.

**Decision & rationale.** Option 3: covers all three named inputs with no fitted weights, and reduces exactly to the old order when all importances are 1.0.

**Consequences & trade-offs.** Recall, weight and priority are written to each review trace entry. Under S0 the review ablation still equals adaptive_full on mastery; under S1 it is slightly better, so no gain is claimed.

**Evidence & validation.** [`tests/test_w8_review_importance.py`](../tests/test_w8_review_importance.py); [`src/planning/review.py`](../src/planning/review.py).

**Revisit trigger.** Curricula with widely varying importance, or a run where review timing changes outcomes measurably.

---

<a id="adr-021"></a>
## ADR-021 — Demonstration interface: static site running the engine in the browser

**Date, status & scope.** 2026-11-06 ([`f86a1c1`](https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT/commit/f86a1c1)). Accepted. Scope: M7 explainability, M8 evidence; deployment model.

**Context & decision drivers.** Mentors and evaluators should see the engine plan, replan and explain itself without installing Python, and every published number must match the result files. No budget for servers or accounts.

**Options considered.** (1) *CLI only* (keep existing). (2) *Hosted web service* (e.g. a Python backend): needs a server, uptime and secrets. (3) *Static GitHub Pages site* whose demos run the project's own `src/` modules in the browser through Pyodide, with saved outputs as a fallback.

**Decision & rationale.** Option 3: no server, no secrets, the same code as the CLI. A build script recomputes every published number from the per-learner CSVs and refuses to write if any differs.

**Consequences & trade-offs.** Needs internet once to load Pyodide (about 10 MB from jsDelivr); no accounts or saved learners; one event per replan. It is a demonstration interface, not a learner-facing product (an LMS is out of scope).

**Evidence & validation.** [`site/`](../site/), [`site/build_data.py`](../site/build_data.py), [`site/README.md`](../site/README.md); live at <https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/>.

**Revisit trigger.** If the CDN becomes unavailable (vendor Pyodide), or if a real learner pilot needs persistence.

---

<a id="adr-022"></a>
## ADR-022 — Keep the diagnostic in the delivered configuration

**Date, status & scope.** 2026-11-14. Accepted. Scope: M2, M8 (which configuration the report's headline numbers describe).

**Context & decision drivers.** After ADR-019, `ablation_no_diagnostic` scores higher on mastery than adaptive_full in every final run. The team had to decide which configuration is the delivered system.

**Options considered.** (1) *Keep the diagnostic* (adaptive_full as delivered, the no-diagnostic arm as an ablation). (2) *Switch the default to no diagnostic* because it scores higher.

**Decision & rationale.** Option 1. Switching after seeing which arm wins would be an unregistered post-hoc choice; M2 is a required milestone; and the weakness is the ability-to-concept mapping, not the diagnostic's measurement (ADR-002 evidence).

**Consequences & trade-offs.** Headline numbers describe adaptive_full with the diagnostic. The negative ablation result is reported as an open limitation (B12) with a named fix (ADR-019 revisit trigger), rather than hidden by changing the default.

**Evidence & validation.** [`docs/final/LIMITATIONS.md`](final/LIMITATIONS.md) B12; report §5.7 and §8.

**Revisit trigger.** Per-concept priors (ADR-019, option 3) that still leave the diagnostic harmful; then removing it would be a documented, pre-registered change.
