"""Week 8 public-data extension, step 3-4: fit standard BKT per ASSISTments skill and test it on held-out students.

Needs the files written by scripts/assistments_prepare.py. Fitting uses pyBKT (EM, train students only).
Fitting is resumable: each fitted skill is cached, so the script can be stopped and re-run
(--max-seconds limits one run). When every skill is fitted, test-set prediction is scored.

Prediction is the standard BKT forward pass with the fitted parameters (written out below so the
number is easy to check): before each attempt p(correct) = L(1 - S) + (1 - L)G; then L is updated
by Bayes on the observed answer and by the learn transition T. Forgetting is off.

Baselines on the same test rows:
  * BKT with the engine's default parameters (config/bkt_params.yaml: p_S 0.10, p_G 0.25,
    p_T 0.10; cold-start prior 0.5), the values the planner and simulator S0 assume
  * skill_mean   - each skill's training correct-rate (no learning over time)
  * majority     - always predicts the majority class of the training data
Metrics: AUC, RMSE, accuracy, log loss, and ECE (10 equal-width bins, the project's
src/evaluation/calibration.py definition). Fitted vs engine-default log loss is also compared
per test student (mean log loss per student, paired over students, compute_paired_bootstrap_ci,
B = 1000, seed 42): the ADR-001 revisit test.

Outputs:
  config/bkt_assistments.yaml                              per-skill fitted parameters (committed)
  evaluation/results/w8/assistments_bkt/metrics.txt        overall comparison
  evaluation/results/w8/assistments_bkt/per_skill.csv      per-skill test metrics
  evaluation/results/w8/assistments_bkt/fit_cache.json     resumable fit cache

Usage (project root):  python scripts/assistments_fit_bkt.py [--max-seconds 150]
"""
import argparse
import json
import os
import re
import time

import numpy as np
import pandas as pd
import sys

import yaml
from pyBKT.models import Model

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.evaluation.calibration import expected_calibration_error  # noqa: E402
from src.evaluation.compare import compute_paired_bootstrap_ci  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "processed", "assistments")
PROV = os.path.join(ROOT, "data", "provenance", "assistments_2009_2010.json")
OUT_CFG = os.path.join(ROOT, "config", "bkt_assistments.yaml")
OUT_DIR = os.path.join(ROOT, "evaluation", "results", "w8", "assistments_bkt")
CACHE = os.path.join(OUT_DIR, "fit_cache.json")
SEED = 20261119
NUM_FITS = 5
COLS = ["user_id", "skill_name", "correct", "order_id"]
ENGINE_DEFAULT = {"prior": 0.5, "p_S": 0.10, "p_G": 0.25, "p_T": 0.10}


def auc(y, p):
    """Rank-based ROC AUC (ties get the average rank)."""
    y = np.asarray(y, dtype=int)
    r = pd.Series(np.asarray(p, dtype=float)).rank(method="average").to_numpy()
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def metrics(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    return {"auc": auc(y, p), "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
            "accuracy": float(np.mean((p >= 0.5) == (y == 1))),
            "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))),
            "ece": expected_calibration_error(list(p), [int(v) for v in y]), "n": int(len(y))}


def fit_skills(train, skills, max_seconds):
    os.makedirs(OUT_DIR, exist_ok=True)
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    start = time.time()
    # Smallest skills first, so short runs make visible progress.
    for skill in sorted(skills, key=lambda s: (train.skill_name == s).sum()):
        if skill in cache:
            continue
        if max_seconds and time.time() - start > max_seconds:
            break
        d = train[train.skill_name == skill]
        m = Model(seed=SEED, num_fits=NUM_FITS, parallel=False)
        # pyBKT reads `skills` as a regex; escape names such as "+,-,/,* ()".
        m.fit(data=d[COLS], skills="^" + re.escape(skill) + "$", parallel=False)
        v = m.params().loc[skill]["value"]
        cache[skill] = {
            "prior": float(v.loc[("prior", "default")]),
            "p_T": float(v.loc[("learns", "default")]),
            "p_G": float(v.loc[("guesses", "default")]),
            "p_S": float(v.loc[("slips", "default")]),
            "forget": float(v.loc[("forgets", "default")]),
            "train_rows": int(len(d)),
        }
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=1)
        print(f"fitted {skill} ({len(d)} rows) [{len(cache)}/{len(skills)}]", flush=True)
    return cache


def bkt_forward(df, params):
    """p(correct) before each attempt, per (user, skill) sequence in order_id order."""
    out = np.empty(len(df))
    users = df.user_id.to_numpy()
    skills = df.skill_name.to_numpy()
    ys = df.correct.to_numpy()
    prev = (None, None)
    L = 0.0
    for i in range(len(df)):
        key = (users[i], skills[i])
        p = params[skills[i]]
        if key != prev:
            L = p["prior"]
            prev = key
        pc = L * (1 - p["p_S"]) + (1 - L) * p["p_G"]
        out[i] = pc
        if ys[i] == 1:
            post = L * (1 - p["p_S"]) / pc
        else:
            post = L * p["p_S"] / (1 - pc)
        L = post + (1 - post) * p["p_T"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-seconds", type=float, default=0, help="stop fitting after this many seconds (0 = no limit)")
    args = ap.parse_args()

    train = pd.read_csv(os.path.join(DATA, "train.csv"), usecols=COLS)
    test = pd.read_csv(os.path.join(DATA, "test.csv"), usecols=COLS)
    train = train.sort_values(["user_id", "skill_name", "order_id"]).reset_index(drop=True)
    test = test.sort_values(["user_id", "skill_name", "order_id"]).reset_index(drop=True)
    skills = sorted(train.skill_name.unique())

    fitted = fit_skills(train, skills, args.max_seconds)
    if len(fitted) < len(skills):
        print(f"{len(fitted)}/{len(skills)} skills fitted; run again to continue.")
        return

    test = test[test.skill_name.isin(skills)].reset_index(drop=True)
    y = test.correct.to_numpy()
    majority = float(train.correct.mean() >= 0.5)
    skill_mean = train.groupby("skill_name").correct.mean()
    test["p_bkt"] = bkt_forward(test, fitted)
    test["p_skill_mean"] = test.skill_name.map(skill_mean)
    test["p_default"] = bkt_forward(test, {s: ENGINE_DEFAULT for s in skills})
    overall = {
        "BKT (pyBKT fit, per skill)": metrics(y, test.p_bkt),
        "BKT, engine defaults": metrics(y, test.p_default),
        "skill_mean baseline": metrics(y, test.p_skill_mean),
        "majority baseline": metrics(y, np.full(len(test), majority)),
    }

    rows = []
    for skill, g in test.groupby("skill_name"):
        b = metrics(g.correct, g.p_bkt)
        s = metrics(g.correct, g.p_skill_mean)
        f = fitted[skill]
        rows.append({"skill_name": skill, "n_test": b["n"], "bkt_auc": round(b["auc"], 4),
                     "bkt_rmse": round(b["rmse"], 4), "skill_mean_rmse": round(s["rmse"], 4),
                     **{k: round(f[k], 4) for k in ("prior", "p_T", "p_G", "p_S")}})
    per_skill = pd.DataFrame(rows).sort_values("n_test", ascending=False)
    per_skill.to_csv(os.path.join(OUT_DIR, "per_skill.csv"), index=False)

    with open(PROV, encoding="utf-8") as f:
        prov = json.load(f)
    better = int((per_skill.bkt_rmse < per_skill.skill_mean_rmse).sum())
    lines = [
        "ASSISTments 2009-2010 (corrected) - standard BKT, fitted on train students, scored on test students",
        f"raw sha256: {prov['raw_sha256']}",
        f"skills: {len(skills)}   train rows: {len(train)}   test rows scored: {len(test)}   "
        f"test students: {test.user_id.nunique()}",
        f"pyBKT EM, seed {SEED}, num_fits {NUM_FITS}, forgetting off; prediction = BKT forward pass",
        "",
        f"{'model':<28}{'AUC':>8}{'RMSE':>8}{'acc':>8}{'logloss':>9}{'ECE':>8}",
    ]
    for name, m in overall.items():
        lines.append(f"{name:<28}{m['auc']:>8.4f}{m['rmse']:>8.4f}{m['accuracy']:>8.4f}"
                     f"{m['log_loss']:>9.4f}{m['ece']:>8.4f}")
    def student_ll(col):
        pc = np.clip(test[col].to_numpy(), 1e-6, 1 - 1e-6)
        ll = -(test.correct * np.log(pc) + (1 - test.correct) * np.log(1 - pc))
        return ll.groupby(test.user_id).mean()
    diff = (student_ll("p_bkt") - student_ll("p_default")).to_numpy()
    dm, dlo, dhi = compute_paired_bootstrap_ci(diff, 1000, 0.95, 42)
    lines += ["", f"Log loss, fitted - engine defaults, per test student (n = {len(diff)}): "
                  f"{dm:+.4f} [{dlo:+.4f}, {dhi:+.4f}] "
                  f"({'fitted better' if dhi < 0 else ('defaults better' if dlo > 0 else 'no difference shown')})"]
    lines += ["", f"BKT RMSE below skill_mean RMSE in {better} of {len(per_skill)} skills", "",
              "Fitted parameters across skills: median [min, max]"]
    for k in ("prior", "p_T", "p_G", "p_S"):
        v = per_skill[k]
        lines.append(f"  {k:<6} {v.median():.3f} [{v.min():.3f}, {v.max():.3f}]")
    text = "\n".join(lines)
    with open(os.path.join(OUT_DIR, "metrics.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)

    cfg = {
        "dataset_type": "PUBLIC_REAL_LEARNER_DATA",
        "description": "Standard 4-parameter BKT fitted per skill on ASSISTments 2009-2010 Skill Builder "
                       "(corrected), train students only. Skills are ASSISTments skills, not project curriculum nodes.",
        "provenance": "data/provenance/assistments_2009_2010.json",
        "fit": {"library": "pyBKT", "seed": SEED, "num_fits": NUM_FITS, "forgets": False},
        "skills": {s: {k: round(fitted[s][k], 6) for k in ("prior", "p_T", "p_G", "p_S")} for s in skills},
    }
    with open(OUT_CFG, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


if __name__ == "__main__":
    main()
