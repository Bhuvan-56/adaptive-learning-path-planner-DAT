# Architecture Decision Record: ADR-004

## Decision ID & Date
ADR-004 | 2026-09-25

## Title
Half-Life Regression (HLR) for Spaced Repetition vs. Fixed-Interval Review

## Status
Reaffirmed (Decided at proposal time)

## Old / Current Approach
N/A — First decision.

## Evidence
- Settles & Meeder (2016) demonstrated that Half-Life Regression (HLR) predicts memory half-life $H_c$ and recall probability $R_c = 2^{-\Delta t / H_c}$ significantly better than fixed-interval models across large student interaction datasets.
- HLR models exponential memory decay continuously as a function of practice history features and concept properties, allowing review urgency to be computed dynamically.

## Alternatives Considered
1. **Fixed-Interval Review (e.g., Leitner / SM-2):** Schedules reviews after static delays. Simple, but fails to adapt to concept-specific difficulty or allow review items to compete dynamically against new learning within a daily time budget.
2. **Fixed Recall Threshold Rules without Scoring:** Triggers reviews immediately when recall drops below a threshold, forcing rigid schedule overrides.
3. **Half-Life Regression (HLR) with Unified Review Score Competition:** Computes continuous predicted recall $R_c = 2^{-\Delta t / H_c}$, flagging concepts with $R_c < 0.85$ as review-eligible, and placing them into a unified score competition with new learning:
   $$\text{ReviewScore}_c = w_1(1-R_c) + w_2(1-p_c) + w_3 I_c + w_4 U_c$$

## Selected Approach + Rationale
**Selected Approach:** Integrate Half-Life Regression (HLR) to model memory decay and compute continuous recall probability $R_c$, allowing review activities to compete against new learning within the daily budget $B$.

**Rationale:**
Fixed-interval review ignores the learner's daily time constraint $B$. By mapping memory decay into a continuous $\text{ReviewScore}_c$, spaced review activities compete mathematically against new learning gain $\text{Gain}_c = (1-p_c)p_{T,c}$ within the precedence-constrained knapsack planner. For unseen concepts without review history, $H_{c,0}$ is initialized to the empirical prior median $H_{\text{prior}}$, preventing undefined recall estimates.

## Impact on Milestones
- **M5 (Spaced Review and Remediation):** Directly drives spaced review eligibility ($R_c < 0.85$) and review activity insertion (TC-5.2).

## Revised Plan / Risks
None yet. HLR parameters will be fitted on Junyi Academy and ASSISTments student training logs. $H_{\text{prior}}$ initialized from median population half-life. Scoring weights $(w_1, w_2, w_3, w_4)$ frozen via dev set grid search prior to evaluation. Re-assessment scheduled for 09 October.
