"""
Transparent Learner Simulator for Policy Evaluation.

ARCHITECTURAL PRINCIPLE:
------------------------
A simulated learner encapsulates a latent cognitive mastery state for each concept.
This latent state is strictly private: only an EvaluatorView instance can read it.
Planning algorithms and state estimators (modules under `src/planning` and `src/state`)
receive only observable, scored exercise responses (0 or 1) via `SimulatedLearner.respond()`.
EvaluatorView must never be imported or referenced by planning or state code.

GENERATOR FAMILIES:
-------------------
1. MatchedBKTGenerator:
   Standard 4-parameter BKT response dynamics with latent binary mastery (L in {0, 1}),
   slip rate p_S, guess rate p_G, and learn transition probability p_T per attempt.
2. MismatchedPFAOrLogisticGenerator:
   Empty, documented interface for non-BKT generative models (Performance Factors Analysis
   or continuous logistic response function), scheduled for Week 5 (W5) implementation.
"""

from abc import ABC, abstractmethod
import os
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np
import yaml


DEFAULT_PROFILES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "profiles.yaml")
)


class EvaluatorView:
    """
    Evaluator-only interface exposing the simulated learner's latent cognitive state.

    CRITICAL BOUNDARY:
    This class must only be imported by evaluation suites (e.g. evaluation/ or tests/).
    It must NEVER be imported anywhere under src/planning or src/state.
    """

    def __init__(self, latent_states: Dict[str, bool], generator_family: Any):
        self._latent_states = latent_states
        self._generator_family = generator_family

    def get_latent_mastery(self, concept: str) -> bool:
        """Returns True if the concept is latently mastered, False otherwise."""
        return bool(self._latent_states.get(concept, False))

    def is_mastered(self, concept: str) -> bool:
        """Alias for get_latent_mastery."""
        return self.get_latent_mastery(concept)

    @property
    def latent_masteries(self) -> Dict[str, bool]:
        """Returns a copy of all concept latent mastery flags."""
        return dict(self._latent_states)

    def get_latent_state_summary(self) -> Dict[str, Any]:
        """Returns latent state metadata for evaluation audit."""
        return {
            "masteries": dict(self._latent_states),
            "generator_family": getattr(self._generator_family, "name", str(self._generator_family)),
            "generator_parameters": (
                self._generator_family.get_parameters()
                if hasattr(self._generator_family, "get_parameters")
                else {}
            ),
        }


class LearnerGeneratorFamily(ABC):
    """Abstract base class for simulated learner response generators."""

    @abstractmethod
    def generate_response(
        self,
        concept: str,
        difficulty: float,
        latent_mastery: bool,
        rng: np.random.Generator,
    ) -> Tuple[int, bool]:
        """
        Generates a scored response (0 or 1) and returns (score, next_latent_mastery).
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Returns parameter configuration dictionary."""
        pass


class MatchedBKTGenerator(LearnerGeneratorFamily):
    """
    Standard BKT-style matched response generator.

    Latent mastery is binary: L in {0, 1}.
    - If L = 1 (mastered):
        P(Y = 1 | L = 1) = 1 - p_S (correct)
        P(Y = 0 | L = 1) = p_S     (slip)
    - If L = 0 (unmastered):
        P(Y = 1 | L = 0) = p_G     (guess)
        P(Y = 0 | L = 0) = 1 - p_G (incorrect)
    - Transition / learning:
        On each attempt of a concept, if unmastered, the learner transitions to
        mastered (L = 1) with probability p_T.
    """

    def __init__(self, p_S: float = 0.10, p_G: float = 0.25, p_T: float = 0.10):
        if not (0.0 <= p_S <= 1.0):
            raise ValueError(f"p_S must be in [0, 1], got {p_S}")
        if not (0.0 <= p_G <= 1.0):
            raise ValueError(f"p_G must be in [0, 1], got {p_G}")
        if not (0.0 <= p_T <= 1.0):
            raise ValueError(f"p_T must be in [0, 1], got {p_T}")

        self.p_S = float(p_S)
        self.p_G = float(p_G)
        self.p_T = float(p_T)
        self.name = "MatchedBKTGenerator"

    def generate_response(
        self,
        concept: str,
        difficulty: float,
        latent_mastery: bool,
        rng: np.random.Generator,
    ) -> Tuple[int, bool]:
        """
        Simulates an attempt on a concept:
        1. Emits response according to slip / guess probabilities.
        2. Applies learning transition if currently unmastered.
        """
        if latent_mastery:
            # Mastered: slips with probability p_S
            score = 0 if (rng.random() < self.p_S) else 1
            next_state = True
        else:
            # Unmastered: guesses correctly with probability p_G
            score = 1 if (rng.random() < self.p_G) else 0
            # Learning opportunity on attempt
            next_state = bool(rng.random() < self.p_T)

        return score, next_state

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "family": self.name,
            "p_S": self.p_S,
            "p_G": self.p_G,
            "p_T": self.p_T,
        }


class MismatchedPFAOrLogisticGenerator(LearnerGeneratorFamily):
    """
    Empty, documented interface for mismatched response generation family.

    SCHEDULED IMPLEMENTATION: Week 5 (W5).
    In this family, response accuracy depends continuously on cumulative practice attempts,
    successes, failures, and item difficulties (e.g. Performance Factors Analysis or
    multidimensional logistic response function) rather than discrete 2-state BKT.
    """

    def __init__(self, **kwargs):
        self.name = "MismatchedPFAOrLogisticGenerator"
        self._kwargs = kwargs

    def generate_response(
        self,
        concept: str,
        difficulty: float,
        latent_mastery: bool,
        rng: np.random.Generator,
    ) -> Tuple[int, bool]:
        raise NotImplementedError(
            "Mismatched generator family (PFA/Logistic response model) is scheduled for "
            "Week 5 (W5) implementation."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "family": self.name,
            "status": "NOT_IMPLEMENTED_SCHEDULED_W5",
            "kwargs": self._kwargs,
        }


class SimulatedLearner:
    """
    Simulated learner for closed-loop evaluation of planning algorithms.

    Encapsulates latent cognitive state accessible solely via `evaluator_view()`.
    Planners interact strictly via `respond(concept, difficulty)`.
    """

    def __init__(
        self,
        profile_id: str = "profile_1",
        generator_family: Optional[LearnerGeneratorFamily] = None,
        seed: Optional[int] = None,
        budget_override: Optional[int] = None,
        initial_mastery: Optional[Dict[str, bool]] = None,
        config_path: Optional[str] = None,
    ):
        self.profile_id = profile_id
        self.seed = 42 if seed is None else int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.generator_family = generator_family or MatchedBKTGenerator()

        # Load profile configuration
        profiles_file = config_path or DEFAULT_PROFILES_PATH
        if not os.path.exists(profiles_file):
            raise FileNotFoundError(f"Profiles configuration file not found: {profiles_file}")

        with open(profiles_file, "r", encoding="utf-8") as f:
            profiles_data = yaml.safe_load(f)

        profiles_dict = profiles_data.get("profiles", {})
        if profile_id not in profiles_dict:
            raise ValueError(f"Profile '{profile_id}' not found in {profiles_file}")

        profile_conf = profiles_dict[profile_id]

        # Daily budget: profile default or explicit demo override
        default_budget = int(profile_conf.get("daily_budget_minutes", 10))
        self.budget = int(budget_override) if budget_override is not None else default_budget
        self.budget_override = budget_override

        # Initialize latent mastery dictionary
        self._latent_states: Dict[str, bool] = {}
        if initial_mastery is not None:
            self._latent_states = {k: bool(v) for k, v in initial_mastery.items()}
        else:
            # Initialize from profile's initial_states
            init_states = profile_conf.get("initial_states", {})
            for group, params in init_states.items():
                p_init = float(params.get("p", 0.5))
                # Sample latent state from Bernoulli(p_init)
                self._latent_states[group] = bool(self.rng.random() < p_init)

    def get_budget(self) -> int:
        """Returns the active daily time budget in minutes."""
        return self.budget

    def respond(self, concept: str, difficulty: float = 0.5) -> int:
        """
        Generates an observable response (0 or 1) for the requested concept.

        Updates the underlying latent state according to the active generator family.
        The caller (planner) receives ONLY the scored integer result.
        """
        current_state = self._latent_states.get(concept, False)
        score, next_state = self.generator_family.generate_response(
            concept=concept,
            difficulty=difficulty,
            latent_mastery=current_state,
            rng=self.rng,
        )
        self._latent_states[concept] = next_state
        return int(score)

    def evaluator_view(self) -> EvaluatorView:
        """
        Returns an EvaluatorView allowing evaluators to inspect true latent mastery.
        Must never be passed to planning or state components.
        """
        return EvaluatorView(self._latent_states, self.generator_family)

    def get_manifest_record(self) -> Dict[str, Any]:
        """Returns structured metadata for provenance recording."""
        return {
            "profile_id": self.profile_id,
            "seed": self.seed,
            "budget": self.budget,
            "budget_override": self.budget_override,
            "generator_family": self.generator_family.name,
            "generator_parameters": self.generator_family.get_parameters(),
            "latent_mastery_snapshot": self.evaluator_view().latent_masteries,
        }
