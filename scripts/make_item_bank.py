"""
Script to generate synthetic 2PL item bank and Q-matrix for computerized adaptive testing (CAT).

Generates:
1. data/processed/item_bank_synthetic.csv: 2PL item parameters (item_id, a, b, c, d)
2. data/processed/q_matrix_synthetic.csv: mapping of item_id -> concept_id
3. data/processed/item_bank_synthetic.provenance.json: provenance metadata labeled SYNTHETIC

Concepts covered:
Concepts A, B, C from demo_curriculum.json receive items.
Concept D receives NO direct items, exercising the ADR-009 rule:
"no direct item means n stays 0 and the state stays Uncertain".
"""

import argparse
import json
import os
import numpy as np
import pandas as pd


DEFAULT_CURRICULUM_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "curricula", "demo_curriculum.json")
)
DEFAULT_BANK_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "processed", "item_bank_synthetic.csv")
)
DEFAULT_QMATRIX_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "processed", "q_matrix_synthetic.csv")
)
DEFAULT_PROVENANCE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "processed", "item_bank_synthetic.provenance.json")
)


def generate_synthetic_item_bank_and_qmatrix(
    curriculum_path: str = DEFAULT_CURRICULUM_PATH,
    bank_path: str = DEFAULT_BANK_PATH,
    qmatrix_path: str = DEFAULT_QMATRIX_PATH,
    provenance_path: str = DEFAULT_PROVENANCE_PATH,
    seed: int = 42,
    items_per_concept: int = 8,
    unprobed_concept: str = "D",
) -> None:
    # 1. Load curriculum concepts
    with open(curriculum_path, "r", encoding="utf-8") as f:
        curr_data = json.load(f)
    all_concepts = [node["node_id"] for node in curr_data.get("nodes", [])]

    if unprobed_concept not in all_concepts:
        raise ValueError(f"Unprobed concept '{unprobed_concept}' not in curriculum concepts {all_concepts}")

    probed_concepts = [c for c in all_concepts if c != unprobed_concept]

    # 2. Random generation using seeded RNG
    rng = np.random.default_rng(seed)

    items = []
    q_matrix_rows = []

    item_counter = 1
    for concept in probed_concepts:
        for _ in range(items_per_concept):
            item_id = f"item_{item_counter:03d}"
            # Discrimination a ~ Normal(1.2, 0.25), clipped to [0.5, 2.5]
            a = float(np.clip(rng.normal(1.20, 0.25), 0.50, 2.50))
            # Difficulty b ~ Normal(0.0, 1.0), clipped to [-2.5, 2.5]
            b = float(np.clip(rng.normal(0.0, 1.0), -2.50, 2.50))
            # 2PL model parameters: c = 0.0 (pseudo-guessing), d = 1.0 (upper asymptote)
            c = 0.0
            d = 1.0

            items.append({
                "item_id": item_id,
                "a": round(a, 4),
                "b": round(b, 4),
                "c": c,
                "d": d,
            })
            q_matrix_rows.append({
                "item_id": item_id,
                "concept_id": concept,
            })
            item_counter += 1

    # 3. Save CSVs
    os.makedirs(os.path.dirname(bank_path), exist_ok=True)
    bank_df = pd.DataFrame(items)
    bank_df.to_csv(bank_path, index=False)

    q_df = pd.DataFrame(q_matrix_rows)
    q_df.to_csv(qmatrix_path, index=False)

    # 4. Save Provenance JSON labeled SYNTHETIC
    provenance = {
        "dataset_type": "SYNTHETIC",
        "label": "SYNTHETIC",
        "description": "Synthetic 2PL IRT item bank and Q-matrix for adaptive diagnostic evaluation",
        "seed": seed,
        "model": "2PL",
        "item_count": len(items),
        "concepts_in_curriculum": all_concepts,
        "probed_concepts": probed_concepts,
        "unprobed_concepts": [unprobed_concept],
        "generator_parameters": {
            "items_per_concept": items_per_concept,
            "discrimination_a": "Normal(mean=1.20, std=0.25), clipped to [0.50, 2.50]",
            "difficulty_b": "Normal(mean=0.0, std=1.0), clipped to [-2.50, 2.50]",
            "pseudo_guessing_c": 0.0,
            "upper_asymptote_d": 1.0,
        },
        "files": {
            "item_bank": os.path.relpath(bank_path, os.path.dirname(provenance_path)),
            "q_matrix": os.path.relpath(qmatrix_path, os.path.dirname(provenance_path)),
        },
    }

    with open(provenance_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    print(f"Generated {len(items)} synthetic items across concepts {probed_concepts}.")
    print(f"Unprobed concept without items: '{unprobed_concept}'.")
    print(f"Wrote item bank to {bank_path}")
    print(f"Wrote Q-matrix to {qmatrix_path}")
    print(f"Wrote provenance to {provenance_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic 2PL item bank and Q-matrix.")
    parser.add_argument("--curriculum", default=DEFAULT_CURRICULUM_PATH, help="Path to demo curriculum JSON")
    parser.add_argument("--bank-out", default=DEFAULT_BANK_PATH, help="Output item bank CSV")
    parser.add_argument("--qmatrix-out", default=DEFAULT_QMATRIX_PATH, help="Output Q-matrix CSV")
    parser.add_argument("--provenance-out", default=DEFAULT_PROVENANCE_PATH, help="Output provenance JSON")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--items-per-concept", type=int, default=8, help="Items per probed concept")
    args = parser.parse_args()

    generate_synthetic_item_bank_and_qmatrix(
        curriculum_path=args.curriculum,
        bank_path=args.bank_out,
        qmatrix_path=args.qmatrix_out,
        provenance_path=args.provenance_out,
        seed=args.seed,
        items_per_concept=args.items_per_concept,
    )
