"""ASSISTments-calibrated BKT learner generator (Week 8 public-data extension, scenario S4).

Same response and learning rule as MatchedBKTGenerator (k = 0, no forgetting), but every
(learner, concept) pair gets its own slip / guess / learn triple, drawn from the per-skill
BKT fits on real students in config/bkt_assistments.yaml (fitted by
scripts/assistments_fit_bkt.py on ASSISTments 2009-2010 train students).

Only fits with p_G < 0.5 and p_S < 0.5 are used; outside that range BKT fits are known to be
poorly identified (a "learner" who guesses better than they answer when they know it).

The draw for a concept depends only on (learner seed, concept name), via its own RNG, so:
  * every arm sees the same parameters for the same learner (matched cohorts stay matched);
  * the learner's response RNG is untouched by the draw.
The engine's own BKT parameters are NOT changed: S4 tests the planner on learners whose
dynamics differ from what it assumes. Initial latent mastery still comes from the harness
(theta >= b_concept), not from the ASSISTments prior.
"""
import os
import zlib
from typing import Dict, List, Optional

import numpy as np
import yaml

from src.simulation.simulator import MatchedBKTGenerator

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_FIT_PATH = os.path.join(REPO_ROOT, "config", "bkt_assistments.yaml")
MAX_GUESS = 0.5
MAX_SLIP = 0.5

_POOL_CACHE: Dict[str, List[Dict[str, float]]] = {}


def load_parameter_pool(path: str = DEFAULT_FIT_PATH) -> List[Dict[str, float]]:
    """Identifiable per-skill (p_S, p_G, p_T) triples, in sorted skill order."""
    if path not in _POOL_CACHE:
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{path} not found. Run scripts/assistments_prepare.py and scripts/assistments_fit_bkt.py first.")
        with open(path, encoding="utf-8") as f:
            skills = yaml.safe_load(f)["skills"]
        pool = []
        for name in sorted(skills):
            p = skills[name]
            if p["p_G"] < MAX_GUESS and p["p_S"] < MAX_SLIP:
                pool.append({"skill": name, "p_S": float(p["p_S"]), "p_G": float(p["p_G"]),
                             "p_T": float(p["p_T"])})
        if not pool:
            raise ValueError(f"No identifiable skill fits in {path}")
        _POOL_CACHE[path] = pool
    return _POOL_CACHE[path]


class CalibratedBKTGenerator(MatchedBKTGenerator):
    def __init__(self, learner_seed: Optional[int] = None, fit_path: str = DEFAULT_FIT_PATH):
        pool = load_parameter_pool(fit_path)
        med = {k: float(np.median([p[k] for p in pool])) for k in ("p_S", "p_G", "p_T")}
        super().__init__(p_S=med["p_S"], p_G=med["p_G"], p_T=med["p_T"], p_F=0.0, k=0.0)
        self.name = "CalibratedBKTGenerator"
        self.pool = pool
        self.learner_seed = 0 if learner_seed is None else int(learner_seed)
        self.concept_params: Dict[str, Dict[str, float]] = {}

    def params_for(self, concept: str) -> Dict[str, float]:
        if concept not in self.concept_params:
            rng = np.random.default_rng([self.learner_seed, zlib.crc32(str(concept).encode("utf-8"))])
            self.concept_params[concept] = dict(self.pool[int(rng.integers(len(self.pool)))])
        return self.concept_params[concept]

    def generate_response(self, concept, difficulty, latent_mastery, rng):
        p = self.params_for(concept)
        if latent_mastery:
            return (0 if rng.random() < p["p_S"] else 1), True
        score = 1 if rng.random() < p["p_G"] else 0
        return score, bool(rng.random() < p["p_T"])

    def get_parameters(self):
        out = super().get_parameters()
        out.update({"pool_size": len(self.pool), "source": "config/bkt_assistments.yaml",
                    "concept_params": {c: dict(v) for c, v in sorted(self.concept_params.items())}})
        return out
