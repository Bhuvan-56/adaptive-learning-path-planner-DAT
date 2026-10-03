# ADR-005: Bounded Self-Learning Policy

## Status

Proposed / Optional Extension

## Context

The core system uses BKT to update learner state, but the recommendation policy itself remains deterministic.

A contextual bandit may optionally be introduced after the integrated baseline has been validated.

## Decision

If implemented, the bandit may select only from the action set produced by a deterministic admissibility layer.

Prerequisites, available time, required remediation, indivisible activity constraints, and curriculum validity cannot be overridden by the learned policy.

The policy will log:

- learner context;
- eligible action set;
- selected action;
- selection probability;
- observable reward;
- elapsed time; and
- policy version.

Rewards must come from delayed quiz/retention outcomes or a declared proxy rather than the planner's own predicted mastery.

Simulator latent state is evaluator-only and must not be exposed to the policy or directly used as a reward.

## Evaluation

Bandit training uses separate episodes from evaluation. The final policy is frozen before evaluation on held-out episodes and seeds.

Evaluation reports learner outcomes and exploration cost and retains a deterministic fallback.

## Scope

This extension is not required for the core project.

LLM orchestration, autonomous content generation, and real-student online experiments are out of scope.

Simulator-only gains support only the claim that the simulator can evaluate the proposed policy; they do not establish real-student effectiveness.
