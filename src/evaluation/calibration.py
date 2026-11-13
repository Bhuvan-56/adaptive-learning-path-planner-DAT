"""
Week 8: calibration of the engine's mastery estimate p against latent mastery (M8).

Pure functions on numbers. The latent flags are read by the evaluation harness through
the simulator's EvaluatorView at the end of the horizon; this module never sees the
simulator, and nothing under src/planning, src/state or src/diagnostic imports it.

- Brier score: mean over items of (p - y)^2, y in {0, 1}.
- Reliability table: 10 equal-width bins on p in [0, 1] (p = 1.0 goes to the last bin);
  per bin the count, mean p and fraction latently mastered.
- ECE: sum over bins of (n_b / N) * |mean p_b - fraction mastered_b|.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# per_learner.csv value for arms that do not maintain p (W8 task 4)
NOT_APPLICABLE = "not applicable"


def brier_score(p: Sequence[float], y: Sequence[int]) -> float:
    p_arr = np.asarray(p, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if p_arr.shape != y_arr.shape:
        raise ValueError(f"p and y differ in length: {p_arr.shape} vs {y_arr.shape}")
    if p_arr.size == 0:
        return float("nan")
    return float(np.mean((p_arr - y_arr) ** 2))


def _bin_index(p: float, n_bins: int) -> int:
    return min(int(math.floor(p * n_bins)), n_bins - 1)


def reliability_table(p: Sequence[float], y: Sequence[int], n_bins: int = 10) -> List[Dict[str, Any]]:
    p_arr = np.asarray(p, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if p_arr.shape != y_arr.shape:
        raise ValueError(f"p and y differ in length: {p_arr.shape} vs {y_arr.shape}")
    idx = np.array([_bin_index(v, n_bins) for v in p_arr], dtype=int)
    table = []
    for b in range(n_bins):
        mask = idx == b
        n = int(mask.sum())
        table.append({
            "bin": b,
            "lo": b / n_bins,
            "hi": (b + 1) / n_bins,
            "count": n,
            "mean_p": float(p_arr[mask].mean()) if n else None,
            "frac_mastered": float(y_arr[mask].mean()) if n else None,
        })
    return table


def expected_calibration_error(p: Sequence[float], y: Sequence[int], n_bins: int = 10) -> float:
    table = reliability_table(p, y, n_bins)
    total = sum(b["count"] for b in table)
    if total == 0:
        return float("nan")
    return float(sum(b["count"] / total * abs(b["mean_p"] - b["frac_mastered"]) for b in table if b["count"]))


def encode_pairs(pairs: Sequence[Tuple[str, float, int]]) -> str:
    """'concept:p:y;...' with p at 12 significant digits (per_learner.csv column)."""
    return ";".join(f"{c}:{float(p):.12g}:{int(y)}" for c, p, y in pairs)


def decode_pairs(s: Any) -> List[Tuple[str, float, int]]:
    if s is None or (isinstance(s, float) and math.isnan(s)) or str(s) in ("", NOT_APPLICABLE):
        return []
    out = []
    for part in str(s).split(";"):
        c, p, y = part.rsplit(":", 2)
        out.append((c, float(p), int(y)))
    return out


def calibration_markdown(
    arm_pairs: Dict[str, Optional[List[Tuple[str, float, int]]]],
    arm_briers: Dict[str, Optional[Sequence[float]]],
    ci_fn,
    n_bins: int = 10,
    heading: str = "## 6. Mastery calibration (end of horizon)",
) -> List[str]:
    """Markdown lines: per-arm Brier [95% CI] and ECE, then one reliability table per arm.

    arm_pairs[arm] / arm_briers[arm] are None for arms that do not maintain p.
    ci_fn(values) -> (mean, lo, hi).
    """
    lines = [
        heading,
        "",
        "Engine estimate p per concept at the end of the horizon against the simulator's latent "
        "mastery (read by the evaluator only). Brier: per-learner mean over concepts, then mean over "
        f"learners with a 95% bootstrap CI. ECE and the reliability table pool all learner × concept "
        f"pairs, {n_bins} equal-width bins on p. Arms that never update p after the diagnostic "
        "(static plan, greedy) are not applicable.",
        "",
        "| Arm | Mastery Brier [95% CI] | ECE | Pairs |",
        "|---|---|---|---|",
    ]
    for arm, pairs in arm_pairs.items():
        if pairs is None:
            lines.append(f"| {arm} | not applicable | not applicable | – |")
            continue
        m, lo, hi = ci_fn(list(arm_briers[arm]))
        ece = expected_calibration_error([q for _, q, _ in pairs], [v for _, _, v in pairs], n_bins)
        lines.append(f"| {arm} | {m:.4f} [{lo:.4f}, {hi:.4f}] | {ece:.4f} | {len(pairs)} |")
    for arm, pairs in arm_pairs.items():
        if pairs is None:
            continue
        lines += ["", f"Reliability, {arm}:", "", "| p bin | Pairs | Mean p | Fraction mastered |", "|---|---|---|---|"]
        for b in reliability_table([q for _, q, _ in pairs], [v for _, _, v in pairs], n_bins):
            mp = "–" if b["mean_p"] is None else f"{b['mean_p']:.4f}"
            fm = "–" if b["frac_mastered"] is None else f"{b['frac_mastered']:.4f}"
            lines.append(f"| {b['lo']:.1f}–{b['hi']:.1f} | {b['count']} | {mp} | {fm} |")
    lines.append("")
    return lines
