"""Build the data files the website reads (site/data/*.json).

Integrated S0 numbers are from the run after the Week 7 adaptive deadlock fix
(docs/w7/deadlock_fix_results.md), with the run before it for comparison.

Run from the repository root with the project venv:
    .venv_w2/Scripts/python.exe site/build_data.py

Writes
  site/data/scheduling.json  per-instance ratios + summary numbers (Week 7 scheduling)
  site/data/s0_pooled.json   pooled five-seed integrated S0 arm table + paired differences
  site/data/fallback.json    saved outputs of every demo preset (shown when Pyodide is unavailable)

Every number is read from a committed file or computed from one with the
project's own functions; the source path travels with it into the JSON.
The script asserts that its numbers equal the ones in the committed
summaries, docs/w7/comparison.md (scheduling, unchanged arms) and
docs/w7/deadlock_fix_results.md (integrated S0), and stops if any differs.
"""
import csv
import json
import os
import re
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "site", "py"))
os.chdir(ROOT)

from src.evaluation.compare import compute_paired_bootstrap_ci  # noqa: E402
import demo_api  # noqa: E402

OUT = os.path.join(ROOT, "site", "data")
SCHED_DIR = "evaluation/results/w7/improvement/scheduling"
# Integrated S0 after the Week 7 adaptive deadlock fix (docs/w7/deadlock_fix_results.md);
# the run before the fix is kept for the before/after comparison.
S0_DIR = "evaluation/results/w7/deadlock_fix/integrated_s0"
S0_BEFORE_DIR = "evaluation/results/w7/improvement/integrated_s0"
BAD_CASES = "tests/fixtures/w7/bad_cases.json"
SEEDS = [42, 101, 2024, 777, 999]  # order used by scripts/w7_pooled_s0.py


def f4(x):
    return float(f"{x:.4f}")


# ---------------------------------------------------------------- scheduling
def build_scheduling():
    path = f"{SCHED_DIR}/per_instance.csv"
    df = pd.read_csv(path)
    bench = df[df.is_fixture.astype(str) == "False"].reset_index(drop=True)
    assert len(bench) == 250, len(bench)

    def stats(col):
        s = bench[col]
        return {
            "mean": f4(s.mean()),
            "p5": f4(s.quantile(0.05)),
            "min": f4(s.min()),
            "below_095": int((s < 0.95).sum()),
            "n": int(len(s)),
        }

    g = stats("greedy_ratio")
    b = stats("greedy_best_singleton_ratio")

    # Numbers as printed in the committed summary.md (shown verbatim on the page).
    summary_path = f"{SCHED_DIR}/summary.md"
    text = open(summary_path, encoding="utf-8").read()
    rows = {}
    for m in re.finditer(r"^\| (greedy(?:_best_singleton)?) \| ([^\n]+)\|$", text, re.M):
        cells = [c.strip() for c in m.group(2).split("|")]
        rows[m.group(1)] = cells
    diff = re.search(r"Paired ratio difference \(greedy_best_singleton minus greedy\): ([-\d.]+) \[([-\d.]+), ([-\d.]+)\]\. Claim: ([^\n]+)", text)
    changed = re.search(r"Instances where the score changed: (\d+) / (\d+)", text)

    # Cross-checks: recomputed from per_instance.csv == summary.md
    for key, st in (("greedy", g), ("greedy_best_singleton", b)):
        c = rows[key]
        assert f"{st['mean']:.4f}" == c[0] and f"{st['p5']:.4f}" == c[1] and f"{st['min']:.4f}" == c[2], (key, st, c)
        assert c[3] == f"{st['below_095']} / 250", (key, c[3])
    n_changed = int((bench.greedy_best_singleton_score != bench.greedy_score).sum())
    assert n_changed == int(changed.group(1)) == 10
    n_lower = int((bench.greedy_best_singleton_score < bench.greedy_score).sum())
    assert n_lower == 0

    fixtures = df[df.is_fixture.astype(str) == "True"]
    bad = json.load(open(BAD_CASES, encoding="utf-8"))

    return {
        "sources": {"per_instance": path, "summary": summary_path, "bad_cases": BAD_CASES},
        "instances": [
            {
                "case_id": r.case_id, "seed": int(r.seed), "instance_id": int(r.instance_id),
                "n_items": int(r.num_activities), "budget": int(r.budget),
                "oracle": int(r.oracle_score), "greedy": int(r.greedy_score),
                "greedy_ratio": float(r.greedy_ratio),
                "bs": float(r.greedy_best_singleton_score),
                "bs_ratio": float(r.greedy_best_singleton_ratio),
            }
            for r in bench.itertuples()
        ],
        "recomputed": {"greedy": g, "greedy_best_singleton": b, "changed": n_changed, "lower": n_lower},
        "summary_table": {
            "header": ["Policy", "Mean ratio", "5th pct", "Min", "Count < 0.95", "Runtime p50 (ms)", "Runtime p95 (ms)"],
            "rows": [[k] + rows[k] for k in ("greedy", "greedy_best_singleton")],
        },
        "paired_diff": {
            "mean": diff.group(1), "lo": diff.group(2), "hi": diff.group(3), "claim": diff.group(4).strip(),
            "line": diff.group(0),
        },
        "changed_line": changed.group(0),
        "fixtures_csv": [
            {
                "case_id": r.case_id, "budget": int(r.budget), "n_items": int(r.num_activities),
                "oracle": int(r.oracle_score), "greedy": int(r.greedy_score),
                "greedy_ratio": float(r.greedy_ratio), "bs": float(r.greedy_best_singleton_score),
                "bs_ratio": float(r.greedy_best_singleton_ratio),
            }
            for r in fixtures.itertuples()
        ],
        "bad_cases": bad["cases"],
    }


# ---------------------------------------------------------------- integrated S0
def trace_coverage():
    """Trace coverage per arm, as printed in each summary_seed_<s>.md."""
    cov = {}
    for s in SEEDS:
        p = f"{S0_DIR}/summary_seed_{s}.md"
        text = open(p, encoding="utf-8").read()
        sec = text.split("## 2.")[1].split("## 3.")[0]
        for m in re.finditer(r"^\| \*\*([a-z_]+)\*\* \| [^|]+\| [^|]+\| [^|]+\| ([\d.]+%) \|", sec, re.M):
            cov.setdefault(m.group(1), []).append(m.group(2))
    return cov


def build_s0():
    files = [f"{S0_DIR}/per_learner_seed_{s}.csv" for s in SEEDS]
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    assert len(df) == 9000
    cov = trace_coverage()
    arms = []
    for arm, g in df.groupby("arm", sort=False):  # file order, as in scripts/w7_pooled_s0.py
        m, lo, hi = compute_paired_bootstrap_ci(g.mastered_concepts.values, 1000, 0.95, 42)
        c = cov.get(arm)
        arms.append({
            "arm": arm, "n": int(len(g)),
            "mastered": f4(m), "lo": f4(lo), "hi": f4(hi),
            "no_plan_days": int(g.no_plan_days.sum()), "learner_days": int(len(g) * 5),
            "prereq_violations": int(g.prereq_violations.sum()),
            "budget_violations": int(g.budget_violations.sum()),
            "trace_coverage": (c[0] if c and len(set(c)) == 1 and len(c) == 5 else None),
        })

    def paired(a, b):
        ga = df[df.arm == a].sort_values("seed", kind="mergesort").reset_index(drop=True)
        gb = df[df.arm == b].sort_values("seed", kind="mergesort").reset_index(drop=True)
        assert (ga[["seed", "learner_id"]].values == gb[["seed", "learner_id"]].values).all()
        d = (ga.mastered_concepts - gb.mastered_concepts).values
        m, lo, hi = compute_paired_bootstrap_ci(d, 1000, 0.95, 42)
        if lo > 0:
            claim = f"{a} better (higher mastery)"
        elif hi < 0:
            claim = f"{b} better (higher mastery)"
        else:
            claim = "no difference shown"
        return {
            "a": a, "b": b, "mean": f4(m), "lo": f4(lo), "hi": f4(hi),
            "changed": int((d != 0).sum()), "up": int((d > 0).sum()), "down": int((d < 0).sum()),
            "claim": claim,
        }

    # The comparisons the evaluate command reports (summary_seed_<s>.md, sections 3 and 4), pooled.
    pairs = [
        ("adaptive_full", "static_prerequisite_order"),
        ("adaptive_full", "non_adaptive_greedy"),
        ("non_adaptive_greedy", "static_prerequisite_order"),
        ("non_adaptive_greedy_best_singleton", "non_adaptive_greedy"),
        ("ablation_no_diagnostic", "adaptive_full"),
        ("ablation_no_replan", "adaptive_full"),
        ("ablation_no_difficulty_step", "adaptive_full"),
        ("ablation_no_review", "adaptive_full"),
        ("ablation_no_remediation", "adaptive_full"),
    ]
    diffs = [paired(a, b) for a, b in pairs]

    # Before/after the deadlock fix, same learners (scripts/w7_deadlock_fix_compare.py).
    before_files = [f"{S0_BEFORE_DIR}/per_learner_seed_{s}.csv" for s in SEEDS]
    before = pd.concat([pd.read_csv(f) for f in before_files], ignore_index=True)
    fix_rows = []
    for arm in ("adaptive_full", "ablation_no_diagnostic", "ablation_no_difficulty_step",
                "ablation_no_review", "ablation_no_remediation"):
        ga = df[df.arm == arm].sort_values("seed", kind="mergesort").reset_index(drop=True)
        gb = before[before.arm == arm].sort_values("seed", kind="mergesort").reset_index(drop=True)
        assert (ga[["seed", "learner_id"]].values == gb[["seed", "learner_id"]].values).all()
        d = (ga.mastered_concepts - gb.mastered_concepts).values
        m, lo, hi = compute_paired_bootstrap_ci(d, 1000, 0.95, 42)
        # Per-arm CI in file order, as scripts/w7_pooled_s0.py does (only paired rows are sorted).
        bm, blo, bhi = compute_paired_bootstrap_ci(before[before.arm == arm].mastered_concepts.values, 1000, 0.95, 42)
        fix_rows.append({
            "arm": arm, "before_mastered": f4(bm), "before_lo": f4(blo), "before_hi": f4(bhi),
            "before_no_plan": int(gb.no_plan_days.sum()), "after_no_plan": int(ga.no_plan_days.sum()),
            "mean": f4(m), "lo": f4(lo), "hi": f4(hi),
            "changed": int((d != 0).sum()), "up": int((d > 0).sum()), "down": int((d < 0).sum()),
        })
    f0 = fix_rows[0]
    # docs/w7/comparison.md section 3: adaptive_full 1.9340 [1.8309, 2.0380], 4,000 no-plan days.
    assert (f0["before_mastered"], f0["before_lo"], f0["before_hi"], f0["before_no_plan"], f0["after_no_plan"]) == (1.9340, 1.8309, 2.0380, 4000, 1000), f0
    assert (f0["mean"], f0["lo"], f0["hi"], f0["changed"], f0["up"], f0["down"]) == (0.2420, 0.2110, 0.2740, 204, 204, 0), f0
    # Arms the fix must not change: identical per-learner columns except runtime_ms.
    cols = [c for c in df.columns if c != "runtime_ms"]
    for arm in ("static_prerequisite_order", "non_adaptive_greedy", "non_adaptive_greedy_best_singleton", "ablation_no_replan"):
        a = df[df.arm == arm].sort_values("seed", kind="mergesort").reset_index(drop=True)[cols]
        b = before[before.arm == arm].sort_values("seed", kind="mergesort").reset_index(drop=True)[cols]
        assert a.equals(b), arm

    # Cross-check against docs/w7/deadlock_fix_results.md (and docs/w7/comparison.md for unchanged arms).
    by = {a["arm"]: a for a in arms}
    expect = {
        "adaptive_full": (2.1760, 2.0800, 2.2680, 1000),
        "static_prerequisite_order": (2.0360, 1.9360, 2.1400, 0),
        "non_adaptive_greedy": (2.0360, 1.9360, 2.1400, 0),
        "non_adaptive_greedy_best_singleton": (2.0490, 1.9510, 2.1510, 0),
    }
    for arm, (m, lo, hi, np_days) in expect.items():
        a = by[arm]
        assert (a["mastered"], a["lo"], a["hi"], a["no_plan_days"]) == (m, lo, hi, np_days), (arm, a)
    d_bs = diffs[3]
    assert (d_bs["mean"], d_bs["lo"], d_bs["hi"], d_bs["changed"], d_bs["up"], d_bs["down"]) == (0.0130, 0.0040, 0.0230, 23, 18, 5), d_bs
    d_af = diffs[0]
    assert (d_af["mean"], d_af["lo"], d_af["hi"], d_af["changed"], d_af["up"], d_af["down"]) == (0.1400, 0.1110, 0.1690, 194, 156, 38), d_af
    assert all(a["trace_coverage"] == "100.0%" for a in arms if a["trace_coverage"] is not None)

    return {
        "sources": {
            "per_learner": files,
            "coverage": [f"{S0_DIR}/summary_seed_{s}.md" for s in SEEDS],
            "per_learner_before": before_files,
            "method": "scripts/w7_pooled_s0.py",
            "fix_method": "scripts/w7_deadlock_fix_compare.py",
            "checked_against": "docs/w7/deadlock_fix_results.md",
            "fix_prereg": "docs/w7/preregistration_deadlock_fix.md",
        },
        "arms": arms,
        "diffs": diffs,
        "fix": fix_rows,
    }


# ---------------------------------------------------------------- demo fallbacks
DEMO_A_PRESETS = {}
DEMO_B_PRESETS = {
    "cold_start": {"target": "D", "budget": 10, "deadline_days": 5, "answers": {}},
    "a_mastered": {"target": "D", "budget": 10, "deadline_days": 5, "answers": {"A": "1111"}},
    "weak_prereq": {"target": "D", "budget": 10, "deadline_days": 5, "answers": {"A": "1111", "B": "0000"}},
    "replan_practice": {
        "target": "D", "budget": 10, "deadline_days": 5, "answers": {"A": "1", "B": "1"}, "studied": ["A", "B"],
        "event": {"type": "assessment_result", "node": "B", "answers": "1"},
    },
    "block_too_big": {"target": "D", "budget": 8, "deadline_days": 5, "answers": {}},
    "too_few_days": {"target": "D", "budget": 10, "deadline_days": 2, "answers": {}},
    "replan_b_mastered": {
        "target": "D", "budget": 10, "deadline_days": 5, "answers": {"A": "1111"},
        "event": {"type": "assessment_result", "node": "B", "answers": "1111"},
    },
    "replan_missed_day": {
        "target": "D", "budget": 10, "deadline_days": 5, "answers": {"A": "1111"},
        "event": {"type": "missed_day"},
    },
}


def build_fallback(sched):
    for c in sched["bad_cases"]:
        DEMO_A_PRESETS[c["id"]] = {"items": c["items"], "budget": c["budget"]}
    out = {"generated_by": "site/build_data.py (same site/py/demo_api.py the live demo runs)", "a": {}, "b": {}, "states": {}}
    for k, p in DEMO_A_PRESETS.items():
        out["a"][k] = {"input": p, "output": demo_api.scheduler_compare(p)}
    for c in sched["bad_cases"]:  # fixture scores must be reproduced
        o = out["a"][c["id"]]["output"]
        assert o["greedy"]["score"] == c["greedy_score"] and o["oracle"]["score"] == c["oracle_score"], c["id"]
    for k, p in DEMO_B_PRESETS.items():
        out["b"][k] = {"input": p, "output": json.loads(json.dumps(demo_api.build_plan(p)))}
    for ans in ["", "1111", "0000", "1010", "11", "0"]:
        out["states"][ans] = demo_api.concept_state(ans)
    out["curriculum"] = demo_api.curriculum()
    return out


def check_jekyll_safe():
    """GitHub Pages builds the repo root with Jekyll, which skips any path whose
    file or folder name starts with "_" or "." and runs Liquid over files that
    start with YAML front matter ("---"). Check every file the site fetches."""
    js = open(os.path.join(ROOT, "site", "assets", "pyrunner.js"), encoding="utf-8").read()
    fetched = re.findall(r'^\s*"((?:src|data|config|experiments)/[^"]+)",', js, re.M)
    assert fetched, "no file list found in pyrunner.js"
    site_files = [os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                  for dp, _, fs in os.walk(os.path.join(ROOT, "site")) if "__pycache__" not in dp for f in fs]
    for p in fetched + site_files:
        assert os.path.isfile(os.path.join(ROOT, p)), f"missing {p}"
        assert not any(part.startswith(("_", ".")) for part in p.split("/")), f"Jekyll would skip {p}"
        if p.endswith((".py", ".json", ".yaml", ".html", ".js", ".css")):
            with open(os.path.join(ROOT, p), encoding="utf-8") as f:
                assert not f.read(3) == "---", f"Jekyll would treat {p} as a page (front matter)"
    print(f"jekyll check: {len(fetched)} fetched repo files + {len(site_files)} site files OK")


def main():
    check_jekyll_safe()
    os.makedirs(OUT, exist_ok=True)
    sched = build_scheduling()
    s0 = build_s0()
    fb = build_fallback(sched)
    for name, obj in (("scheduling.json", sched), ("s0_pooled.json", s0), ("fallback.json", fb)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, indent=1)
            f.write("\n")
        print("wrote", f"site/data/{name}")
    print("all cross-checks passed")


if __name__ == "__main__":
    main()
