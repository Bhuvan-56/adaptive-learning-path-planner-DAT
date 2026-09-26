# Problem Boundary and Actors

## System Boundary

**What the prototype will implement:** A backend recommendation, learner-state
estimation, policy, and path-planning service tailored to structured quantitative
subjects (Mathematics and Computer Science). It ingests learner state and time
constraints to produce learning plans, activity recommendations, and machine-readable
explanations of those decisions.

**What the prototype will not implement:** The project excludes building a Learning
Management System (LMS) interface, authoring extensive educational curriculum content,
building natural-language content-generation pipelines, and collecting private or
proprietary student telemetry.

## Actors

- **Learner:** The end-user whose knowledge state is continuously estimated from their
  quiz and exercise performance. The learner also operates under external constraints —
  a deadline and a daily time budget — that the system must respect when generating a
  plan.

- **Mentor/Instructor:** An external auditor of the system's automated decisions.
  Rather than receiving natural-language summaries, the instructor reviews a
  structured, machine-readable trace of each generated plan to verify why specific
  activities were selected or rejected.

- **Curriculum Administrator:** The structural authority over the educational domain.
  It supplies the curriculum as a graph of concepts and their mandatory prerequisite
  relationships, which the planning engine treats as a fixed input once validated.

- **Assessment Engine:** The system's diagnostic module. It calibrates a new learner's
  initial ability with a short adaptive test, converts that into starting mastery
  estimates per concept, and later flags when a learner is repeatedly struggling with a
  concept so the planner can intervene.

- **Planning Engine:** The daily scheduling module. Given the learner's current state,
  the curriculum's prerequisite structure, and the time budget, it decides what mix of
  new learning, review, and remediation activities to schedule each day, and replans
  when circumstances change (missed sessions, failed assessments, or changed
  deadlines/budgets).

Detailed assumptions about curriculum structure, data availability, and learner
behavior are addressed in `ASSUMPTIONS.md`.
