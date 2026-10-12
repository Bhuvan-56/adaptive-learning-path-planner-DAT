"""
Example script to fit pyBKT on synthetic student response data,
save fitted parameters to config/bkt_fitted.yaml with provenance,
and predict correctness probability on a held-out student.

PROVENANCE:
- Data source: data/processed/synthetic_bkt_responses.csv (SYNTHETIC DATA)
- Student split: by student_id (NOT by row)
"""

import os
import yaml
import pandas as pd
from pyBKT.models import Model


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_path = os.path.join(repo_root, "data", "processed", "synthetic_bkt_responses.csv")
    output_config_path = os.path.join(repo_root, "config", "bkt_fitted.yaml")

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Synthetic data file not found at: {data_path}")

    # Load synthetic responses
    df = pd.read_csv(data_path)

    # Held-out student split by student ID (not by row)
    heldout_student_id = "student_10"
    train_df = df[df["user_id"] != heldout_student_id].copy()
    test_df = df[df["user_id"] == heldout_student_id].copy()

    print(f"Total rows: {len(df)}")
    print(f"Training students: {sorted(train_df['user_id'].unique())} ({len(train_df)} rows)")
    print(f"Held-out student: {heldout_student_id} ({len(test_df)} rows)")

    # Initialize pyBKT model
    # parallel=False avoids Windows multiprocessing paging file limits
    model = Model(seed=42, num_fits=1, parallel=False)

    print("\nFitting pyBKT on training students...")
    model.fit(data=train_df)

    # Extract fitted parameters
    params_df = model.params()
    print("\nFitted Parameters DataFrame:")
    print(params_df)

    skill_name = "Addition"
    prior_val = float(params_df.loc[(skill_name, "prior", "default"), "value"])
    learn_val = float(params_df.loc[(skill_name, "learns", "default"), "value"])
    guess_val = float(params_df.loc[(skill_name, "guesses", "default"), "value"])
    slip_val = float(params_df.loc[(skill_name, "slips", "default"), "value"])
    forget_val = float(params_df.loc[(skill_name, "forgets", "default"), "value"])

    print("\nExtracted Parameter Values:")
    print(f"  prior (p_L0): {prior_val:.6f}")
    print(f"  learn (p_T):  {learn_val:.6f}")
    print(f"  guess (p_G):  {guess_val:.6f}")
    print(f"  slip (p_S):   {slip_val:.6f}")
    print(f"  forget:       {forget_val:.6f}")

    # Prepare fitted config YAML content with SYNTHETIC DATA provenance header
    fitted_config_dict = {
        "dataset_type": "SYNTHETIC_DATA",
        "description": "Fitted BKT parameters on synthetic student responses. NOT REAL LEARNER DATA.",
        "skill_name": skill_name,
        "fitted_parameters": {
            "p_S": slip_val,
            "p_G": guess_val,
            "p_T": learn_val,
            "prior": prior_val,
            "forget": forget_val,
        },
        "window_size": 4,
        "mastered_p": 0.85,
        "weak_p": 0.40,
        "sigma2_max": 0.05,
        "min_obs": 3,
        "kappa0": 2.0,
    }

    yaml_header = (
        "# ==============================================================================\n"
        "# PROVENANCE RECORD: SYNTHETIC DATA\n"
        "# Source: Fitted using pyBKT (v1.4.3) on synthetic response data\n"
        "# Data file: data/processed/synthetic_bkt_responses.csv\n"
        "# Model: Standard 4-parameter BKT (Corbett & Anderson 1995)\n"
        "# Split: Student-level split (train: student_01..09, heldout: student_10)\n"
        "# WARNING: Parameters estimated on synthetic simulation data. NOT REAL LEARNER DATA.\n"
        "# ==============================================================================\n"
    )

    with open(output_config_path, "w", encoding="utf-8") as f:
        f.write(yaml_header)
        yaml.dump(fitted_config_dict, f, default_flow_style=False, sort_keys=False)

    print(f"\nSaved fitted parameters with provenance to: {output_config_path}")

    # Predict on held-out student
    print("\nPredicting on held-out student...")
    preds_df = model.predict(data=test_df)

    # Print predicted probability of correct on held-out student's first three interactions
    first_three = preds_df.head(3)
    print("\nHeld-out student first three interactions:")
    for idx, row in first_three.reset_index(drop=True).iterrows():
        order = int(row["order_id"])
        obs = int(row["correct"])
        p_correct = float(row["correct_predictions"])
        p_state = float(row["state_predictions"])
        print(f"  Interaction {order} (obs={obs}): P(correct) = {p_correct:.6f}, Prior belief P(L) = {p_state:.6f}")


if __name__ == "__main__":
    main()
