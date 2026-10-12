import os
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
import yaml

from src.state.policy import PolicyConfig, load_policy, default_policy

DEFAULT_BKT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "bkt_params.yaml")
DEFAULT_PROFILES_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "profiles.yaml")


def load_bkt_params(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads default BKT update parameters and evidence window size from config YAML via load_policy."""
    path = config_path or DEFAULT_BKT_CONFIG_PATH
    policy = load_policy(path)
    return {
        "p_S": policy.p_S,
        "p_G": policy.p_G,
        "p_T": policy.p_T,
        "window_size": policy.window_size,
    }


WINDOW_SIZE: int = 4


@dataclass
class ConceptState:
    """
    Represents the learner's cognitive state for a single concept using a Beta-distributed belief proxy.

    sigma2 remains an uncalibrated HEURISTIC EVIDENCE-COUNT CONFIDENCE PROXY.
    The window gate is a heuristic guard against confident classification under contradictory evidence.
    """
    A: float = 1.0
    B: float = 1.0
    p: float = field(init=False)
    kappa: float = field(init=False)
    n: int = 0
    history: List[int] = field(default_factory=list)
    policy: Optional[PolicyConfig] = None

    def __post_init__(self):
        self._recompute_p_kappa()
        # Input validation
        if not isinstance(self.p, (int, float)) or not math.isfinite(self.p) or not (0.0 <= self.p <= 1.0):
            raise ValueError(f"p must be a finite float in [0, 1], got {self.p}")
        if not isinstance(self.kappa, (int, float)) or not math.isfinite(self.kappa) or self.kappa <= 0:
            raise ValueError(f"kappa must be a positive finite float, got {self.kappa}")
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n < 0:
            raise ValueError(f"n must be a non-negative integer, got {self.n}")

        cleaned_history = []
        for h in self.history:
            if h not in (0, 1) or isinstance(h, bool):
                raise ValueError(f"history entries must be 0 or 1, got {h}")
            cleaned_history.append(int(h))
        self.history = cleaned_history

        active_window = self.policy.window_size if self.policy is not None else 4
        if len(self.history) > active_window:
            raise ValueError(f"history length ({len(self.history)}) exceeds window_size ({active_window})")

    def _recompute_p_kappa(self):
        self.kappa = float(self.A + self.B)
        if self.kappa > 0:
            self.p = float(self.A / self.kappa)
        else:
            self.p = 0.5

    @property
    def sigma2(self) -> float:
        """Derived variance: p*(1-p)/(kappa + 1)."""
        if self.kappa <= 0:
            return 0.0
        return (self.p * (1.0 - self.p)) / (self.kappa + 1.0)

    @classmethod
    def cold_start(cls) -> "ConceptState":
        """Creates a cold-start state: A=1, B=1 (p=0.5, kappa=2, sigma2=1/12≈0.0833, n=0, history=[])."""
        return cls(A=1.0, B=1.0, n=0, history=[])

    @classmethod
    def init_from_ability(cls, p0: float) -> "ConceptState":
        """Creates an unprobed concept state with prior ability p0, kappa=2, n=0, history=[]."""
        p0 = max(0.001, min(0.999, p0))
        A = p0 * 2.0
        B = (1.0 - p0) * 2.0
        return cls(A=A, B=B, n=0, history=[])

    def update(
        self,
        correct: Union[bool, int],
        policy: Optional[PolicyConfig] = None,
        params: Optional[Any] = None
    ) -> "ConceptState":
        """
        Updates concept mastery state via Bayesian Knowledge Tracing (BKT) posterior update
        followed by a learning transition, incrementing kappa and n, and tracking recent history.
        """
        if correct not in (0, 1, True, False) or (isinstance(correct, float) and math.isnan(correct)):
            raise ValueError(f"Outcome must be 0 or 1 (or boolean), got {correct}")

        active_policy: PolicyConfig
        if policy is not None:
            if isinstance(policy, tuple) and hasattr(policy, "policy"):
                active_policy = policy.policy
            else:
                active_policy = policy
            self.policy = active_policy
        elif self.policy is not None:
            active_policy = self.policy
        elif params is not None:
            if isinstance(params, PolicyConfig):
                active_policy = params
            elif isinstance(params, dict):
                allowed = {"p_S", "p_G", "p_T", "window_size", "mastered_p", "weak_p", "sigma2_max", "min_obs", "kappa0"}
                filtered = {k: v for k, v in params.items() if k in allowed}
                active_policy = PolicyConfig(**filtered)
            else:
                active_policy = PolicyConfig()
            self.policy = active_policy
        else:
            active_policy = PolicyConfig()
            self.policy = active_policy

        window_size = active_policy.window_size
        outcome_val = 1 if (correct is True or correct == 1) else 0
        self.history.append(outcome_val)
        if len(self.history) > window_size:
            self.history = self.history[-window_size:]

        p_S = active_policy.p_S
        p_G = active_policy.p_G
        p_T = active_policy.p_T

        current_p = self.p

        if outcome_val == 1:
            denom = current_p * (1.0 - p_S) + (1.0 - current_p) * p_G
            p_obs = (current_p * (1.0 - p_S)) / denom if denom > 0 else current_p
        else:
            denom = current_p * p_S + (1.0 - current_p) * (1.0 - p_G)
            p_obs = (current_p * p_S) / denom if denom > 0 else current_p

        # Learning transition
        new_p = p_obs + (1.0 - p_obs) * p_T
        new_p = max(0.0001, min(0.9999, new_p))

        self.n += 1
        self.kappa += 1.0
        self.A = new_p * self.kappa
        self.B = (1.0 - new_p) * self.kappa
        self.p = new_p
        return self

    def classify(self, policy: Optional[PolicyConfig] = None) -> str:
        """
        Classifies state into one of four mutually exclusive states with strict precedence order:
        1. Uncertain: if sigma2 > sigma2_max OR n < min_obs (top precedence)
        2. Mastered: if p >= mastered_p AND sigma2 <= sigma2_max AND n >= min_obs AND (last window has >= quorum correct)
        3. Weak: if p < weak_p (STRICT) AND sigma2 <= sigma2_max AND n >= min_obs AND (last window has >= quorum incorrect)
        4. Developing: all remaining cases
        """
        active_policy: PolicyConfig
        if policy is not None:
            if isinstance(policy, tuple) and hasattr(policy, "policy"):
                active_policy = policy.policy
            else:
                active_policy = policy
        elif self.policy is not None:
            active_policy = self.policy
        else:
            active_policy = PolicyConfig()

        if self.sigma2 > active_policy.sigma2_max or self.n < active_policy.min_obs:
            return "Uncertain"

        window_full = len(self.history) >= active_policy.window_size
        correct_count = sum(self.history) if window_full else 0
        incorrect_count = (active_policy.window_size - correct_count) if window_full else 0

        mastered_gate = window_full and (correct_count >= active_policy.quorum)
        weak_gate = window_full and (incorrect_count >= active_policy.quorum)

        if self.p >= active_policy.mastered_p and self.sigma2 <= active_policy.sigma2_max and self.n >= active_policy.min_obs and mastered_gate:
            return "Mastered"

        if self.p < active_policy.weak_p and self.sigma2 <= active_policy.sigma2_max and self.n >= active_policy.min_obs and weak_gate:
            return "Weak"

        return "Developing"

    def validate(self) -> bool:
        """Validates that variance satisfies theoretical Beta distribution bounds: 0 <= sigma2 <= p*(1-p)."""
        max_possible_var = self.p * (1.0 - self.p)
        return 0.0 <= self.sigma2 <= (max_possible_var + 1e-9)


def load_profiles(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads profiles from YAML and validates every concept state.
    Calls ConceptState.validate() on every profile load.
    """
    file_path = path or DEFAULT_PROFILES_CONFIG_PATH
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Profiles config file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Profiles YAML must contain a dictionary, got {type(data)}")

    profiles = data.get("profiles", {})
    for prof_id, prof in profiles.items():
        init_states = prof.get("initial_states", {})
        for group, params in init_states.items():
            p = params["p"]
            kappa = params["kappa"]
            n = params.get("n", 0)
            A = p * kappa
            B = (1.0 - p) * kappa
            state = ConceptState(A=A, B=B, n=n)
            if not state.validate():
                raise ValueError(f"Invalid state for profile {prof_id}, group {group}")

    return data
