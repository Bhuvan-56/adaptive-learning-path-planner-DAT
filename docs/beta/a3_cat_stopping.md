# Investigation: CAT Variance Stopping Rule Feasibility (Task Beta-A3)

## 1. Executive Summary

In the integrated benchmark specification (`experiments/w5_final.yaml`), the Computerized Adaptive Testing (CAT) diagnostic configuration defines:
```yaml
diagnostic:
  item_cap: 10
  stopping_variance: 0.15
```
During the baseline evaluation run, the variance-based stopping condition never triggered. This investigation evaluates whether the stopping rule $\operatorname{Var}(\hat\theta) \le 0.15$ can ever fire given the committed synthetic item bank (`data/processed/item_bank_synthetic.csv`).

**Plain Conclusion:**
> **The 0.15 variance stopping rule CANNOT fire with this item bank within 10 items.**
> Reaching $\operatorname{Var}(\hat\theta) \le 0.15$ within 10 items is mathematically impossible for any learner under any possible response sequence. All diagnostic administrations strictly terminate at the item cap of 10 items.

---

## 2. Empirical Variance Trajectory Across Declared Cases

We evaluated CAT diagnostics across all declared synthetic cases:
- **5 Cohort Seeds:** `[42, 101, 2024, 777, 999]` with 200 synthetic learners each (1000 learners).
- **3 Static Profile Learners:** `profile_1`, `profile_2`, `profile_3`.
- **Total Diagnostic Runs Evaluated:** 1,003 runs.

### Item-by-Item Variance Trajectory ($k = 1 \dots 10$)

| Item Number ($k$) | Minimum Variance | Mean Variance | Median Variance | Maximum Variance |
|:---:|:---:|:---:|:---:|:---:|
| 1 | 1.3890 | 2.0935 | 2.5161 | 2.5161 |
| 2 | 0.7678 | 1.0340 | 0.9983 | 1.2842 |
| 3 | 0.6020 | 0.7411 | 0.7738 | 0.8417 |
| 4 | 0.4436 | 0.5954 | 0.5768 | 0.7560 |
| 5 | 0.3886 | 0.4980 | 0.4564 | 0.7309 |
| 6 | 0.3272 | 0.4296 | 0.3871 | 0.7629 |
| 7 | 0.2912 | 0.3807 | 0.3368 | 0.7729 |
| 8 | 0.2601 | 0.3435 | 0.2961 | 0.7803 |
| 9 | 0.2372 | 0.3152 | 0.2666 | 0.8410 |
| **10** | **0.2182** | **0.2932** | **0.2448** | **0.9141** |

- **Minimum variance observed by item 10:** **0.218164**
- **Was 0.15 ever crossed?** **False (0 out of 1,003 runs)**
- **Termination distribution:** 100% of runs administered exactly 10 questions (`{10: 1003}`).

---

## 3. Mathematical Proof of Infeasibility (Theoretical Lower Bound)

Under the standard 2PL Item Response Theory (IRT) formulation without pseudo-guessing ($c = 0.0, d = 1.0$), the Fisher Information contribution of an administered item $i$ at estimated ability $\theta$ is:
$$I_i(\theta) = a_i^2 \cdot P_i(\theta) \cdot (1 - P_i(\theta))$$

Because $P(1 - P) \le 0.25$ for all $P \in [0, 1]$ (peaking when $P = 0.5$, i.e. when $\theta = b_i$), the maximum possible information contribution of item $i$ is strictly bounded:
$$I_{i,\max} = \frac{a_i^2}{4}$$

Total Fisher information from any subset of $k$ items is bounded by the sum of their individual maxima:
$$I_{\text{total}}(\theta) \le \sum_{i=1}^k \frac{a_i^2}{4}$$

Standard error and variance of the maximum likelihood estimate satisfy:
$$\operatorname{Var}(\hat\theta) = \operatorname{SEE}^2 = \frac{1}{I_{\text{total}}(\theta)} \ge \frac{1}{\sum_{i=1}^k \frac{a_i^2}{4}}$$

### Calculation for the Committed Item Bank
The committed item bank (`data/processed/item_bank_synthetic.csv`) contains 24 items. Sorting all items by maximum theoretical information $\frac{a_i^2}{4}$, the top 10 most discriminating items are:

1. `item_016` ($a=1.7354 \implies I_{\max}=0.7529$)
2. `item_012` ($a=1.5056 \implies I_{\max}=0.5667$)
3. `item_006` ($a=1.4198 \implies I_{\max}=0.5039$)
4. `item_010` ($a=1.4196 \implies I_{\max}=0.5038$)
5. `item_024` ($a=1.4179 \implies I_{\max}=0.5026$)
6. `item_002` ($a=1.3876 \implies I_{\max}=0.4814$)
7. `item_021` ($a=1.3858 \implies I_{\max}=0.4801$)
8. `item_018` ($a=1.3540 \implies I_{\max}=0.4583$)
9. `item_014` ($a=1.3331 \implies I_{\max}=0.4443$)
10. `item_008` ($a=1.3169 \implies I_{\max}=0.4336$)

Summing these top 10 items:
$$I_{\text{top10},\max} = 5.127638$$

Therefore, the **absolute theoretical lower bound on variance after 10 items** is:
$$\operatorname{Var}_{\min} = \frac{1}{5.127638} \approx \mathbf{0.195022}$$

Since $0.195022 > 0.15$:
- To reach $\operatorname{Var} \le 0.15$, total Fisher information must be at least:
  $$I_{\text{target}} \ge \frac{1}{0.15} \approx 6.6667$$
- Given the average information of top items in this bank ($\approx 0.40$), achieving $\operatorname{Var} \le 0.15$ requires at least **16 to 17 administered items**.
- Consequently, with `item_cap = 10`, the stopping variance of 0.15 is mathematically unreachable.

---

## 4. Policy and Architectural Impact

1. **Dead Stopping Code:** Lines 317 and 354 in `src/diagnostic/diagnostic.py` (`variance <= self.stopping_variance`) can never evaluate to True during a standard 10-item assessment with this bank.
2. **Deterministic Horizon:** Every diagnostic assessment operates as a fixed-length test of exactly 10 questions.
3. **Synthetic Calibration:** All numbers represent synthetic simulation behavior on synthetic item bank parameters.
