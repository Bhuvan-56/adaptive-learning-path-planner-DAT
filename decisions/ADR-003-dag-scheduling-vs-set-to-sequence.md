# Architecture Decision Record: ADR-003

## Decision ID & Date
ADR-003 | 2026-09-25

## Title
Explicit Precedence-Constrained DAG Scheduling vs. Neural Set-to-Sequence Recommendation

## Status
Reaffirmed (Decided at proposal time)

## Old / Current Approach
N/A — First decision.

## Evidence
- Neural set-to-sequence models (Chen et al., 2023) predict study sequences from embeddings, but operate as black-box approximators.
- Neural models cannot guarantee zero prerequisite violations under hard constraints and cannot compute exact daily time-budget capacity infeasibility traces ($W_{\text{req}} > DB$).
- Deterministic graph validation algorithms (e.g., Tarjan's SCC for cycle detection, topological ordering) provide mathematical guarantees of prerequisite validity.

## Alternatives Considered
1. **Neural Set-to-Sequence Architecture:** End-to-end deep learning recommendation. High sequence representation capacity, but lacks hard constraint enforcement, predictable infeasibility handling, and deterministic auditability.
2. **Unconstrained Greedy Knapsack:** Selects highest gain items purely based on value-to-cost ratio, ignoring prerequisite dependencies.
3. **Precedence-Constrained DAG Scheduler with Deterministic Heuristic:** Treats learning path generation as a precedence-constrained knapsack problem solved via a score-per-minute greedy heuristic $\frac{\text{Score}_i}{L_i}$ with exact DP benchmarking on small instances.

## Selected Approach + Rationale
**Selected Approach:** Adopt explicit Directed Acyclic Graph (DAG) validation and a precedence-constrained knapsack planner (`/planner`).

**Rationale:**
This architectural departure is strictly required to guarantee zero prerequisite violations (TC-1.1, TC-1.2) and strictly bound daily schedules within time budgets $B$ (TC-3.1). Deterministic graph planning allows the system to compute precise capacity infeasibility ($W_{\text{req}} > DB$) and emit machine-readable failure reason codes (e.g., `"PREREQUISITE_UNMET"`, `"CAPACITY_INFEASIBLE"`) in audit traces (M7), fulfilling mandatory explainability criteria.

## Impact on Milestones
- **M1 (Curriculum Graph):** Requires 5 automated DAG checks (valid node references, positive durations, difficulty bounds $[0.05, 0.95]$, no self-loops, zero cycles via Tarjan's SCC).
- **M3 (Path Planning Optimization):** Implements greedy score-per-minute scheduling and benchmark DP optimal comparison ($\ge 95\%$ optimal score threshold).
- **M7 (Explainability Framework):** Guarantees complete audit trace coverage for all candidate nodes on the planning frontier.

## Revised Plan / Risks
None yet. DAG validator and precedence-constrained greedy planner will be built with benchmark DP comparison on small test cases. Re-confirmation scheduled for 09 October.
