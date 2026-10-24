import os
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union
import yaml


@dataclass(frozen=True)
class PolicyConfig:
    """
    Policy configuration for learner state estimation and classification.

    quorum is derived as:
    - 3 when window_size == 4
    - ceil(0.75 * window_size) for other window sizes.
    """
    p_S: float = 0.10
    p_G: float = 0.25
    p_T: float = 0.10
    window_size: int = 4
    mastered_p: float = 0.85
    weak_p: float = 0.40
    sigma2_max: float = 0.05
    min_obs: int = 3
    kappa0: float = 2.0
    defaulted_fields: Tuple[str, ...] = ()
    quorum: int = field(init=False)

    def __post_init__(self):
        # Ensure defaulted_fields is a tuple
        if not isinstance(self.defaulted_fields, tuple):
            object.__setattr__(self, "defaulted_fields", tuple(self.defaulted_fields))

        # Validate probabilities: finite and in [0, 1]
        for name in ("p_S", "p_G", "p_T", "mastered_p", "weak_p"):
            val = getattr(self, name)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ValueError(f"Field '{name}' must be a finite probability in [0, 1], got {val}")

        # Validate window_size: positive integer
        if not isinstance(self.window_size, int) or isinstance(self.window_size, bool) or self.window_size <= 0:
            raise ValueError(f"Field 'window_size' must be a positive integer, got {self.window_size}")

        # Validate min_obs: non-negative integer
        if not isinstance(self.min_obs, int) or isinstance(self.min_obs, bool) or self.min_obs < 0:
            raise ValueError(f"Field 'min_obs' must be a non-negative integer, got {self.min_obs}")

        # Validate sigma2_max: non-negative finite float
        if not isinstance(self.sigma2_max, (int, float)) or isinstance(self.sigma2_max, bool) or not math.isfinite(self.sigma2_max) or self.sigma2_max < 0:
            raise ValueError(f"Field 'sigma2_max' must be a finite non-negative float, got {self.sigma2_max}")

        # Validate mastered_p > weak_p
        if self.mastered_p <= self.weak_p:
            raise ValueError(f"Field 'mastered_p' ({self.mastered_p}) must be strictly greater than 'weak_p' ({self.weak_p})")

        # Validate kappa0: positive finite float
        if not isinstance(self.kappa0, (int, float)) or isinstance(self.kappa0, bool) or not math.isfinite(self.kappa0) or self.kappa0 <= 0:
            raise ValueError(f"Field 'kappa0' must be a positive finite float, got {self.kappa0}")

        # Derive quorum
        q = 3 if self.window_size == 4 else math.ceil(0.75 * self.window_size)
        object.__setattr__(self, "quorum", q)


class DefaultPolicyResult(tuple):
    """A 2-tuple (PolicyConfig, List[str]) that provides .policy and .warnings attributes."""
    @property
    def policy(self) -> PolicyConfig:
        return self[0]

    @property
    def warnings(self) -> List[str]:
        return self[1]


REQUIRED_POLICY_KEYS = {"p_S", "p_G", "p_T", "window_size"}
OPTIONAL_POLICY_FIELDS = {
    "mastered_p": 0.85,
    "weak_p": 0.40,
    "sigma2_max": 0.05,
    "min_obs": 3,
    "kappa0": 2.0,
}
ALLOWED_POLICY_KEYS = REQUIRED_POLICY_KEYS | set(OPTIONAL_POLICY_FIELDS.keys())


def validate_policy_dict(data: Any) -> Tuple[Dict[str, Any], Tuple[str, ...]]:
    """
    Validates a dictionary against the strict PolicyConfig schema.
    Returns (cleaned_dict, defaulted_fields).
    Raises ValueError with descriptive messages for missing or unknown keys.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Policy YAML must contain a mapping/dictionary, got {type(data)}")

    data_keys = set(data.keys())
    unknown_keys = sorted(data_keys - ALLOWED_POLICY_KEYS)
    missing_keys = sorted(REQUIRED_POLICY_KEYS - data_keys)

    errs = []
    if missing_keys:
        errs.append(f"Missing required key(s) in configuration: {', '.join(missing_keys)}")
    if unknown_keys:
        errs.append(f"Unknown key(s) in configuration: {', '.join(unknown_keys)}")
    if errs:
        raise ValueError(". ".join(errs))

    defaulted = []
    cleaned = dict(data)
    for opt_key, def_val in OPTIONAL_POLICY_FIELDS.items():
        if opt_key not in cleaned:
            cleaned[opt_key] = def_val
            defaulted.append(opt_key)

    return cleaned, tuple(defaulted)


def default_policy(log: Optional[Any] = None) -> DefaultPolicyResult:
    """
    Explicit opt-in function that returns declared default PolicyConfig
    and records a line in a returned warnings list.
    """
    msg = "Explicit opt-in fallback to declared default PolicyConfig."
    if isinstance(log, list):
        log.append(msg)
        warnings = log
    else:
        warnings = [msg]
    all_defaulted = ("p_S", "p_G", "p_T", "window_size") + tuple(OPTIONAL_POLICY_FIELDS.keys())
    return DefaultPolicyResult((PolicyConfig(defaulted_fields=all_defaulted), warnings))


def load_policy(path: str) -> PolicyConfig:
    """
    Reads YAML policy configuration and returns a validated PolicyConfig.
    Raises FileNotFoundError if the file is missing.
    Raises ValueError on malformed YAML or invalid configuration values.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Policy file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Malformed YAML in policy file: {e}") from e

    cleaned, defaulted = validate_policy_dict(data)
    return PolicyConfig(**cleaned, defaulted_fields=defaulted)

