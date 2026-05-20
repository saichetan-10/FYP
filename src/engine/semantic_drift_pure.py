"""Semantic Drift Metric - Pure Python (No External Dependencies)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from src.types import DriftMetrics
from src.logging_config import StructuredLogger

logger = StructuredLogger(__name__)


@dataclass
class DriftComponent:
    """Individual component of drift calculation."""

    name: str
    value: float
    weight: float
    threshold: float
    details: Dict = field(default_factory=dict)


class SimpleNumpy:
    """Minimal numpy-like functionality without external dependencies."""

    @staticmethod
    def mean(values: List[float]) -> float:
        """Compute mean."""
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def std(values: List[float]) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = SimpleNumpy.mean(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    @staticmethod
    def max(values: List[float]) -> float:
        """Get maximum."""
        return max(values) if values else 0.0

    @staticmethod
    def clip(value: float, min_val: float, max_val: float) -> float:
        """Clip value to range."""
        return max(min_val, min(max_val, value))


class SemanticDriftMetricPure:
    """
    Semantic Drift Metric implementation using only Python standard library.
    No dependencies on NumPy or SciPy.
    """

    BASELINES_FILE = "logs/baselines.json"

    def __init__(self):
        """Initialize the metric calculator."""
        self.intent_weight = 0.4
        self.constraint_weight = 0.3
        self.plausibility_weight = 0.3
        self.z_threshold = 3.0
        self.drift_threshold = 0.15

        # Baseline statistics cache
        self.historical_stats: Dict[str, Dict] = {}
        self._load_baselines()

    def compute_intent_alignment(
        self,
        query_embedding: List[float],
        ontology_embeddings: List[List[float]],
        retrieved_ontology_paths: List[str],
    ) -> Tuple[float, Dict]:
        """
        Compute intent alignment via cosine similarity.

        Args:
            query_embedding: Query embedding vector
            ontology_embeddings: List of ontology path embeddings
            retrieved_ontology_paths: Paths retrieved from ontology

        Returns:
            Tuple of (alignment_score, details_dict)
        """
        if not ontology_embeddings or len(ontology_embeddings) == 0:
            logger.warning("empty_ontology_embeddings")
            return 0.0, {"error": "no_ontology_embeddings", "similarities": []}

        # Compute cosine similarities
        similarities = []
        for emb in ontology_embeddings:
            sim = self._cosine_similarity(query_embedding, emb)
            similarities.append(sim)

        max_similarity = SimpleNumpy.max(similarities)
        mean_similarity = SimpleNumpy.mean(similarities)
        std_similarity = SimpleNumpy.std(similarities)

        # Alignment score: high if similarities concentrated near peak
        if std_similarity + 1.0 > 0:
            alignment_score = max_similarity * (1.0 - (std_similarity / (1.0 + std_similarity)))
        else:
            alignment_score = max_similarity

        details = {
            "max_similarity": float(max_similarity),
            "mean_similarity": float(mean_similarity),
            "std_similarity": float(std_similarity),
            "num_paths_evaluated": len(ontology_embeddings),
            "alignment_formula": "max_sim * (1 - std_norm)",
        }

        logger.info("intent_alignment_computed", alignment=float(alignment_score), **details)
        return float(alignment_score), details

    def compute_constraint_adherence(
        self,
        constraints_required: int,
        constraints_satisfied: int,
        constraint_details: List[Dict] = None,
    ) -> Tuple[float, Dict]:
        """
        Compute constraint adherence as percentage of rules satisfied.

        Args:
            constraints_required: Total business rules that should apply
            constraints_satisfied: Number of rules actually satisfied
            constraint_details: Optional list of constraint satisfaction details

        Returns:
            Tuple of (adherence_score, details_dict)
        """
        if constraints_required == 0:
            adherence_score = 1.0
        else:
            adherence_score = float(constraints_satisfied / constraints_required)

        details = {
            "required": constraints_required,
            "satisfied": constraints_satisfied,
            "adherence_percentage": adherence_score * 100.0,
            "constraint_details": constraint_details or [],
        }

        logger.info(
            "constraint_adherence_computed",
            adherence=float(adherence_score),
            **details,
        )
        return float(adherence_score), details

    def compute_result_plausibility(
        self,
        result_values: List[float],
        metric_id: str,
        historical_values: Optional[List[float]] = None,
    ) -> Tuple[float, Dict]:
        """
        Compute result plausibility via z-score deviation from baseline.

        Args:
            result_values: Result metric values
            metric_id: Identifier for this metric type
            historical_values: Historical values for computing baseline (optional)

        Returns:
            Tuple of (plausibility_score, details_dict)
        """
        if not result_values:
            return 1.0, {"error": "no_result_values"}

        result_mean = SimpleNumpy.mean(result_values)
        result_std = SimpleNumpy.std(result_values)
        if result_std == 0:
            result_std = 1.0

        # Get or compute baseline statistics
        if metric_id not in self.historical_stats:
            if historical_values is None:
                # Initialize baseline if not provided
                self.historical_stats[metric_id] = {
                    "mean": result_mean,
                    "std": max(result_std, 1.0),
                }
            else:
                self.historical_stats[metric_id] = {
                    "mean": SimpleNumpy.mean(historical_values),
                    "std": max(SimpleNumpy.std(historical_values), 1.0),
                }

        baseline = self.historical_stats[metric_id]

        # Compute z-scores
        z_scores = []
        for val in result_values:
            z = abs((val - baseline["mean"]) / (baseline["std"] + 1e-8))
            z_scores.append(z)

        max_z_score = SimpleNumpy.max(z_scores) if z_scores else 0.0

        # Plausibility: higher if z-scores are lower (more normal)
        plausibility_score = 1.0 / (1.0 + max_z_score / self.z_threshold)

        details = {
            "result_mean": float(result_mean),
            "result_std": float(result_std),
            "baseline_mean": float(baseline["mean"]),
            "baseline_std": float(baseline["std"]),
            "max_z_score": float(max_z_score),
            "z_threshold": self.z_threshold,
            "plausibility_formula": "1 / (1 + z_score/threshold)",
            "num_values": len(result_values),
        }

        logger.info(
            "result_plausibility_computed",
            plausibility=float(plausibility_score),
            **details,
        )
        return float(plausibility_score), details

    def compute_composite_drift(
        self,
        intent_alignment: float,
        constraint_adherence: float,
        result_plausibility: float,
    ) -> Tuple[float, DriftMetrics]:
        """
        Compute composite drift as weighted sum of components.

        Args:
            intent_alignment: Alignment score [0, 1]
            constraint_adherence: Adherence score [0, 1]
            result_plausibility: Plausibility score [0, 1]

        Returns:
            Tuple of (composite_drift_score, DriftMetrics object)
        """
        # Invert scores so higher = worse (drift)
        intent_drift = 1.0 - intent_alignment
        constraint_drift = 1.0 - constraint_adherence
        plausibility_drift = 1.0 - result_plausibility

        # Weighted composite
        composite = (
            self.intent_weight * intent_drift
            + self.constraint_weight * constraint_drift
            + self.plausibility_weight * plausibility_drift
        )

        # Ensure bounded [0, 1]
        composite_drift = SimpleNumpy.clip(float(composite), 0.0, 1.0)

        # Passing threshold means drift is BELOW configured threshold
        passing = composite_drift < self.drift_threshold

        metrics = DriftMetrics(
            intent_alignment=float(intent_alignment),
            constraint_adherence=float(constraint_adherence),
            result_plausibility=float(result_plausibility),
            composite_drift=composite_drift,
            components={
                "intent_drift": float(intent_drift),
                "constraint_drift": float(constraint_drift),
                "plausibility_drift": float(plausibility_drift),
                "weights": {
                    "intent": self.intent_weight,
                    "constraint": self.constraint_weight,
                    "plausibility": self.plausibility_weight,
                },
            },
            passing_threshold=passing,
        )

        logger.info(
            "composite_drift_computed",
            composite_drift=composite_drift,
            passing=passing,
            threshold=self.drift_threshold,
        )

        return composite_drift, metrics

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = (sum(a ** 2 for a in vec1)) ** 0.5
        norm2 = (sum(b ** 2 for b in vec2)) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def validate_drift_threshold(
        self, composite_drift: float, iteration: int, max_iterations: int
    ) -> Tuple[bool, str]:
        """
        Validate if drift has converged or max iterations reached.

        Args:
            composite_drift: Current composite drift score
            iteration: Current iteration count
            max_iterations: Maximum iterations allowed

        Returns:
            Tuple of (continue_iteration, reason_message)
        """
        if composite_drift < self.drift_threshold:
            return False, f"Drift converged: {composite_drift:.4f} < {self.drift_threshold}"

        if iteration >= max_iterations:
            return False, f"Max iterations reached: {iteration}/{max_iterations}"

        return True, f"Continuing: iteration {iteration}/{max_iterations}, drift {composite_drift:.4f}"

    def _load_baselines(self) -> None:
        """Load persisted baselines from disk if available."""
        import json
        import os
        if os.path.exists(self.BASELINES_FILE):
            try:
                with open(self.BASELINES_FILE) as f:
                    self.historical_stats = json.load(f)
            except Exception:
                self.historical_stats = {}

    def _save_baselines(self) -> None:
        """Persist baseline statistics to disk."""
        import json
        import os
        os.makedirs("logs", exist_ok=True)
        try:
            with open(self.BASELINES_FILE, "w") as f:
                json.dump(self.historical_stats, f)
        except Exception:
            pass

    def update_baseline(self, metric_id: str, values: List[float]) -> None:
        """Update and persist baseline statistics for a metric."""
        self.historical_stats[metric_id] = {
            "mean": SimpleNumpy.mean(values),
            "std": max(SimpleNumpy.std(values), 1.0),
        }
        self._save_baselines()

    def get_baseline(self, metric_id: str) -> Optional[dict]:
        """Get baseline statistics for a metric."""
        return self.historical_stats.get(metric_id)


# Alias so tests can import as SemanticDriftMetric
SemanticDriftMetric = SemanticDriftMetricPure
