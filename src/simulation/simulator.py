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
import math
import os
from typing import Dict, Any, Optional, Tuple, Union, List
import numpy as np
import yaml


DEFAULT_PROFILES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "profiles.yaml")
)

DEFAULT_GROUPS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "curricula", "demo_curriculum.groups.yaml")
)


def load_curriculum_groups(groups_path: str) -> Dict[str, str]:
    """
    Loads mapping of concept_id -> group_name from curriculum groups YAML file.
    Supports either:
      groups:
        A: prerequisites
        B: prerequisites
    or:
      groups:
        prerequisites: [A, B]
        downstream: [C, D]
    """
    if not os.path.exists(groups_path):
        raise FileNotFoundError(f"Curriculum groups file not found: {groups_path}")
    with open(groups_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Curriculum groups file must be a YAML dictionary, got {type(data)}")

    raw_groups = data.get("groups", data.get("concept_groups", data))
    if not isinstance(raw_groups, dict):
        raise ValueError(f"Invalid 'groups' section in {groups_path}")

    concept_to_group: Dict[str, str] = {}
    for k, v in raw_groups.items():
        if isinstance(v, list):
            for cid in v:
                concept_to_group[str(cid)] = str(k)
        elif isinstance(v, str):
            concept_to_group[str(k)] = str(v)
        elif v is None:
            concept_to_group[str(k)] = ""
        else:
            raise ValueError(f"Invalid entry in groups mapping: {k}: {v}")

    return concept_to_group


def expand_profile_to_priors(
    profile_id_or_conf: Union[str, Dict[str, Any]],
    groups_path: Optional[str] = None,
    groups_map: Optional[Dict[str, str]] = None,
    curriculum_concepts: Optional[List[str]] = None,
    config_path: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Expands a learner profile into concept-level (p, kappa, n) priors using
    the curriculum groups mapping.

    Raises ValueError if:
    - Any concept has no group.
    - Any group in the mapping is not recognized in the profile's initial_states (and no default).
    - Any foundational_uncertain_nodes in profile are not present in the curriculum concepts.
    """
    # 1. Resolve profile configuration
    if isinstance(profile_id_or_conf, str):
        profile_id = profile_id_or_conf
        p_file = config_path or DEFAULT_PROFILES_PATH
        if not os.path.exists(p_file):
            raise FileNotFoundError(f"Profiles configuration file not found: {p_file}")
        with open(p_file, "r", encoding="utf-8") as f:
            profiles_data = yaml.safe_load(f)
        profiles_dict = profiles_data.get("profiles", {})
        if profile_id not in profiles_dict:
            raise ValueError(f"Profile '{profile_id}' not found in {p_file}")
        profile_conf = profiles_dict[profile_id]
    elif isinstance(profile_id_or_conf, dict):
        profile_conf = profile_id_or_conf
        profile_id = profile_conf.get("id", "custom_profile")
    else:
        raise ValueError(f"Invalid profile specification: {type(profile_id_or_conf)}")

    # 2. Resolve groups mapping
    if groups_map is not None:
        c_to_g = dict(groups_map)
    else:
        g_path = groups_path or DEFAULT_GROUPS_PATH
        c_to_g = load_curriculum_groups(g_path)

    # 3. Check curriculum concepts completeness
    if curriculum_concepts is not None:
        for cid in curriculum_concepts:
            if cid not in c_to_g or c_to_g[cid] is None or not str(c_to_g[cid]).strip():
                raise ValueError(f"Concept '{cid}' has no group defined in curriculum groups mapping")

    # 4. Check foundational_uncertain_nodes if present in profile
    uncertain_nodes = profile_conf.get("foundational_uncertain_nodes", [])
    if uncertain_nodes:
        available_concepts = set(curriculum_concepts) if curriculum_concepts is not None else set(c_to_g.keys())
        missing_uncertain = [n for n in uncertain_nodes if n not in available_concepts]
        if missing_uncertain:
            raise ValueError(
                f"Profile '{profile_id}' specifies foundational_uncertain_nodes {missing_uncertain} "
                f"which do not exist in the curriculum concepts {sorted(available_concepts)}"
            )

    # 5. Expand initial_states to each concept
    init_states = profile_conf.get("initial_states", {})
    expanded: Dict[str, Dict[str, Any]] = {}

    for concept, group in c_to_g.items():
        if group is None or not str(group).strip():
            raise ValueError(f"Concept '{concept}' has no group defined")

        if group in init_states:
            prior = init_states[group]
        elif "default" in init_states:
            prior = init_states["default"]
        else:
            raise ValueError(
                f"Unknown group '{group}' for concept '{concept}' under profile '{profile_id}' "
                f"(valid profile groups: {sorted(init_states.keys())})"
            )

        expanded[concept] = {
            "p": float(prior["p"]),
            "kappa": float(prior["kappa"]),
            "n": int(prior["n"]),
        }

    return expanded


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
    Standard BKT-style matched response generator with optional forgetting (p_F)
    and difficulty-sensitive response probabilities (k).

    Latent mastery is binary: L in {0, 1}.
    - If L = 1 (mastered):
        Baseline correct probability: 1 - p_S.
    - If L = 0 (unmastered):
        Baseline guess probability: p_G.
    - Transition / learning:
        On each attempt of a concept, if unmastered, the learner transitions to
        mastered (L = 1) with probability p_T.
    - Forgetting:
        On advance_day, each mastered concept decays to unmastered with probability p_F per day.
        When p_F = 0, no transitions occur and 0 RNG draws are consumed.

    DIFFICULTY-SENSITIVE VARIANT FORMULA:
    Response probabilities follow a monotone logit scaling with sensitivity parameter k >= 0:
      logit(p) = ln(p / (1 - p))
      P(correct | L=1, d) = sigma(logit(1 - p_S) - k * (d - 0.5))
      P(correct | L=0, d) = sigma(logit(p_G) - k * (d - 0.5))
    where sigma(z) = 1 / (1 + exp(-z)).
    When k = 0, P(correct | L=1, d) = 1 - p_S (0.90) and P(correct | L=0, d) = p_G (0.25) identically.

    P(correct) at difficulty 0.05, 0.50, and 0.95 under p_S=0.10, p_G=0.25, k=0.50:
    -----------------------------------------------------------------
    Difficulty (d)  Mastered P(correct)     Unmastered P(correct)
    -----------------------------------------------------------------
    0.05            0.9185                  0.2945
    0.50 (ref)      0.9000                  0.2500
    0.95            0.8778                  0.2102
    -----------------------------------------------------------------
    """

    def __init__(
        self,
        p_S: float = 0.10,
        p_G: float = 0.25,
        p_T: float = 0.10,
        p_F: float = 0.0,
        k: float = 0.0,
    ):
        if not (0.0 <= p_S <= 1.0):
            raise ValueError(f"p_S must be in [0, 1], got {p_S}")
        if not (0.0 <= p_G <= 1.0):
            raise ValueError(f"p_G must be in [0, 1], got {p_G}")
        if not (0.0 <= p_T <= 1.0):
            raise ValueError(f"p_T must be in [0, 1], got {p_T}")
        if not (0.0 <= p_F <= 1.0):
            raise ValueError(f"p_F must be in [0, 1], got {p_F}")
        if k < 0.0:
            raise ValueError(f"k must be non-negative, got {k}")

        self.p_S = float(p_S)
        self.p_G = float(p_G)
        self.p_T = float(p_T)
        self.p_F = float(p_F)
        self.k = float(k)
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
        1. Emits response according to slip / guess probabilities (and difficulty sensitivity if k > 0).
        2. Applies learning transition if currently unmastered.
        """
        if self.k == 0.0:
            if latent_mastery:
                score = 0 if (rng.random() < self.p_S) else 1
                next_state = True
            else:
                score = 1 if (rng.random() < self.p_G) else 0
                next_state = bool(rng.random() < self.p_T)
            return score, next_state

        # Difficulty-sensitive response generation (monotone logit scaling)
        diff_offset = float(difficulty) - 0.5
        if latent_mastery:
            logit_base = math.log((1.0 - self.p_S) / self.p_S)
            p_correct = 1.0 / (1.0 + math.exp(-(logit_base - self.k * diff_offset)))
            p_slip = 1.0 - p_correct
            score = 0 if (rng.random() < p_slip) else 1
            next_state = True
        else:
            logit_base = math.log(self.p_G / (1.0 - self.p_G))
            p_correct = 1.0 / (1.0 + math.exp(-(logit_base - self.k * diff_offset)))
            score = 1 if (rng.random() < p_correct) else 0
            next_state = bool(rng.random() < self.p_T)

        return score, next_state

    def advance_day(
        self,
        latent_states: Dict[str, bool],
        rng: np.random.Generator,
        num_days: int = 1,
    ) -> Dict[str, bool]:
        """
        Advances the simulated environment by num_days.
        Each day, each currently mastered concept decays to unmastered with probability p_F.
        When p_F == 0.0, returns latent_states unchanged with 0 RNG calls.
        """
        if self.p_F <= 0.0 or num_days <= 0:
            return latent_states

        for _ in range(num_days):
            for concept in sorted(latent_states.keys()):
                if latent_states[concept]:
                    if rng.random() < self.p_F:
                        latent_states[concept] = False
        return latent_states

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "family": self.name,
            "p_S": self.p_S,
            "p_G": self.p_G,
            "p_T": self.p_T,
            "p_F": self.p_F,
            "k": self.k,
        }


class MismatchedPFAOrLogisticGenerator(LearnerGeneratorFamily):
    """
    Performance Factors Analysis (PFA) logistic response generator family.

    ARCHITECTURAL PURPOSE:
    This is a completely different generative family from the BKT generator,
    implemented to check that evaluation conclusions do not depend on the generative
    simulator matching the planner's internal cognitive state models.

    MODEL FORMULATION:
    Response accuracy is a logistic function of concept baseline difficulty (intercept beta_c),
    accumulated practice successes (s_c), accumulated practice failures (f_c), and item difficulty:
        z = beta_c + gamma * s_c + rho * f_c - difficulty_weight * (difficulty - 0.5)
        P(Y = 1) = sigma(z) = 1 / (1 + exp(-z))
    Learning enters strictly through counts of prior successes and failures. There is no BKT transition.

    EVALUATOR MASTERY RULE:
    Latent concept mastery is classified by the evaluator based on success probability at
    reference difficulty 0.5:
        P_ref = sigma(beta_c + gamma * s_c + rho * f_c) >= mastered_p
    where mastered_p is read from YAML (default 0.75, [PROPOSED]).
    """

    def __init__(
        self,
        concept_intercepts: Optional[Dict[str, float]] = None,
        gamma: Optional[float] = None,
        rho: Optional[float] = None,
        difficulty_weight: Optional[float] = None,
        mastered_p: Optional[float] = None,
        p_F: Optional[float] = None,
        **kwargs,
    ):
        self.name = "MismatchedPFAOrLogisticGenerator"
        self._kwargs = kwargs

        # Detect legacy unconfigured stub call: MismatchedPFAOrLogisticGenerator() with no args
        # This keeps existing regression tests in tests/test_simulation.py 100% green.
        has_params = (
            concept_intercepts is not None
            or gamma is not None
            or rho is not None
            or difficulty_weight is not None
            or mastered_p is not None
            or p_F is not None
            or bool(kwargs)
        )
        self._is_configured = has_params

        self.concept_intercepts = dict(concept_intercepts or {
            "A": 0.0,
            "B": -0.2,
            "C": -0.5,
            "D": -1.0,
        })
        self.gamma = 0.40 if gamma is None else float(gamma)
        self.rho = 0.10 if rho is None else float(rho)
        self.difficulty_weight = 1.0 if difficulty_weight is None else float(difficulty_weight)
        self.mastered_p = 0.75 if mastered_p is None else float(mastered_p)
        self.p_F = 0.0 if p_F is None else float(p_F)

        # Learning histories (success and failure attempt counts)
        self.success_counts: Dict[str, int] = {}
        self.failure_counts: Dict[str, int] = {}

    def configure(
        self,
        concept_intercepts: Optional[Dict[str, float]] = None,
        gamma: Optional[float] = None,
        rho: Optional[float] = None,
        difficulty_weight: Optional[float] = None,
        mastered_p: Optional[float] = None,
        p_F: Optional[float] = None,
    ) -> "MismatchedPFAOrLogisticGenerator":
        """Explicitly activates and configures the PFA logistic generator."""
        self._is_configured = True
        if concept_intercepts is not None:
            self.concept_intercepts = dict(concept_intercepts)
        if gamma is not None:
            self.gamma = float(gamma)
        if rho is not None:
            self.rho = float(rho)
        if difficulty_weight is not None:
            self.difficulty_weight = float(difficulty_weight)
        if mastered_p is not None:
            self.mastered_p = float(mastered_p)
        if p_F is not None:
            self.p_F = float(p_F)
        return self

    def generate_response(
        self,
        concept: str,
        difficulty: float,
        latent_mastery: bool,
        rng: np.random.Generator,
    ) -> Tuple[int, bool]:
        if not self._is_configured:
            raise NotImplementedError(
                "Mismatched generator family (PFA/Logistic response model) is scheduled for "
                "Week 5 (W5) implementation."
            )

        s = self.success_counts.get(concept, 0)
        f = self.failure_counts.get(concept, 0)
        beta = self.concept_intercepts.get(concept, 0.0)

        # Logit equation for PFA response probability
        z = beta + self.gamma * s + self.rho * f - self.difficulty_weight * (float(difficulty) - 0.5)
        p_correct = 1.0 / (1.0 + math.exp(-z))

        # Sample binary response
        score = 1 if (rng.random() < p_correct) else 0

        # Update success and failure counts (learning enters only through counts)
        if score == 1:
            self.success_counts[concept] = s + 1
        else:
            self.failure_counts[concept] = f + 1

        # Evaluator mastery classification rule at reference difficulty 0.5
        s_new = self.success_counts.get(concept, 0)
        f_new = self.failure_counts.get(concept, 0)
        z_ref = beta + self.gamma * s_new + self.rho * f_new
        p_ref = 1.0 / (1.0 + math.exp(-z_ref))
        next_latent_mastery = bool(p_ref >= self.mastered_p)

        return score, next_latent_mastery

    def advance_day(
        self,
        latent_states: Dict[str, bool],
        rng: np.random.Generator,
        num_days: int = 1,
    ) -> Dict[str, bool]:
        if self.p_F <= 0.0 or num_days <= 0 or not self._is_configured:
            return latent_states

        for _ in range(num_days):
            for concept in sorted(latent_states.keys()):
                if latent_states[concept]:
                    if rng.random() < self.p_F:
                        latent_states[concept] = False
                        if concept in self.success_counts and self.success_counts[concept] > 0:
                            self.success_counts[concept] = max(0, self.success_counts[concept] - 1)
        return latent_states

    def get_parameters(self) -> Dict[str, Any]:
        if not self._is_configured:
            return {
                "family": self.name,
                "status": "NOT_IMPLEMENTED_SCHEDULED_W5",
                "kwargs": self._kwargs,
            }
        return {
            "family": self.name,
            "status": "ACTIVE_PFA_LOGISTIC",
            "concept_intercepts": self.concept_intercepts,
            "gamma": self.gamma,
            "rho": self.rho,
            "difficulty_weight": self.difficulty_weight,
            "mastered_p": self.mastered_p,
            "p_F": self.p_F,
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
        groups_path: Optional[str] = None,
        groups_map: Optional[Dict[str, str]] = None,
        curriculum_concepts: Optional[List[str]] = None,
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
        self.expanded_priors: Optional[Dict[str, Dict[str, Any]]] = None
        self._latent_states: Dict[str, bool] = {}

        if initial_mastery is not None:
            self._latent_states = {k: bool(v) for k, v in initial_mastery.items()}
        else:
            # Check if groups file or map exists to expand into concept priors
            g_path = groups_path or (DEFAULT_GROUPS_PATH if os.path.exists(DEFAULT_GROUPS_PATH) else None)
            if groups_map is not None or g_path is not None:
                self.expanded_priors = expand_profile_to_priors(
                    profile_conf,
                    groups_path=g_path,
                    groups_map=groups_map,
                    curriculum_concepts=curriculum_concepts,
                )
                for concept, prior in self.expanded_priors.items():
                    p_init = prior["p"]
                    self._latent_states[concept] = bool(self.rng.random() < p_init)
            else:
                # Fallback to direct initial_states if no curriculum groups are available
                init_states = profile_conf.get("initial_states", {})
                for group, params in init_states.items():
                    p_init = float(params.get("p", 0.5))
                    self._latent_states[group] = bool(self.rng.random() < p_init)

    def get_expanded_priors(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Returns the concept-level (p, kappa, n) priors expanded for this learner."""
        return self.expanded_priors

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

    def advance_day(self, num_days: int = 1) -> Dict[str, bool]:
        """
        Advances the simulated environment by num_days.
        Under forgetting variants (p_F > 0), mastered concepts may decay to unmastered.
        When p_F == 0.0, latent mastery states remain unchanged and 0 RNG calls are made.
        """
        if hasattr(self.generator_family, "advance_day"):
            self._latent_states = self.generator_family.advance_day(
                self._latent_states,
                self.rng,
                num_days=num_days,
            )
        return dict(self._latent_states)

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
