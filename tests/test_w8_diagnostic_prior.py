"""W8 fix 3 (LIMITATIONS.md B10): the CAT diagnostic's evidence must reach the
planner. A concept probed by k diagnostic items gets n = k (and kappa = 2 + k,
one pseudo-count per observation, as in ConceptState.update), so with k >= 3 it
is no longer Uncertain. Unprobed concepts stay cold-start / n = 0."""
import os

import pandas as pd
import pytest
import yaml

from src.diagnostic import diagnostic as diag
from src.diagnostic.diagnostic import ability_to_prior, run_adaptive_diagnostic
from src.evaluation import integrated
from src.state.policy import PolicyConfig

ROOT = os.path.join(os.path.dirname(__file__), "..")
MATHS_CURRICULUM = os.path.join(ROOT, "data", "curricula", "maths_curriculum.json")
MATHS_QMATRIX = os.path.join(ROOT, "data", "processed", "q_matrix_maths.csv")
TOY_QMATRIX = os.path.join(ROOT, "data", "processed", "q_matrix_synthetic.csv")
POLICY = PolicyConfig()


def _counts(res, qmatrix=TOY_QMATRIX):
    q = dict(pd.read_csv(qmatrix)[["item_id", "concept_id"]].values)
    out = {}
    for item in res.items_asked:
        out[q[item]] = out.get(q[item], 0) + 1
    return out


def _run(answer, **kw):
    return run_adaptive_diagnostic(respond=lambda _item: answer, **kw)


def test_high_theta_probed_concepts_are_not_uncertain():
    res = _run(1)
    counts = _counts(res)
    p_hat = ability_to_prior(res.theta_hat)
    assert p_hat > 0.5
    assert max(counts.values()) >= 4  # 10 items over 3 concepts
    for c, k in counts.items():
        st = res.concept_states[c]
        assert st.n == k
        assert st.kappa == pytest.approx(2.0 + k)
        assert st.p == pytest.approx(p_hat)  # ADR-009 mapping unchanged
        assert st.sigma2 == pytest.approx(st.p * (1 - st.p) / (st.kappa + 1))
        if k >= 3:
            assert st.classify(POLICY) != "Uncertain"
        if k >= POLICY.window_size:
            # All answers correct. The bank's estimator caps theta_hat near 1.13
            # (p ~ 0.755 < mastered_p 0.85), so the unchanged mapping gives Developing.
            assert st.classify(POLICY) == ("Mastered" if p_hat >= POLICY.mastered_p else "Developing")


def test_low_theta_probed_concepts_are_weak():
    res = _run(0)
    counts = _counts(res)
    assert ability_to_prior(res.theta_hat) < POLICY.weak_p
    assert max(counts.values()) >= 4
    for c, k in counts.items():
        st = res.concept_states[c]
        assert st.n == k
        if k >= POLICY.window_size:
            assert st.classify(POLICY) == "Weak"
        elif k >= 3:
            assert st.classify(POLICY) != "Uncertain"


@pytest.mark.parametrize("kw", [
    {},
    {"curriculum_source": MATHS_CURRICULUM, "qmatrix_source": MATHS_QMATRIX},
])
def test_unprobed_concepts_stay_cold_start(kw):
    res = _run(1, **kw)
    asked = set(_counts(res, kw.get("qmatrix_source", TOY_QMATRIX)))
    unasked = [c for c in res.concept_states if c not in asked]
    assert unasked  # toy: D has no items; maths: 13 of 16 concepts have none
    for c in unasked:
        st = res.concept_states[c]
        assert st.n == 0 and st.history == []
        assert st.kappa == pytest.approx(2.0)
        assert st.classify(POLICY) == "Uncertain"


def test_diagnostic_record_shows_n_and_item_count_per_concept():
    res = _run(1)
    counts = _counts(res)
    rec = diag.describe_concept_priors(res, POLICY)
    assert set(rec) == set(res.concept_states)
    for c, row in rec.items():
        assert row["items_answered"] == counts.get(c, 0)
        assert row["n"] == res.concept_states[c].n
        assert row["kappa"] == pytest.approx(res.concept_states[c].kappa)
        assert row["class"] == res.concept_states[c].classify(POLICY)


def test_recount_accepts_prerequisites_mastered_at_start():
    """A prerequisite that was evidence-Mastered before day 1 is met without being studied."""
    import networkx as nx
    g = nx.DiGraph()
    for c in "ABD":
        g.add_node(c, baseline_duration=3)
    g.add_edge("A", "D")
    g.add_edge("B", "D")
    days = [{"day": 1, "activities": ["A", "D"]}]
    assert integrated.recount_plan_violations(days, g, 10) == (1, 0)
    assert integrated.recount_plan_violations(days, g, 10, initially_mastered={"B"}) == (0, 0)
    assert integrated.recount_plan_violations(days, g, 10, initially_mastered=set()) == (1, 0)


def _small_run(tmp_path, monkeypatch):
    with open(os.path.join(ROOT, "experiments", "w8_final.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["seeds"] = [42]
    p = tmp_path / "w8_final.yaml"
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    plans = []  # recount_plan_violations is called once per (arm, learner), arms in config order
    real = integrated.recount_plan_violations

    def spy(executed_days, g, budget, **kw):
        plans.append([tuple(d["activities"]) for d in executed_days])
        return real(executed_days, g, budget, **kw)

    monkeypatch.setattr(integrated, "recount_plan_violations", spy)
    res = integrated.run_integrated_evaluation(config_path=str(p), output_dir=str(tmp_path / "out"),
                                               override_learners=20, override_resamples=20)
    arms = list(res["arm_results"])
    by_arm = {a: plans[i * 20:(i + 1) * 20] for i, a in enumerate(arms)}
    return res, by_arm


def test_diagnostic_changes_a_plan_in_the_integrated_loop(tmp_path, monkeypatch):
    res, by_arm = _small_run(tmp_path, monkeypatch)
    diffs = sum(a != b for a, b in zip(by_arm["adaptive_full"], by_arm["ablation_no_diagnostic"]))
    assert diffs >= 1
    for r in res["arm_results"].values():
        assert r.total_prereq_violations == 0 and r.total_budget_violations == 0
        assert r.trace_coverage == 100.0


def test_baseline_arms_unchanged_against_committed_run(tmp_path, monkeypatch):
    """Control: static and greedy baselines keep the pre-fix (n = 0) priors."""
    res, _ = _small_run(tmp_path, monkeypatch)
    new = pd.read_csv(res["csv_path"]).drop(columns="runtime_ms")
    old = pd.read_csv(os.path.join(ROOT, "evaluation/results/w8/final/integrated_s0/per_learner_seed_42.csv"))
    old = old[old.learner_id.isin(new.learner_id.unique())].drop(columns="runtime_ms")
    base = ["static_prerequisite_order", "non_adaptive_greedy", "non_adaptive_greedy_best_singleton"]
    new = new[new.arm.isin(base)].reset_index(drop=True)
    old = old[old.arm.isin(base)].reset_index(drop=True)
    assert len(new) == 60
    pd.testing.assert_frame_equal(new, old, check_dtype=False)
