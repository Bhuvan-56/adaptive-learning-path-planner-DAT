"""
Adaptive Diagnostic Module using Computerized Adaptive Testing (CAT / IRT).

ARCHITECTURE & CONTRACT:
-------------------------
1. Implements Computerized Adaptive Testing using the catsim package (v0.21.0):
   - Initializer: catsim.initialization.FixedPointInitializer(0.0)
   - Item Selector: catsim.selection.MaxInfoSelector() (Maximum Fisher Information)
   - Ability Estimator: catsim.estimation.NumericalSearchEstimator()
   - Stopping Rule: catsim.stopping.MinErrorStopper with standard error sqrt(stopping_variance)
     and maximum questions cap.
2. Injected Responder: The diagnostic engine accepts an injected callable `respond(item_id)`
   returning 0 or 1. It never imports or interacts directly with the simulation engine.

3. ADR-009 Cold-Start Mapping:
   - Probed concepts (having direct items in the Q-matrix) are initialized with:
       p = 1 / (1 + exp(-theta_hat)), clamped to [0.01, 0.99]
       ConceptState.init_from_ability(p)  -> kappa=2.0, n=0, history=[]
   - Unprobed concepts (having no items in the Q-matrix) are initialized with:
       ConceptState.cold_start()         -> p=0.5, kappa=2.0, n=0, history=[]
   - All concept states classify as 'Uncertain' because n == 0 < min_obs.
"""

from dataclasses import dataclass
import json
import math
import os
from typing import Callable, Dict, List, Optional, Set, Tuple, Union, Any
import numpy as np
import pandas as pd
import yaml

import catsim.cat as cat
import catsim.estimation as est
import catsim.initialization as init
import catsim.irt as irt
import catsim.selection as sel
import catsim.stopping as stp

from src.state.learner_state import ConceptState


DEFAULT_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "m8_learner_eval.yaml")
)
DEFAULT_CURRICULUM_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "curricula", "demo_curriculum.json")
)
DEFAULT_ITEM_BANK_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "item_bank_synthetic.csv")
)
DEFAULT_QMATRIX_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "q_matrix_synthetic.csv")
)


def load_cat_hyperparameters(config_path: Optional[str] = None) -> Tuple[float, int]:
    """
    Loads CAT stopping hyperparameters from experiments/m8_learner_eval.yaml:
    - stopping_variance: maximum variance of theta_hat to trigger stopping
    - max_questions: maximum items before forced termination
    """
    path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cat_cfg = data.get("model_hyperparameters", {}).get("cat", {})
    stopping_variance = float(cat_cfg.get("stopping_variance", 0.15))
    max_questions = int(cat_cfg.get("max_questions", 10))
    return stopping_variance, max_questions


def ability_to_prior(theta: float) -> float:
    """
    Maps IRT ability estimate theta to initial BKT mastery prior p using the
    canonical logistic link function (ADR-009):
        p = 1 / (1 + exp(-theta))
    clamped to [0.01, 0.99].
    """
    if theta >= 40.0:
        p = 1.0
    elif theta <= -40.0:
        p = 0.0
    else:
        p = 1.0 / (1.0 + math.exp(-theta))
    return max(0.01, min(0.99, p))


def load_item_bank_and_qmatrix(
    bank_source: Any,
    qmatrix_source: Any,
    curriculum_source: Any = None,
) -> Tuple[List[str], np.ndarray, Dict[str, str], List[str]]:
    """
    Loads and validates the item bank, Q-matrix, and curriculum concepts.

    Raises ValueError with the field named for:
    - An item with no concept in Q-matrix ('concept')
    - An item mapped to a concept not in the curriculum ('concept')
    - Duplicate item ID ('item_id')
    - Non-finite parameter ('a', 'b', 'c', 'd', etc.)
    """
    # 1. Resolve curriculum concepts
    curriculum_concepts: Optional[List[str]] = None
    if curriculum_source is not None:
        if isinstance(curriculum_source, (list, tuple, set)):
            curriculum_concepts = [str(c) for c in curriculum_source]
        elif isinstance(curriculum_source, str):
            if os.path.exists(curriculum_source):
                with open(curriculum_source, "r", encoding="utf-8") as f:
                    curr_json = json.load(f)
                curriculum_concepts = [n["node_id"] for n in curr_json.get("nodes", [])]
            else:
                curriculum_concepts = [curriculum_source]
    else:
        if os.path.exists(DEFAULT_CURRICULUM_PATH):
            with open(DEFAULT_CURRICULUM_PATH, "r", encoding="utf-8") as f:
                curr_json = json.load(f)
            curriculum_concepts = [n["node_id"] for n in curr_json.get("nodes", [])]

    # 2. Load Item Bank DataFrame
    if isinstance(bank_source, pd.DataFrame):
        bank_df = bank_source.copy()
    elif isinstance(bank_source, str):
        if not os.path.exists(bank_source):
            raise FileNotFoundError(f"Item bank file not found: {bank_source}")
        bank_df = pd.read_csv(bank_source)
    elif isinstance(bank_source, list):
        bank_df = pd.DataFrame(bank_source)
    else:
        raise ValueError(f"Unsupported item bank source type: {type(bank_source)}")

    # 3. Load Q-matrix DataFrame or dict
    if isinstance(qmatrix_source, pd.DataFrame):
        q_df = qmatrix_source.copy()
    elif isinstance(qmatrix_source, str):
        if not os.path.exists(qmatrix_source):
            raise FileNotFoundError(f"Q-matrix file not found: {qmatrix_source}")
        q_df = pd.read_csv(qmatrix_source)
    elif isinstance(qmatrix_source, dict):
        q_df = pd.DataFrame([{"item_id": k, "concept_id": v} for k, v in qmatrix_source.items()])
    elif isinstance(qmatrix_source, list):
        q_df = pd.DataFrame(qmatrix_source)
    else:
        raise ValueError(f"Unsupported Q-matrix source type: {type(qmatrix_source)}")

    # 4. Normalize and validate Q-matrix columns
    q_cols = {c.lower(): c for c in q_df.columns}
    item_col_q = q_cols.get("item_id", q_cols.get("item"))
    concept_col = q_cols.get("concept_id", q_cols.get("concept"))

    if not item_col_q:
        raise ValueError("Field 'item_id' missing from Q-matrix")
    if not concept_col:
        raise ValueError("Field 'concept' missing from Q-matrix")

    # Check duplicate item_id in Q-matrix
    q_items_seen = set()
    item_to_concept: Dict[str, str] = {}
    for _, row in q_df.iterrows():
        iid = str(row[item_col_q])
        if iid in q_items_seen:
            raise ValueError(f"Duplicate item_id in Q-matrix: '{iid}'")
        q_items_seen.add(iid)
        cval = row[concept_col]
        if pd.isna(cval) or cval is None or not str(cval).strip():
            raise ValueError(f"Field 'concept' cannot be empty for item '{iid}'")
        item_to_concept[iid] = str(cval).strip()

    # 5. Normalize and validate Item Bank columns
    b_cols = {c.lower(): c for c in bank_df.columns}
    item_col_b = b_cols.get("item_id", b_cols.get("item"))
    if not item_col_b:
        raise ValueError("Field 'item_id' missing from item bank")

    col_a = b_cols.get("a", b_cols.get("discrimination"))
    col_b = b_cols.get("b", b_cols.get("difficulty"))
    col_c = b_cols.get("c", b_cols.get("pseudo_guessing"))
    col_d = b_cols.get("d", b_cols.get("upper_asymptote"))

    if not col_a:
        raise ValueError("Field 'a' (discrimination) missing from item bank")
    if not col_b:
        raise ValueError("Field 'b' (difficulty) missing from item bank")

    # Check duplicate item_id in Item Bank
    bank_items_seen = set()
    item_ids: List[str] = []
    matrix_rows = []

    for _, row in bank_df.iterrows():
        iid = str(row[item_col_b])
        if iid in bank_items_seen:
            raise ValueError(f"Duplicate item_id found: '{iid}'")
        bank_items_seen.add(iid)

        # Validate non-finite parameters with field names
        for field_name, col_name, default_val in [
            ("a", col_a, None),
            ("b", col_b, None),
            ("c", col_c, 0.0),
            ("d", col_d, 1.0),
        ]:
            if col_name and col_name in row:
                val = row[col_name]
            else:
                val = default_val

            if val is None or pd.isna(val) or not math.isfinite(float(val)):
                raise ValueError(f"Non-finite parameter '{field_name}' for item '{iid}': {val}")

        val_a = float(row[col_a])
        val_b = float(row[col_b])
        val_c = float(row[col_c]) if col_c and col_c in row and not pd.isna(row[col_c]) else 0.0
        val_d = float(row[col_d]) if col_d and col_d in row and not pd.isna(row[col_d]) else 1.0

        if val_a <= 0.0:
            raise ValueError(f"Parameter 'a' (discrimination) must be strictly positive for item '{iid}': {val_a}")

        # Check item has concept in Q-matrix
        if iid not in item_to_concept:
            raise ValueError(f"Item '{iid}' has no concept defined in Q-matrix (field 'concept' missing)")

        concept_id = item_to_concept[iid]
        # Check concept in curriculum
        if curriculum_concepts is not None and concept_id not in curriculum_concepts:
            raise ValueError(
                f"Item '{iid}' mapped to concept '{concept_id}' which is not in the curriculum concepts {curriculum_concepts} (field 'concept')"
            )

        item_ids.append(iid)
        # catsim ItemBank expects 5 columns: [a, b, c, d, exposure_rate]
        matrix_rows.append([val_a, val_b, val_c, val_d, 0.0])

    items_matrix = np.array(matrix_rows, dtype=float)
    final_curriculum_concepts = curriculum_concepts if curriculum_concepts is not None else sorted(set(item_to_concept.values()))

    return item_ids, items_matrix, item_to_concept, final_curriculum_concepts


@dataclass
class DiagnosticResult:
    """Output artifact resulting from an adaptive diagnostic assessment."""
    theta_hat: float
    variance: float
    items_asked: List[str]
    concept_states: Dict[str, ConceptState]

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


class AdaptiveDiagnostic:
    """
    Adaptive diagnostic assessment engine executing Computerized Adaptive Testing (CAT).
    """

    def __init__(
        self,
        bank_source: Any = DEFAULT_ITEM_BANK_PATH,
        qmatrix_source: Any = DEFAULT_QMATRIX_PATH,
        curriculum_source: Any = DEFAULT_CURRICULUM_PATH,
        config_path: Optional[str] = None,
        stopping_variance: Optional[float] = None,
        max_questions: Optional[int] = None,
    ):
        self.item_ids, self.items_matrix, self.item_to_concept, self.curriculum_concepts = load_item_bank_and_qmatrix(
            bank_source=bank_source,
            qmatrix_source=qmatrix_source,
            curriculum_source=curriculum_source,
        )

        cfg_var, cfg_max_q = load_cat_hyperparameters(config_path)
        self.stopping_variance = float(stopping_variance) if stopping_variance is not None else cfg_var
        self.max_questions = int(max_questions) if max_questions is not None else cfg_max_q

        # Calculate standard error stopping criterion dynamically (math.sqrt)
        self.stopping_error = math.sqrt(self.stopping_variance)

        # Initialize catsim ItemBank
        self.catsim_bank = cat.ItemBank(self.items_matrix)

    def run(self, respond: Callable[[str], int]) -> DiagnosticResult:
        """
        Executes the adaptive testing loop using injected respond(item_id) callable.
        """
        initializer = init.FixedPointInitializer(0.0)
        current_theta = float(initializer.initialize())

        selector = sel.MaxInfoSelector()
        estimator = est.NumericalSearchEstimator()
        stopper = stp.MinErrorStopper(min_error=self.stopping_error, max_items=self.max_questions)

        administered_indices: List[int] = []
        administered_item_ids: List[str] = []
        response_vector: List[bool] = []

        while True:
            # Check stopping constraints if at least one item was administered
            if administered_indices:
                if len(administered_indices) >= self.max_questions:
                    break

                administered_params = self.catsim_bank.get_items(administered_indices)[:, :4]
                see = float(irt.see(current_theta, administered_params))
                variance = see ** 2

                if stopper.stop(administered_items=administered_params, theta=current_theta) or variance <= self.stopping_variance:
                    break

            # Select next maximum Fisher information item
            next_idx = selector.select(
                item_bank=self.catsim_bank,
                administered_items=administered_indices,
                est_theta=current_theta,
            )

            if next_idx is None:
                # All items in bank exhausted
                break

            item_id = self.item_ids[next_idx]
            outcome = int(respond(item_id))
            bool_resp = bool(outcome == 1 or outcome is True)

            administered_indices.append(next_idx)
            administered_item_ids.append(item_id)
            response_vector.append(bool_resp)

            # Update ability estimate theta_hat via numerical search maximum likelihood
            current_theta = float(
                estimator.estimate(
                    item_bank=self.catsim_bank,
                    administered_items=administered_indices,
                    response_vector=response_vector,
                    est_theta=current_theta,
                )
            )

            # Post-response check
            administered_params = self.catsim_bank.get_items(administered_indices)[:, :4]
            see = float(irt.see(current_theta, administered_params))
            variance = see ** 2

            if stopper.stop(administered_items=administered_params, theta=current_theta) or variance <= self.stopping_variance:
                break
            if len(administered_indices) >= self.max_questions:
                break

        # Compute final variance
        if administered_indices:
            administered_params = self.catsim_bank.get_items(administered_indices)[:, :4]
            final_see = float(irt.see(current_theta, administered_params))
            final_variance = final_see ** 2
        else:
            final_variance = float("inf")

        # Build concept states according to ADR-009:
        # - Concepts with items in bank: initialized from ability (p = sigmoid(theta_hat), kappa=2.0, n=0)
        # - Concepts without items in bank: cold start (p=0.5, kappa=2.0, n=0)
        probed_concepts: Set[str] = set(self.item_to_concept.values())
        concept_states: Dict[str, ConceptState] = {}
        prior_p = ability_to_prior(current_theta)

        for concept in self.curriculum_concepts:
            if concept in probed_concepts:
                concept_states[concept] = ConceptState.init_from_ability(prior_p)
            else:
                concept_states[concept] = ConceptState.cold_start()

        return DiagnosticResult(
            theta_hat=current_theta,
            variance=final_variance,
            items_asked=administered_item_ids,
            concept_states=concept_states,
        )


def run_adaptive_diagnostic(
    respond: Callable[[str], int],
    bank_source: Any = DEFAULT_ITEM_BANK_PATH,
    qmatrix_source: Any = DEFAULT_QMATRIX_PATH,
    curriculum_source: Any = DEFAULT_CURRICULUM_PATH,
    config_path: Optional[str] = None,
    stopping_variance: Optional[float] = None,
    max_questions: Optional[int] = None,
) -> DiagnosticResult:
    """Convenience function running adaptive diagnostic assessment."""
    diagnostic = AdaptiveDiagnostic(
        bank_source=bank_source,
        qmatrix_source=qmatrix_source,
        curriculum_source=curriculum_source,
        config_path=config_path,
        stopping_variance=stopping_variance,
        max_questions=max_questions,
    )
    return diagnostic.run(respond)
