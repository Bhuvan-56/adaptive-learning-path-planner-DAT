# Methodology Freeze Record (Week 3 / 12 October 2026)

## 1. Five Core Methods and Implementation Routes

The Adaptive Learning and Path-Planning Engine relies on five core algorithmic methods. Their theoretical formulation, reference baseline, and implementation routes are declared below:

### Method 1: Bayesian Knowledge Tracing (BKT)
- **Mathematical Model:** Two-state Hidden Markov Model tracking latent mastery $L_t \in \{0, 1\}$ per concept, parameterized by $(P(L_0), P(T), P(S), P(G))$:
  - Prior: $P(L_0)$
  - Transition (learning rate): $P(T) = P(L_t = 1 \mid L_{t-1} = 0)$
  - Slip: $P(S) = P(\text{obs}_t = 0 \mid L_t = 1)$
  - Guess: $P(G) = P(\text{obs}_t = 1 \mid L_t = 0)$
- **Implementation Route:** Integrated via `pyBKT` (version `1.4.3`), benchmarked against exact closed-form Bayesian posterior updates in `src/state/learner_state.py`.
- **Configuration & Parameters:** Loaded deterministically from `config/bkt_params.yaml` ($P(L_0)=0.10, P(T)=0.15, P(S)=0.10, P(G)=0.20$). Verified via numeric parity tests in `tests/test_m1_bkt_parity.py`.

### Method 2: Beta-Variance Uncertainty Proxy
- **Mathematical Model:** BKT produces only scalar point estimates $p_{c,t}$ without native posterior variance. The engine pairs $p_{c,t}$ with a conjugate $\operatorname{Beta}(A_{c,t}, B_{c,t})$ belief representation where:
  $$p_{c,t} = \frac{A_{c,t}}{A_{c,t} + B_{c,t}}, \qquad \kappa_{c,t} = A_{c,t} + B_{c,t}$$
  $$\sigma^2_{c,t} = \frac{p_{c,t}(1 - p_{c,t})}{\kappa_{c,t} + 1}$$
- **Implementation Route:** Implemented in `src/state/learner_state.py` and `src/state/policy.py`. Treated strictly as a heuristic evidence-count confidence proxy (ADR-005). Supported by an observation threshold $n \ge 3$ and a conflict-sensitive sliding evidence window ($W=4$) that prevents oscillatory state assignment under noisy sequences.

### Method 3: Computerized Adaptive Testing (CAT) with 2PL IRT
- **Mathematical Model:** 2-Parameter Logistic Item Response Theory (2PL IRT) item characteristic curve:
  $$P(Y_{ij} = 1 \mid \theta_j) = \frac{1}{1 + \exp\left(-a_i (\theta_j - b_i)\right)}$$
  Items are dynamically selected via Maximum Fisher Information $I_i(\hat{\theta})$. Diagnostic stopping rule terminates when $\operatorname{Var}(\theta) \le 0.15$ or a maximum of 10 items is reached.
- **Implementation Route:** Implementation route planned via `catsim` (or custom 2PL IRT Fisher information engine). Resulting latent ability $\hat{\theta} \in [-3, 3]$ maps to concept-level initial mastery via logistic link $p_{c,0} = \frac{1}{1 + \exp(-\hat{\theta})}$ clamped to $[0.01, 0.99]$ (ADR-009). The multi-concept Q-matrix linking diagnostic items to specific curriculum DAG nodes remains pending declaration.

### Method 4: Half-Life Regression (HLR) for Spaced Repetition
- **Mathematical Model:** Settles & Meeder (2016) Duolingo formulation modeling exponential memory decay:
  $$R_c(t) = 2^{-\frac{\Delta t}{H_c}}, \qquad \log_2 H_c = \Theta \cdot \mathbf{x}_c$$
  where $R_c$ is predicted recall probability, $\Delta t$ is elapsed time since last review, and $H_c$ is memory half-life predicted from feature vector $\mathbf{x}_c$ (repetition count, lapse count, difficulty).
- **Implementation Route:** Implemented as a continuous decay tracker where concepts with $R_c < 0.85$ become eligible for review, entering a unified priority scoring competition against new learning within the daily study budget $B$ (ADR-004). For cold-start concepts without review history, $H_c$ initializes to the empirical prior median $H_{\text{prior}}$.

### Method 5: Prerequisite-Constrained Knapsack on NetworkX DAG
- **Mathematical Model:** Multi-day curriculum scheduling formulated as a Precedence-Constrained Knapsack Problem (PCKP) over Directed Acyclic Graph $G = (V, E)$:
  $$\max \sum_{i \in S} \text{Score}_i \quad \text{s.t.} \quad \sum_{i \in S} \text{duration}_i \le B, \quad \text{Pred}(i) \subseteq S \cup \text{Mastered}$$
- **Implementation Route:** Built on `NetworkX` (`networkx==3.1`) for topological DAG validation (5 structural checks). Candidate universe generation extracts the target node and all ancestors (`src/trace/universe.py`). Solved daily via Score-Per-Minute (SPM) greedy heuristic (`src/planning/greedy.py`), evaluated against an exact exhaustive search DP oracle (`src/planning/oracle.py`, renamed `run_exhaustive_oracle` with $N \le 20$ cap and 2.0 s timeout) across a declared 250-instance benchmark (`src/planning/benchmark.py`).

---

## 2. Table of Differences Between Week 1 and Current Plan

Every difference between the Week 1 baseline plan and the current implementation plan, verified by direct document inspection with exact file and line citations:

| # | Topic / Area | Week 1 Plan | Current Plan (12 Oct 2026) | Reason / Justification | File & Line Citations |
|---|---|---|---|---|---|
| 1 | **Data Strategy Route** | Hybrid Junyi Academy plus ASSISTments 2009–2010 datasets for empirical fitting of all models (BKT, IRT, HLR) via 70/15/15 student splits. | Simulator-first approach using `SyntheticStudentGenerator` for controlled policy evaluation; public datasets (Junyi) relegated to optional secondary validation. | Real public datasets lack true latent state ground truth, contain no counterfactual paths for missed days, and have schema mismatch. | `weekly/W1.md:12-13`<br>`docs/DATA_STRATEGY.md:20-36`<br>`weekly/W2.md:20,323`<br>`src/simulation/simulator.py:1-20` |
| 2 | **ASSISTments Dataset** | ASSISTments 2009–2010 listed as co-primary public dataset for mathematics skill tracing and response time evaluation. | ASSISTments evaluation route explicitly **deferred**. | ASSISTments lacks curriculum prerequisite DAG annotations, has no concept-level lesson duration metrics, and presents licensing/schema hurdles. | `docs/PROBLEM_BOUNDARY.md:19`<br>`weekly/W1.md:12`<br>`docs/DATA_STRATEGY.md:47-50`<br>`weekly/W2.md:20,323` |
| 3 | **TC-3.2 Knapsack Approximation Claim** | Assumed/claimed greedy score-per-minute scheduler achieved a universal $\ge 95\%$ approximation ratio against the exact oracle. | Retracted universal guarantee; replaced with empirical distribution reporting target ($\bar{\rho} \ge 0.95$ over 250 instances; report mean, 5th pctile, worst-case min, and runtimes). | Discovery of hand-derived 12-vs-18 counterexample ($\rho = 0.6667$) and empirical knapsack pathology worst-case ($\rho = 0.2143$, seed 47 instance 215). | `decisions/ADR-003:33`<br>`docs/METRICS.md:24-74`<br>`TRACEABILITY.md:14`<br>`weekly/W2.md:47,199-215` |
| 4 | **Weak State Boundary** | Tentative boundary floating at $p < 0.35$ in early Week 2 notes and test fixtures. | Boundary strictly settled at $p < 0.40$ (strict inequality: $p < 0.40$ is Weak, $p = 0.40$ is Developing, requiring $\sigma^2 \le 0.05, n \ge 3,$ and window quorum). | Prevented misclassification of low-performing learners; aligns with asymmetric BKT posterior distributions. | `weekly/W2.md:46,91`<br>`docs/audits/W2_AUDIT.md:46`<br>`decisions/ADR-007:19`<br>`decisions/ADR-009:42-44`<br>`docs/FORMAL_MODELS.md:91`<br>`src/state/policy.py:22` |
| 5 | **Uncertain Classification Rule** | State classified as `Uncertain` solely when variance ceiling $\sigma^2 > 0.05$ was exceeded. | Added explicit interaction count threshold: $n < 3$ OR $\sigma^2 > 0.05 \implies \text{Uncertain}$. | Without $n < 3$, unprobed concepts with prior variance $\le 0.05$ could erroneously classify as Developing or Mastered, bypassing prerequisite checks. | `decisions/ADR-005:13-23`<br>`decisions/ADR-007:21`<br>`docs/FORMAL_MODELS.md:88`<br>`src/state/policy.py:24` |
| 6 | **CAT Diagnostic Skill Mapping** | Assumed latent ability $\hat{\theta}$ would map directly to concept-level initial mastery across all concepts. | Scalar mapping defined as $p_{c,0} = \operatorname{sigm}(\hat{\theta})$ clamped to $[0.01, 0.99]$, but **multi-concept Q-matrix linking CAT test items to curriculum DAG nodes remains undeclared**. | Unprobed concepts must remain `Uncertain` ($n=0$) without invented observations; item-to-skill graph matrix requires formal M2 design. | `decisions/ADR-002:28`<br>`decisions/ADR-009:32-40`<br>`tests/test_m2_adaptive_diagnostic.py:4-11` |
| 7 | **Sliding Evidence-Window Gate ($W=4$)** | Classification evaluated purely on instantaneous posterior point estimates $(p, \sigma^2)$. | Introduced 4-observation sliding window gate ($W=4$): Mastered requires $\ge 3/4$ correct; Weak requires $\ge 3/4$ incorrect; conflicting evidence defaults to Developing. | Under alternating responses ($[1,0,1,0]$), point updates caused variance to drop below $0.05$ and $p$ below $0.40$, prematurely assigning Weak to inconsistent learners. | `weekly/W2.md:253-258`<br>`decisions/ADR-007:15-22`<br>`docs/FORMAL_MODELS.md:86-93`<br>`src/state/policy.py:23` |
| 8 | **BKT Parameter Provenance & Parity** | Parameters sketched in code; early W2 used artificial zero-learning workaround ($p_T=0.0, p_S=p_G=0.20$) to pass alternating-evidence tests. | Zero-learning workaround rejected; canonical parameters locked in `config/bkt_params.yaml` ($p_S=0.10, p_G=0.20, p_T=0.15$), verified against `pyBKT==1.4.3`. | A zero-learning rate disables BKT skill acquisition; conflict gate structurally handles alternating evidence while preserving learning progression. | `docs/audits/W2_AUDIT.md:47-48`<br>`weekly/W2.md:254-258`<br>`config/bkt_params.yaml:1-6`<br>`tests/test_m1_bkt_parity.py:10-50` |
| 9 | **Feasibility Protocol** | Binary feasibility classification (feasible vs. infeasible). | Protocol partitioned into 4 distinct statuses: `CAPACITY_CHECK_PASSED`, `FEASIBLE`, `INFEASIBLE_PROVED` (with minimal actionable repair recommendations), and `HEURISTIC_NO_PLAN`. | Distinguishes mathematical impossibility (single block $> B$ or total work $> DB$) from heuristic packing failures, ensuring actionable remediation. | `docs/METRICS.md:17-21`<br>`src/planning/feasibility.py:7-12`<br>`tests/test_m3_states_feasibility.py:15-35` |
| 10 | **Unprobed Cold-Start Prior** | Conflicting prior specifications existed (`seeds.yaml` specified $p_L=0.10$; profiles had impossible $p=0.01, \sigma^2=0.25$). | Canonicalized to uninformative $\operatorname{Beta}(1, 1) \implies p_0=0.5, \kappa=2.0, n=0, \sigma^2 = 1/12 \approx 0.0833 \to \text{Uncertain}$. | Resolved mathematical inconsistency ($\sigma^2 \le p(1-p)$) and guaranteed all unprobed nodes start strictly Uncertain. | `weekly/W2.md:45`<br>`decisions/ADR-009-cold-start-prior-and-ability-mapping.md:28-31` |
| 11 | **Candidate Universe & Audit Trace Contract** | Conceptual trace requirement without strict universe definition or automated schema enforcement. | Formally defined Candidate Universe (target + all DAG ancestors); 8 mandatory schema fields; 8 strict `ReasonCode` values; 100% daily coverage invariant. | Ensures complete algorithmic accountability, detecting omitted, duplicated, or unjustified scheduling actions. | `decisions/ADR-003:34`<br>`TRACEABILITY.md:22-24`<br>`src/trace/universe.py:5-15`<br>`src/trace/schema.py:6-39`<br>`src/trace/checker.py:15-80`<br>`tests/test_m7_explainability.py:12-95` |
| 12 | **Exact Oracle Algorithm & Order Invariance** | Named `run_exact_dp_oracle`, but was recursive forward search whose output depended on input list ordering. | Renamed to `run_exhaustive_oracle` (with thin backwards-compatible alias); repaired to enumerate all precedence-closed subsets independently of input order. | A true benchmark oracle must be order-invariant and provably exact; input ordering cannot dictate optimal subset value. | `weekly/W2.md:106-110`<br>`src/planning/oracle.py:15-60`<br>`tests/test_m3_oracle_order.py:1-25` |
| 13 | **Bounded Contextual Bandit Scope** | Listed as optional exploration module without formal safety guardrails. | Formally bounded by deterministic admissibility layer (ADR-008): cannot override prerequisites or budget; latent simulator state is strictly invisible. | Protects pedagogical correctness; prevents exploratory bandit policies from violating hard curriculum constraints. | `weekly/W1.md:22`<br>`decisions/ADR-008:13-46`<br>`tests/test_simulation.py:25-40` |

---

## 3. Decision Record Status

The decision line and signature below are deliberately left unexecuted for human members of the project team to review, deliberate, and strike.

**Decision: REAFFIRMED / CHANGED (strike one)**  
**Decided by:** 
