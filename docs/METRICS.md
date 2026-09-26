# Initial Metrics

The initial metrics are explicitly defined to evaluate both the strict correctness
constraints and the adaptive performance of the planning engine, diagnostic, and
mastery models.

- **Prerequisite-Violation Count:** A strict correctness requirement, rather than a mere
  performance metric. It counts the number of times a scheduled activity violates the
  rule that a downstream target is only unlocked when all mandatory prerequisites are
  Mastered ($p \ge 0.85$, $\sigma^2 \le 0.05$, and at least 3 scored observations) and
  not classified as Uncertain.

- **Daily-Budget Violations:** Another absolute correctness requirement tracking any
  instance where the total scheduled activity duration for a given day exceeds the
  learner's specified daily time budget (B).

- **Plan Feasibility Rate:** The percentage of generated paths that successfully pass
  two distinct checks: the capacity feasibility check (total required work $W_{req}$
  does not exceed total available capacity $DB$) and the scheduling feasibility check
  (valid day-by-day block assignments exist without indivisible duration conflicts).

- **Diagnostic Accuracy and Calibration:** Evaluated using the initial mastery Mean
  Squared Error (MSE), Brier score, Expected Calibration Error (ECE), and information
  gained per question to explicitly compare the adaptive CAT diagnostic against
  fixed-order and random-selection baselines.

- **Mastery-Prediction Quality:** Measured by computing the Brier score and a 10-bin
  Expected Calibration Error (ECE) on held-out real learner responses. This relies on
  the predicted probability of a correct response derived from the estimated mastery
  and BKT slip/guess parameters: $p(\text{correct}) = p(1-p_{S,c}) + (1-p)p_{G,c}$.

- **Simulated Final Mastery (Goal Coverage):** The fraction of simulated learners that
  reach true mastery of their target concept by the prescribed deadline. In synthetic
  evaluations, this metric relies on the true latent state of the simulator satisfying
  the 0.85 threshold, not just the system's own internal estimate.

- **Retained Mastery After Review:** Tracked as the retention rate at evaluation day T.
  It serves as a measure of the spaced review mechanism's effectiveness, relying on the
  Half-Life Regression model's predicted recall metric
  $R_c = 2^{-\Delta t / H_c}$ (see `docs/FORMAL_MODELS.md`, Predicted Recall).

- **Replanning Runtime:** Measured as runtime latency to evaluate the efficiency of the
  greedy score-per-minute heuristic and dynamic replanning algorithm when recalculating
  daily schedules after a missed session or failed assessment.

- **Explanation Coverage:** Assessed via the Trace Completeness automated test. This
  metric verifies that 100% of the activities on the planning frontier are successfully
  documented in the JSON audit trace exactly once — either marked as selected alongside
  their policy scores, or marked as filtered alongside a valid machine-readable reason
  code.

> Note: when reported in the final evaluation, Plan Feasibility Rate and Simulated Final
> Mastery should be explicitly compared against the Static Prerequisite Order and
> Non-Adaptive Greedy baselines defined in `docs/LITERATURE_REVIEW.md` / the evaluation
> configuration, per the course's requirement to report predeclared metrics against
> baselines.
