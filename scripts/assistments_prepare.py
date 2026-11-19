"""Week 8 public-data extension, step 1-2: provenance record and cleaned, student-split ASSISTments logs.

Input : data/raw/skill_builder_data_corrected_collapsed.csv
        ASSISTments 2009-2010 Skill Builder, corrected version (one row per student-problem).
Output: data/provenance/assistments_2009_2010.json      (committed)
        data/processed/assistments/{train,dev,test}.csv  (git-ignored; rebuilt by this script)

Cleaning rules (each step's row count is written to the provenance record):
  1. keep original == 1           (drop scaffolding sub-questions)
  2. drop rows with no skill_name
  3. drop multi-skill rows        (skill_id contains "_", e.g. "1_13"; the corrected file
                                    collapses a problem's skills into one combined id)
  4. drop repeated (user_id, problem_id) rows, keeping the earliest order_id
  5. keep skills with >= MIN_STUDENTS students and >= MIN_ROWS rows
Rows are sorted by user_id, then order_id (temporal order within each learner is kept).
Students, not rows, are split 70/15/15 with a fixed seed, so no student is in two splits.

Usage: python scripts/assistments_prepare.py
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "skill_builder_data_corrected_collapsed.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed", "assistments")
PROV = os.path.join(ROOT, "data", "provenance", "assistments_2009_2010.json")

SEED = 20261119
SPLIT = (0.70, 0.15, 0.15)
MIN_STUDENTS = 50
MIN_ROWS = 500
COLUMNS = ["user_id", "skill_name", "skill_id", "problem_id", "order_id", "correct",
           "ms_first_response", "attempt_count", "hint_count"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.exists(RAW):
        sys.exit(f"Missing {RAW}. Download the corrected Skill Builder CSV first (see data/README.md).")

    # The file is not valid UTF-8 (some answer_text values); latin-1 reads every byte.
    df = pd.read_csv(RAW, encoding="latin-1", low_memory=False, usecols=COLUMNS + ["original"])
    steps = [{"step": "raw", "rows": int(len(df)), "students": int(df.user_id.nunique())}]

    def log(name, frame):
        steps.append({"step": name, "rows": int(len(frame)), "students": int(frame.user_id.nunique()),
                      "skills": int(frame.skill_name.nunique())})

    df = df[df.original == 1]
    log("original == 1", df)
    df = df.dropna(subset=["skill_name"])
    log("skill_name present", df)
    df = df[~df.skill_id.astype(str).str.contains("_")]
    log("single-skill rows only", df)
    df = df.sort_values(["user_id", "order_id"]).drop_duplicates(["user_id", "problem_id"], keep="first")
    log("first attempt per (user_id, problem_id)", df)

    per_skill = df.groupby("skill_name").agg(rows=("correct", "size"), students=("user_id", "nunique"))
    kept = per_skill[(per_skill.students >= MIN_STUDENTS) & (per_skill.rows >= MIN_ROWS)].index
    df = df[df.skill_name.isin(kept)].drop(columns=["original"])
    log(f"skills with >= {MIN_STUDENTS} students and >= {MIN_ROWS} rows", df)
    df["correct"] = df["correct"].astype(int)

    users = np.array(sorted(df.user_id.unique()))
    rng = np.random.default_rng(SEED)
    rng.shuffle(users)
    n_train = int(round(SPLIT[0] * len(users)))
    n_dev = int(round(SPLIT[1] * len(users)))
    split_of = {u: "train" for u in users[:n_train]}
    split_of.update({u: "dev" for u in users[n_train:n_train + n_dev]})
    split_of.update({u: "test" for u in users[n_train + n_dev:]})
    df["split"] = df.user_id.map(split_of)

    os.makedirs(OUT_DIR, exist_ok=True)
    outputs = {}
    for name in ("train", "dev", "test"):
        part = df[df.split == name].drop(columns=["split"])
        path = os.path.join(OUT_DIR, f"{name}.csv")
        part.to_csv(path, index=False)
        outputs[name] = {"file": os.path.relpath(path, ROOT).replace(os.sep, "/"), "rows": int(len(part)),
                         "students": int(part.user_id.nunique()), "sha256": sha256(path)}

    skills = (df.groupby("skill_name")
                .agg(rows=("correct", "size"), students=("user_id", "nunique"), p_correct=("correct", "mean"))
                .sort_values("rows", ascending=False))

    record = {
        "dataset_type": "PUBLIC_REAL_LEARNER_DATA",
        "dataset": "ASSISTments 2009-2010 Skill Builder, corrected version (skill_builder_data_corrected_collapsed.csv)",
        "source_page": "https://sites.google.com/site/assistmentsdata/home/2009-2010-assistment-data/skill-builder-data-2009-2010",
        "download_link": "https://drive.google.com/file/d/1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE/view?usp=sharing",
        "acquisition_date": "2026-11-19",
        "raw_file": os.path.relpath(RAW, ROOT).replace(os.sep, "/"),
        "raw_sha256": sha256(RAW),
        "raw_encoding": "not valid UTF-8; read as latin-1",
        "terms_of_use": "https://sites.google.com/site/assistmentsdata/termsofuseforusingdata (research and educational use; see the page)",
        "citation": "Feng, M., Heffernan, N.T., & Koedinger, K.R. (2009). Addressing the assessment challenge in an "
                    "online system that tutors as it assesses. User Modeling and User-Adapted Interaction, 19(3), 243-266. "
                    "Dataset URL as source_page.",
        "field_mapping": {
            "user_id": "learner id",
            "skill_name": "concept (ASSISTments skill; NOT a node of either project curriculum)",
            "correct": "first-attempt correctness (0/1)",
            "order_id": "temporal order of attempts within a learner",
            "ms_first_response": "milliseconds to first response (timing; not yet used)",
            "attempt_count, hint_count": "kept for reference; not used by BKT",
        },
        "prerequisite_fields": "none in this dataset; no prerequisite edges are taken from it",
        "timing_fields": "ms_first_response (milliseconds)",
        "cleaning_steps": steps,
        "skill_filter": {"min_students": MIN_STUDENTS, "min_rows": MIN_ROWS, "skills_kept": int(len(kept))},
        "split": {"unit": "student", "ratios": list(SPLIT), "seed": SEED, "outputs": outputs},
        "skills": {k: {"rows": int(v.rows), "students": int(v.students), "p_correct": round(float(v.p_correct), 4)}
                   for k, v in skills.iterrows()},
        "fallbacks": "none; every field used is observed in the dataset",
    }
    os.makedirs(os.path.dirname(PROV), exist_ok=True)
    with open(PROV, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    for s in steps:
        print(s)
    for k, v in outputs.items():
        print(k, v["rows"], "rows", v["students"], "students")
    print("skills kept:", len(kept))


if __name__ == "__main__":
    main()
