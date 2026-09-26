# Literature Review and System Landscape

## Mastery Estimation

**Bayesian Knowledge Tracing (BKT) vs. Deep Knowledge Tracing (DKT):** The methodology
adopts Bayesian Knowledge Tracing (BKT) as its primary online mastery model, leveraging
implementations like pyBKT (Badrinath et al., 2021) to fit individual learner
parameters. While neural sequence architectures like Deep Knowledge Tracing (DKT)
(Piech et al., 2015) offer high predictive accuracy, they are explicitly excluded. The
system requires an explicitly probabilistic measure of mastery and variance
($p_{c,t}$ and $\sigma^2_{c,t}$) that natively integrates with hard prerequisite
constraints. DKT's black-box latent state representation cannot provide the transparent
mathematical triggers required for the system's mandatory structured audit trace.

## Diagnostic Assessment

**Computerized Adaptive Testing (CAT) vs. Fixed-Order/Random-Item Diagnostics:** To
cold-start learner profiles without requiring lengthy baseline quizzes, the engine
utilizes Computerized Adaptive Testing (CAT) driven by an Item Response Theory (IRT)
model. Using maximum Fisher information for item selection — a well-established
strategy in CAT designs to maximize measurement efficiency (Eggen, 2018) — the
diagnostic dynamically adjusts difficulty after each response. Unlike fixed-order or
random-item diagnostics, which the evaluation later uses as baselines, CAT's adaptive
item selection reduces the number of questions needed to reach a stable ability
estimate. This approach forces the assessment to terminate immediately once the
variance drops to 0.15 or 10 questions are reached, rapidly generating a single latent
ability parameter that the system converts into initial concept-level mastery.

## Path Planning

**Explicit DAG Scheduling vs. Set-to-Sequence Recommendation:** Recent advancements in
learning path generation propose concept-aware set-to-sequence neural networks to
predict optimal study sequences (Chen et al., 2023). However, the engine rejects neural
sequence generation in favor of a queryable Directed Acyclic Graph (DAG) solved by a
precedence-constrained knapsack scheduler. This architectural departure is strictly
required because the system must guarantee zero prerequisite violations and explicitly
bound assignments within a daily time limit (DB). A deterministic DAG scheduler
calculates capacity infeasibility precisely and assigns machine-readable reason codes
(e.g., "PREREQUISITE_UNMET") to rejected tasks, an explainability requirement that
set-to-sequence models cannot inherently guarantee.

## Spaced Repetition

**Half-Life Regression (HLR):** Spaced review is integrated using Half-Life Regression
(HLR), a trainable model designed to estimate memory decay and subsequent recall
probability from interaction histories (Settles & Meeder, 2016). Rather than enforcing
fixed review intervals, the engine leverages HLR to compute a continuously decaying
predicted recall probability ($R_{c,t}$) for every mastered concept. This directly
affects the proposed methodology by forcing spaced reviews to compete mathematically
against new learning activities via a unified Review Score, ensuring the learner's
fixed daily time budget is prioritized effectively.

## References

Badrinath, A., Wang, F., & Pardos, Z. (2021). pyBKT: An accessible Python library of
Bayesian Knowledge Tracing models. _arXiv_. https://doi.org/10.48550/arxiv.2105.00385

Chen, X., Shen, J., Xia, W., et al. (2023). Set-to-sequence ranking-based concept-aware
learning path recommendation. _Proceedings of the AAAI Conference on Artificial
Intelligence, 37_(4), 5027-5035. https://doi.org/10.1609/aaai.v37i4.25630

Eggen, T. J. H. M. (2018). Multi-segment computerized adaptive testing for educational
testing purposes. _Frontiers in Education, 3_. https://doi.org/10.3389/feduc.2018.00111

Piech, C., Spencer, J., Huang, J., Ganguli, S., Sahami, M., Guibas, L., &
Sohl-Dickstein, J. (2015). Deep knowledge tracing. _Advances in Neural Information
Processing Systems, 28_.

Settles, B., & Meeder, B. (2016). A trainable spaced repetition model for language
learning. _Proceedings of the 54th Annual Meeting of the Association for Computational
Linguistics_ (Vol. 1, pp. 1848-1858). https://doi.org/10.18653/v1/P16-1174
