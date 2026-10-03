# ADR-006: Duration Proxy as Scheduling Proxy

## Status

Accepted

## Context

Public educational datasets (Junyi Academy, ASSISTments) record per-attempt student response times, but do not contain explicit concept-level lesson baseline durations for path planning.

## Decision

The engine computes baseline lesson duration using median response time on task multiplied by configured practice count:

\[
L_c = \frac{\operatorname{median}(\text{time\_taken}_c) \times N_c}{60}.
\]

Where raw dataset fields are missing or unavailable, synthetic duration values are assigned and explicitly labeled as `"synthetic"` in dataset fixtures and configuration.

This metric is treated as a **scheduling proxy** for packing indivisible daily time budget blocks, not as a measured physical lesson duration.

## Consequences

- Prevents unmeasured baseline durations from being falsely presented as ground-truth dataset properties.
- Enables deterministic daily block packing and indivisibility feasibility checking.
- Maintains clear provenance separating empirical response timing from synthetic scheduling assumptions.
