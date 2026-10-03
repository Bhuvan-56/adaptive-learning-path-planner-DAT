import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import yaml

DEFAULT_BKT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "bkt_params.yaml")


def load_bkt_params(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads default BKT update parameters and evidence window size from config YAML."""
    path = config_path or DEFAULT_BKT_CONFIG_PATH
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return {
                        "p_S": data.get("p_S", 0.10),
                        "p_G": data.get("p_G", 0.25),
                        "p_T": data.get("p_T", 0.10),
                        "window_size": data.get("window_size", 4)
                    }
        except Exception:
            pass
    return {"p_S": 0.10, "p_G": 0.25, "p_T": 0.10, "window_size": 4}


WINDOW_SIZE: int = load_bkt_params().get("window_size", 4)


@dataclass
class ConceptState:
    """
    Represents the learner's cognitive state for a single concept using a Beta-distributed belief proxy.

    sigma2 remains an uncalibrated HEURISTIC EVIDENCE-COUNT CONFIDENCE PROXY.
    The W=4 window gate is a heuristic guard against confident classification under contradictory evidence, also not calibrated.
    The earlier learn=0.0 setting was a workaround that has been removed.
    """
    A: float = 1.0
    B: float = 1.0
    p: float = field(init=False)
    kappa: float = field(init=False)
    n: int = 0
    history: List[int] = field(default_factory=list)

    def __post_init__(self):
        self._recompute_p_kappa()

    def _recompute_p_kappa(self):
        self.kappa = self.A + self.B
        if self.kappa > 0:
            self.p = self.A / self.kappa
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

    def update(self, correct: bool, params: Optional[Dict[str, Any]] = None) -> "ConceptState":
        """
        Updates concept mastery state via Bayesian Knowledge Tracing (BKT) posterior update
        followed by a learning transition, incrementing kappa and n, and tracking recent history.
        """
        outcome_val = 1 if correct else 0
        self.history.append(outcome_val)
        if len(self.history) > WINDOW_SIZE:
            self.history = self.history[-WINDOW_SIZE:]

        if params is None:
            params = load_bkt_params()

        p_S = params.get("p_S", 0.10)  # Slip
        p_G = params.get("p_G", 0.25)  # Guess
        p_T = params.get("p_T", 0.10)  # Transition / learning rate

        current_p = self.p

        if correct:
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

    def classify(self) -> str:
        """
        Classifies state into one of four mutually exclusive states with strict precedence order:
        1. Uncertain: if sigma2 > 0.05 OR n < 3 (top precedence)
        2. Mastered: if p >= 0.85 AND sigma2 <= 0.05 AND n >= 3 AND (last 4 window has >= 3 correct)
        3. Weak: if p < 0.40 (STRICT) AND sigma2 <= 0.05 AND n >= 3 AND (last 4 window has >= 3 incorrect)
        4. Developing: all remaining cases
        """
        if self.sigma2 > 0.05 or self.n < 3:
            return "Uncertain"

        window_full = len(self.history) >= WINDOW_SIZE
        correct_count = sum(self.history) if window_full else 0
        incorrect_count = (WINDOW_SIZE - correct_count) if window_full else 0

        mastered_gate = window_full and (correct_count >= 3)
        weak_gate = window_full and (incorrect_count >= 3)

        if self.p >= 0.85 and self.sigma2 <= 0.05 and self.n >= 3 and mastered_gate:
            return "Mastered"

        if self.p < 0.40 and self.sigma2 <= 0.05 and self.n >= 3 and weak_gate:
            return "Weak"

        return "Developing"

    def validate(self) -> bool:
        """Validates that variance satisfies theoretical Beta distribution bounds: 0 <= sigma2 <= p*(1-p)."""
        max_possible_var = self.p * (1.0 - self.p)
        return 0.0 <= self.sigma2 <= (max_possible_var + 1e-9)
