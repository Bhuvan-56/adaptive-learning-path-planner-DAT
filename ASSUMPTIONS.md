# Assumptions

Documented assumptions for the system's operational boundaries and models, covering
curriculum size, prerequisite correctness, lesson duration, question tagging, response
generation, learner availability, and mastery observability.

- **Curriculum size:** Assumes the curriculum can be mapped as a finite, queryable
  Directed Acyclic Graph (DAG) derived from public datasets like Junyi Academy, which is
  sized such that a topological ordering and Tarjan's strongly connected components
  algorithm can efficiently validate it prior to planning.

- **Prerequisite correctness:** Assumes the prerequisite relationships defined by the
  source dataset are perfectly accurate and mandatory. If this prerequisite data is
  incomplete or mistagged, this limitation will propagate incorrect gating decisions
  downstream, either unfairly blocking learners or advancing them unprepared.

- **Lesson duration:** Assumes every learning activity acts as an indivisible block of
  time. Baseline durations are assumed to be accurately derived from the median
  per-attempt timing in the dataset, and review activities are assumed to take a
  consistent fractional duration compared to new learning (the specific scheduling
  equation is defined formally in `docs/FORMAL_MODELS.md`).

- **Question tagging:** Assumes each exercise or diagnostic item in the dataset is
  definitively mapped to a specific learning concept (e.g., via Junyi exercise
  identifiers or ASSISTments skill IDs), allowing direct updates to the concept's
  specific Bayesian Knowledge Tracing (BKT) parameters.

- **Response generation:** Assumes all learner answers can be strictly graded as binary
  outcomes. If a concept requires nuanced partial credit or subjective evaluation,
  forcing a binary classification will distort the BKT mastery estimate. For robust
  evaluation, it assumes synthetic responses generated via Item Response Theory (IRT) or
  Performance Factor Analysis (PFA) accurately mirror real-world learning dynamics when
  parameters are sampled from empirical distributions.

- **Learner availability:** Assumes learner availability is rigidly defined by a fixed
  daily time budget and a hard deadline constraint. The system assumes missed sessions
  are completely empty days, triggering the Half-Life Regression (HLR) forgetting model
  and dynamic replanning rather than partial completion.

- **Mastery observability:** Assumes true mastery is an unobservable latent state that
  can only be probabilistically estimated from limited evidence. If diagnostic or
  practice items are poorly calibrated, the resulting mastery estimates will
  misrepresent true learner capability. The specific probability, variance, and
  observation thresholds used to operationalize "sufficiently observed" mastery are
  defined formally in `docs/FORMAL_MODELS.md`.
