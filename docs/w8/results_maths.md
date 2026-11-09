# Week 8 Results (addendum 2): Larger Curriculum and Mismatched Simulator

Pre-registration: [`preregistration_maths.md`](preregistration_maths.md) (commit `315d4f9`); tests first `b147713`; harness change `9b50338`. All three new runs record code `9b50338` in their manifests. Every figure is simulator behaviour on synthetic learners: 1,000 paired learners per run (5 seeds × 200), B = 1,000 paired bootstrap resamples, pooled with `scripts/w7_pooled_s0.py` (`--horizon=10` for maths).

| Run | Curriculum | Simulator | Days × budget | Output |
|---|---|---|---|---|
| toy-S0 | toy, 4 concepts | matched BKT | 5 × 10 min | `evaluation/results/w8/final/integrated_s0/` (existing) |
| toy-S3 | toy, 4 concepts | mismatched PFA | 5 × 10 min | `evaluation/results/w8/maths_eval/toy_s3/` |
| maths-S0 | maths, 16 concepts, target INT | matched BKT | 10 × 30 min | `evaluation/results/w8/maths_eval/maths_s0/` |
| maths-S3 | maths, 16 concepts, target INT | mismatched PFA | 10 × 30 min | `evaluation/results/w8/maths_eval/maths_s3/` |

The runtime rule was not triggered: about 3.5 minutes per 200-learner maths seed, against the 45-minute limit. The full 200 learners per seed were used.

## 1. Hard constraints: passed

0 prerequisite violations and 0 budget violations in every arm of all three runs. Trace coverage is 100% for the four primary arms in all 15 per-seed summaries. Toy-S0 is reproduced exactly: `tests/test_w8_maths_eval.py::test_toy_s0_unchanged_against_committed_run`.

## 2. Primary result: the adaptive advantage holds in every cell

Concepts truly mastered at the end; paired difference adaptive_full minus baseline, 95% CI:

| Run | adaptive_full | static order | greedy | adaptive − static | adaptive − greedy |
|---|---|---|---|---|---|
| toy-S0 | 2.1760 | 2.0360 | 2.0360 | +0.1400 [0.1110, 0.1690] | +0.1400 [0.1110, 0.1690] |
| toy-S3 | 2.6880 | 2.3340 | 2.3340 | **+0.3540 [0.2990, 0.4100]** | +0.3540 [0.2990, 0.4100] |
| maths-S0 (of 16) | 6.4680 | 6.2540 | 6.3370 | **+0.2140 [0.1600, 0.2680]** | +0.1310 [0.0840, 0.1810] |
| maths-S3 (of 16) | 7.5870 | 6.7760 | 7.0980 | **+0.8110 [0.6980, 0.9170]** | +0.4890 [0.3730, 0.5990] |

Retained recall after 7 days, adaptive minus static: toy-S3 +0.0748 [0.0695, 0.0805], maths-S0 +0.0876 [0.0819, 0.0931], maths-S3 +0.1046 [0.0999, 0.1089]. Adaptive minus greedy is also positive in all three new runs.

**Claim:** adaptive_full is better than both baselines in all four cells, on mastery and on retained recall.

The pre-registration did not predict a direction for S3. The advantage there is **larger**, not smaller. Read this with care: in the PFA simulator, learning comes only from the number of practice attempts. The adaptive arm practises concepts it cannot yet prove (practice for evidence), so it gets more attempts, and this simulator rewards attempts directly. "The advantage survives a mismatched simulator" is supported. "It is larger with real learners" is not.

## 3. Best-singleton fallback: helps on the larger curriculum

non_adaptive_greedy_best_singleton − non_adaptive_greedy:
- maths-S0: +0.0930 [0.0720, 0.1150]
- maths-S3: +0.0760 [0.0530, 0.0990]
- toy-S3: +0.0040 [−0.0130, 0.0220], no difference shown

On toy-S0 it was +0.0130 [0.0040, 0.0230], and under toy-S1 there was no difference. With 10–25 minute topics and a 30-minute day, the score-per-minute greedy more often leaves a valuable long topic out, which is the case the fallback was built for.

## 4. Ablations: the prediction was not met

Pre-registered expectation: "at least one replan ablation differs from adaptive_full on the maths curriculum (difficulty under S3 is the most likely)".

| Ablation − adaptive_full | toy-S3 | maths-S0 | maths-S3 |
|---|---|---|---|
| no_diagnostic | 0.0000 (identical) | 0.0000 (identical) | 0.0000 (identical) |
| no_difficulty_step | −0.0020 [−0.0050, 0.0000], 2 learners | 0.0000 (identical) | −0.0010 [−0.0080, 0.0040], 9 learners |
| no_review | 0.0000 (identical) | 0.0000 (identical) | 0.0000 (identical) |
| no_remediation | 0.0000 (identical, by construction) | 0.0000 | 0.0000 |
| no_replan | −0.3540 | −0.2140 | −0.8110 |

- `no_replan` is the static plan with difficulty stepping, so its loss is the adaptive advantage itself, not a component.
- Difficulty stepping now changes a handful of learners under S3, which responds to item difficulty, but no difference is shown.
- **Why the diagnostic can never matter (found here):** the diagnostic gives each concept a prior p from θ̂, but with n = 0 observations (`ConceptState.init_from_ability`). The classifier labels anything with n < 3 Uncertain, so every diagnosed concept starts Uncertain, the same as a cold start. Plans depend on the class, so the CAT result cannot change any plan, on any curriculum. This is a design limit, not noise, and it explains the identical `no_diagnostic` rows in every run since Week 5.
- Review and remediation stay inactive for the reasons in `docs/w8/results.md` §5 and `docs/final/LIMITATIONS.md` B1–B2.

So the evidence supports the whole adaptive loop against static and greedy baselines. It still cannot credit the diagnostic, difficulty, review or remediation components separately.

## 5. Other observations

- **The best-effort plan now matters.** On the maths curriculum, 4,000 of adaptive_full's 6,000 no-plan learner-days are `CAPACITY_EXCEEDED`: the remaining work no longer fits before the deadline. Since Week 8, those days still run the work that fits instead of idling. The other 2,000 are `SCHEDULING_CONSTRAINTS_UNMET`. Static and greedy arms have no no-plan days, by definition.
- **Runtime:** adaptive_full planning takes 123 ms (p50) and 245 ms (p95) per learner for the whole 10-day maths horizon, against 4 ms for the static plan.

## Decision

Report the adaptive advantage as holding on a 16-concept curriculum and under a mismatched simulator, with the caveat in §2. Record the diagnostic-prior limit (§4) in `docs/final/LIMITATIONS.md`. No code is changed in response to these results.
