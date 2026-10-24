"""
Module for dynamic difficulty adaptation (Module M4 / 2-Up 1-Down staircase).

MatchedBKTGenerator ignores difficulty, so a difficulty step changes the recorded
and requested difficulty but not the simulated response.
"""

from dataclasses import dataclass
import math
import os
from typing import Dict, Any, Optional, Union
import yaml

from src.curriculum.graph import MIN_DIFFICULTY, MAX_DIFFICULTY


DEFAULT_CONFIG_PATH = "config/adaptive.yaml"


def load_adaptive_config(path: Optional[str] = None) -> Dict[str, float]:
    """
    Strict loader for adaptive configuration (config/adaptive.yaml).

    Enforces:
    - Path must exist (raises FileNotFoundError).
    - Content must be a YAML dictionary mapping.
    - Required key 'step' must be present (missing key raises KeyError or ValueError).
    - Unknown keys are disallowed (raises ValueError).
    - Value of 'step' must be a finite numerical value with 0.0 < step <= 0.9.
    """
    cfg_path = path if path is not None else DEFAULT_CONFIG_PATH
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"Adaptive config file not found: {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Adaptive config at {cfg_path} must be a dictionary mapping.")

    allowed_keys = {"step"}
    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        raise ValueError(f"Unknown key(s) in adaptive configuration: {sorted(list(unknown_keys))}")

    if "step" not in data:
        raise KeyError("Missing required key 'step' in adaptive configuration.")

    step = data["step"]
    if isinstance(step, bool) or not isinstance(step, (int, float)) or not math.isfinite(step):
        raise ValueError(f"Adaptive step must be a finite number, got {step!r}")

    step_val = float(step)
    if not (0.0 < step_val <= 0.9):
        raise ValueError(f"Adaptive step must be in (0, 0.9], got {step_val}")

    return {"step": step_val}


def get_step_size(path: Optional[str] = None) -> float:
    """Convenience helper returning the scalar step size from config."""
    return load_adaptive_config(path)["step"]


@dataclass
class DifficultyState:
    """
    State tracking exercise difficulty and consecutive successes for a concept.
    """
    difficulty: float = 0.5
    consecutive_successes: int = 0

    def __post_init__(self):
        self.difficulty = round(min(MAX_DIFFICULTY, max(MIN_DIFFICULTY, float(self.difficulty))), 4)
        self.consecutive_successes = max(0, int(self.consecutive_successes))


def step_difficulty(
    state: DifficultyState,
    correct: Union[bool, int],
    step_size: Optional[float] = None,
    config_path: Optional[str] = None,
) -> DifficultyState:
    """
    Pure 2-Up / 1-Down difficulty stepping function.

    - Single failure (correct=False/0): decreases difficulty by step_size (floored at MIN_DIFFICULTY 0.05),
      and resets consecutive successes counter to 0.
    - Two consecutive successes (correct=True/1): increases difficulty by step_size (capped at MAX_DIFFICULTY 0.95),
      and resets consecutive successes counter to 0.
    - Single success: increments consecutive successes counter; difficulty remains unchanged.

    Returns a new DifficultyState without mutating the input state.
    """
    if step_size is None:
        step_size = get_step_size(config_path)

    is_correct = bool(correct)

    if not is_correct:
        new_diff = round(max(MIN_DIFFICULTY, state.difficulty - step_size), 4)
        return DifficultyState(difficulty=new_diff, consecutive_successes=0)
    else:
        new_streak = state.consecutive_successes + 1
        if new_streak >= 2:
            new_diff = round(min(MAX_DIFFICULTY, state.difficulty + step_size), 4)
            return DifficultyState(difficulty=new_diff, consecutive_successes=0)
        else:
            return DifficultyState(difficulty=state.difficulty, consecutive_successes=new_streak)
