import os
import glob
import pytest
import yaml


@pytest.mark.xfail(
    strict=True,
    reason="Defect 10: config/ and evaluation/config/ define conflicting BKT parameter values across YAML files",
)
def test_defect_10_no_conflicting_bkt_keys_across_configs():
    """Defect 10: Scanning config/ and evaluation/config/ must not find conflicting BKT parameters."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_dirs = [
        os.path.join(repo_root, "config"),
        os.path.join(repo_root, "evaluation", "config"),
    ]

    bkt_params_found = {}

    def extract_bkt(data, filepath):
        if not isinstance(data, dict):
            return
        slip = data.get("p_S")
        guess = data.get("p_G")
        transit = data.get("p_T")

        if isinstance(data.get("bkt"), dict):
            slip = slip or data["bkt"].get("slip_p_S")
            guess = guess or data["bkt"].get("guess_p_G")
            transit = transit or data["bkt"].get("transit_p_T")

        if isinstance(data.get("model_hyperparameters"), dict):
            m = data["model_hyperparameters"]
            if isinstance(m.get("bkt"), dict):
                slip = slip or m["bkt"].get("slip_p_S")
                guess = guess or m["bkt"].get("guess_p_G")
                transit = transit or m["bkt"].get("transit_p_T")

        extracted = {}
        if slip is not None:
            extracted["slip"] = slip
        if guess is not None:
            extracted["guess"] = guess
        if transit is not None:
            extracted["transit"] = transit

        if extracted:
            bkt_params_found[filepath] = extracted

    for cdir in config_dirs:
        if os.path.exists(cdir):
            for ypath in glob.glob(os.path.join(cdir, "*.yaml")) + glob.glob(os.path.join(cdir, "*.yml")):
                with open(ypath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    extract_bkt(data, ypath)

    conflicts = []
    files = list(bkt_params_found.keys())
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            f1, f2 = files[i], files[j]
            p1, p2 = bkt_params_found[f1], bkt_params_found[f2]
            for k in set(p1.keys()).intersection(set(p2.keys())):
                if p1[k] != p2[k]:
                    conflicts.append(
                        f"Conflict on {k}: {os.path.basename(f1)} ({p1[k]}) vs {os.path.basename(f2)} ({p2[k]})"
                    )

    assert len(conflicts) == 0, f"Found BKT config conflicts: {conflicts}"
