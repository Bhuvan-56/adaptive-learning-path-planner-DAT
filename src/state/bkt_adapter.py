"""
Online Bayesian Knowledge Tracing (BKT) Adapter.

This module provides an online adapter wrapping the project's per-interaction BKT
update semantics and accepting fitted parameters from configuration YAML files,
such as config/bkt_fitted.yaml.

FORGETTING PARAMETER SPECIFICATION:
-----------------------------------
In this adapter and the underlying cognitive state model, the forget rate is
strictly zero (forget = 0.0, P(F) = 0.0). Standard 4-parameter BKT (Corbett &
Anderson 1995) and the project's mastery tracking policy model monotonic skill
acquisition during active learning practice. In particular, once a learner has
acquired a skill transition, they are assumed not to unlearn it within the scope
of immediate curriculum sequences. pyBKT fits standard BKT with forget=0.0 by
default, matching this project's formulation.
"""

import os
import math
from typing import Dict, Any, Optional, Union, Tuple
import yaml

from src.state.policy import PolicyConfig, load_policy, OPTIONAL_POLICY_FIELDS, ALLOWED_POLICY_KEYS
from src.state.learner_state import ConceptState


DEFAULT_FITTED_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "bkt_fitted.yaml")
)

ALLOWED_FITTED_METADATA_KEYS = {"dataset_type", "description", "skill_name"}
REQUIRED_FITTED_PARAMS = {"p_S", "p_G", "p_T", "prior", "forget"}
ALLOWED_FITTED_TOP_LEVEL = ALLOWED_FITTED_METADATA_KEYS | {"fitted_parameters"} | ALLOWED_POLICY_KEYS


def load_fitted_bkt_params(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads fitted BKT parameters from a YAML file (e.g. config/bkt_fitted.yaml).

    Returns a dictionary containing:
      - p_S: Slip rate
      - p_G: Guess rate
      - p_T: Learning / transition rate
      - prior: Initial mastery probability
      - forget: Forget rate (strictly 0.0)
      - window_size, mastered_p, weak_p, sigma2_max, min_obs, kappa0
      - skill_name
      - defaulted_fields
    """
    path = config_path or DEFAULT_FITTED_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fitted BKT configuration file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Malformed YAML in fitted BKT configuration file: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Fitted BKT configuration must be a mapping, got {type(data)}")

    data_keys = set(data.keys())
    unknown_top = sorted(data_keys - ALLOWED_FITTED_TOP_LEVEL)
    if unknown_top:
        raise ValueError(f"Unknown key(s) in configuration: {', '.join(unknown_top)}")

    if "fitted_parameters" not in data:
        raise ValueError("Missing required key(s) in configuration: fitted_parameters")

    params_dict = data["fitted_parameters"]
    if not isinstance(params_dict, dict):
        raise ValueError(f"'fitted_parameters' must be a mapping, got {type(params_dict)}")

    fitted_keys = set(params_dict.keys())
    unknown_nested = sorted(fitted_keys - REQUIRED_FITTED_PARAMS)
    missing_nested = sorted(REQUIRED_FITTED_PARAMS - fitted_keys)

    errs = []
    if missing_nested:
        errs.append(f"Missing required key(s) in configuration: {', '.join(missing_nested)}")
    if unknown_nested:
        errs.append(f"Unknown key(s) in configuration: {', '.join(unknown_nested)}")
    if errs:
        raise ValueError(". ".join(errs))

    forget_val = float(params_dict["forget"])
    if forget_val != 0.0:
        raise ValueError(
            f"Standard BKT requires forget == 0.0 (got {forget_val}). "
            "Non-zero forgetting is not supported by the online state engine."
        )

    defaulted_fields = []
    window_size = data.get("window_size", 4)
    if "window_size" not in data:
        defaulted_fields.append("window_size")

    mastered_p = data.get("mastered_p", OPTIONAL_POLICY_FIELDS["mastered_p"])
    if "mastered_p" not in data:
        defaulted_fields.append("mastered_p")

    weak_p = data.get("weak_p", OPTIONAL_POLICY_FIELDS["weak_p"])
    if "weak_p" not in data:
        defaulted_fields.append("weak_p")

    sigma2_max = data.get("sigma2_max", OPTIONAL_POLICY_FIELDS["sigma2_max"])
    if "sigma2_max" not in data:
        defaulted_fields.append("sigma2_max")

    min_obs = data.get("min_obs", OPTIONAL_POLICY_FIELDS["min_obs"])
    if "min_obs" not in data:
        defaulted_fields.append("min_obs")

    kappa0 = data.get("kappa0", OPTIONAL_POLICY_FIELDS["kappa0"])
    if "kappa0" not in data:
        defaulted_fields.append("kappa0")

    return {
        "p_S": float(params_dict["p_S"]),
        "p_G": float(params_dict["p_G"]),
        "p_T": float(params_dict["p_T"]),
        "prior": float(params_dict["prior"]),
        "forget": forget_val,
        "window_size": int(window_size),
        "mastered_p": float(mastered_p),
        "weak_p": float(weak_p),
        "sigma2_max": float(sigma2_max),
        "min_obs": int(min_obs),
        "kappa0": float(kappa0),
        "skill_name": data.get("skill_name", "default"),
        "defaulted_fields": defaulted_fields,
    }



class BKTOnlineAdapter:
    """
    Online BKT adapter executing exact sequential updates.

    Attributes:
        p_S (float): Slip probability P(incorrect | mastered)
        p_G (float): Guess probability P(correct | unmastered)
        p_T (float): Transition / learning probability P(L_{t+1} | not L_t)
        p (float): Current belief of mastery P(L_t)
        forget (float): Strictly 0.0 in standard BKT
        history (list): Sequence of recorded outcomes (0 or 1)
    """

    def __init__(
        self,
        p_S: float,
        p_G: float,
        p_T: float,
        prior: float = 0.5,
        forget: float = 0.0,
        policy: Optional[PolicyConfig] = None,
    ):
        if not (0.0 <= p_S <= 1.0):
            raise ValueError(f"p_S must be in [0, 1], got {p_S}")
        if not (0.0 <= p_G <= 1.0):
            raise ValueError(f"p_G must be in [0, 1], got {p_G}")
        if not (0.0 <= p_T <= 1.0):
            raise ValueError(f"p_T must be in [0, 1], got {p_T}")
        if not (0.0 <= prior <= 1.0):
            raise ValueError(f"prior must be in [0, 1], got {prior}")
        if forget != 0.0:
            raise ValueError(
                f"Standard BKT requires forget == 0.0 (got {forget}). "
                "Non-zero forgetting is not supported by the online state engine."
            )

        self.p_S = float(p_S)
        self.p_G = float(p_G)
        self.p_T = float(p_T)
        self.prior = float(prior)
        self.forget = 0.0
        self.p = float(prior)
        self.history = []
        self.policy = policy or PolicyConfig(
            p_S=self.p_S,
            p_G=self.p_G,
            p_T=self.p_T,
        )

    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> "BKTOnlineAdapter":
        """Factory constructor instantiating adapter from a YAML config file."""
        params = load_fitted_bkt_params(config_path)
        policy = PolicyConfig(
            p_S=params["p_S"],
            p_G=params["p_G"],
            p_T=params["p_T"],
            window_size=params["window_size"],
            mastered_p=params["mastered_p"],
            weak_p=params["weak_p"],
            sigma2_max=params["sigma2_max"],
            min_obs=params["min_obs"],
            kappa0=params["kappa0"],
        )
        return cls(
            p_S=params["p_S"],
            p_G=params["p_G"],
            p_T=params["p_T"],
            prior=params["prior"],
            forget=params["forget"],
            policy=policy,
        )

    def predict_correct_probability(self) -> float:
        """
        Computes predicted probability of a correct response given current mastery belief:
            P(correct) = P(L) * (1 - p_S) + (1 - P(L)) * p_G
        """
        return self.p * (1.0 - self.p_S) + (1.0 - self.p) * self.p_G

    def update(self, correct: Union[int, bool]) -> float:
        """
        Applies online BKT update for an observed response.

        Step 1: Posterior update given evidence
            P(L | obs=1) = (P(L) * (1 - p_S)) / P(correct)
            P(L | obs=0) = (P(L) * p_S) / P(incorrect)
        Step 2: Learning transition
            P(L_{t+1}) = P(L | obs) + (1 - P(L | obs)) * p_T

        Returns the new posterior mastery belief P(L_{t+1}).
        """
        outcome_val = 1 if (correct is True or correct == 1) else 0
        self.history.append(outcome_val)

        p = self.p
        if outcome_val == 1:
            denom = p * (1.0 - self.p_S) + (1.0 - p) * self.p_G
            p_obs = (p * (1.0 - self.p_S)) / denom if denom > 0.0 else p
        else:
            denom = p * self.p_S + (1.0 - p) * (1.0 - self.p_G)
            p_obs = (p * self.p_S) / denom if denom > 0.0 else p

        # Learning transition (forget is 0.0)
        new_p = p_obs + (1.0 - p_obs) * self.p_T
        self.p = new_p
        return self.p

    def step(self, correct: Union[int, bool]) -> Tuple[float, float]:
        """
        Executes a full step: returns (P(correct entering trial), P(mastery posterior after trial)).
        """
        p_correct = self.predict_correct_probability()
        posterior = self.update(correct)
        return p_correct, posterior

    def to_concept_state(self) -> ConceptState:
        """
        Constructs a ConceptState representing current state with weight kappa0.
        """
        kappa0 = self.policy.kappa0
        A = self.p * kappa0
        B = (1.0 - self.p) * kappa0
        cs = ConceptState(A=A, B=B, policy=self.policy)
        cs.history = list(self.history[-self.policy.window_size:])
        cs.n = len(self.history)
        return cs
