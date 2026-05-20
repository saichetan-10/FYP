"""
Semantic Drift Metric: A Novel Composite Scoring System

This module implements the core semantic drift metric combining three dimensions:
1. Intent Alignment (40%): How well extracted intent matches ontology
2. Constraint Adherence (30%): Percentage of business rules satisfied
3. Result Plausibility (30%): Statistical anomaly detection on results

The metric ranges from [0, 1] where:
- 0.0 = Perfect drift-free execution
- 1.0 = Severe misalignment
- Convergence threshold = 0.15 (configurable)

Academic Formula:
drift = 0.4×(1-intent_alignment) + 0.3×(1-constraint_adherence) + 0.3×(1-result_plausibility)
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics


@dataclass
class DriftMetricComponents:
    """Breakdown of drift metric components for analysis."""
    intent_alignment: float
    constraint_adherence: float
    result_plausibility: float
    composite_drift: float
    timestamp: datetime
    breakdown: Dict[str, Any]


class IntentAlignmentCalculator:
    """
    Calculates Intent Alignment (40% weight):
    
    Measures cosine similarity between extracted user intent embeddings
    and the formal business ontology embeddings. Higher similarity = better alignment.
    """
    
    @staticmethod
    def calculate_embedding_similarity(
        query_embedding: List[float],
        ontology_embedding: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            query_embedding: Vector representation of user query
            ontology_embedding: Vector representation of ontology path
            
        Returns:
            Cosine similarity score [0, 1]
        """
        if not query_embedding or not ontology_embedding:
            return 0.0
        
        # Cosine similarity: A·B / (||A|| × ||B||)
        dot_product = sum(a * b for a, b in zip(query_embedding, ontology_embedding))
        mag_a = math.sqrt(sum(a ** 2 for a in query_embedding))
        mag_b = math.sqrt(sum(b ** 2 for b in ontology_embedding))
        
        if mag_a == 0 or mag_b == 0:
            return 0.0
        
        return dot_product / (mag_a * mag_b)
    
    @staticmethod
    def calculate_alignment_score(
        extraction_confidences: Dict[str, float],
        mapping_similarities: List[float]
    ) -> float:
        """
        Aggregate alignment from extraction confidences and mapping similarities.
        
        Args:
            extraction_confidences: Confidence scores for each extracted element
            mapping_similarities: Semantic similarities for each ontology mapping
            
        Returns:
            Overall alignment score [0, 1]
        """
        if not extraction_confidences and not mapping_similarities:
            return 0.0
        
        # Weight: 60% extraction confidence, 40% mapping similarity
        extract_avg = (
            sum(extraction_confidences.values()) / len(extraction_confidences)
            if extraction_confidences else 0.0
        )
        
        map_avg = (
            sum(mapping_similarities) / len(mapping_similarities)
            if mapping_similarities else 0.0
        )
        
        return 0.6 * extract_avg + 0.4 * map_avg


class ConstraintAdherenceCalculator:
    """
    Calculates Constraint Adherence (30% weight):
    
    Measures percentage of business rules that are satisfied by the
    retrieved results and query plan. All constraints are equally weighted.
    """
    
    @staticmethod
    def calculate_adherence_score(
        constraints_list: List[Dict[str, Any]],
        satisfied_count: Optional[int] = None
    ) -> float:
        """
        Calculate percentage of satisfied constraints.
        
        Args:
            constraints_list: List of constraint dictionaries with 'is_satisfied' key
            satisfied_count: Optional override for satisfied count
            
        Returns:
            Adherence score [0, 1] (1.0 = all constraints satisfied)
        """
        if not constraints_list:
            return 1.0  # No constraints = perfect adherence
        
        if satisfied_count is not None:
            return min(1.0, satisfied_count / len(constraints_list))
        
        # Count constraints with is_satisfied=True
        satisfied = sum(1 for c in constraints_list if c.get("is_satisfied", False))
        return satisfied / len(constraints_list)
    
    @staticmethod
    def categorize_constraint_violations(
        constraints_list: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Categorize constraints by type and violation status for debugging.
        
        Args:
            constraints_list: List of constraint dictionaries
            
        Returns:
            Dictionary mapping constraint types to list of violated descriptions
        """
        violations = {}
        
        for constraint in constraints_list:
            if not constraint.get("is_satisfied", True):
                ctype = constraint.get("type", "unknown")
                if ctype not in violations:
                    violations[ctype] = []
                violations[ctype].append(constraint.get("description", ""))
        
        return violations


class ResultPlausibilityCalculator:
    """
    Calculates Result Plausibility (30% weight):
    
    Uses statistical anomaly detection (Z-score based) to detect if
    retrieved results are statistically plausible given historical data.
    Also considers row count sanity checks.
    """
    
    @staticmethod
    def calculate_z_score_anomaly(
        value: float,
        historical_values: List[float]
    ) -> float:
        """
        Calculate Z-score for detecting statistical anomalies.
        
        Z = (x - mean) / std_dev
        
        Args:
            value: The result value to test
            historical_values: List of historical values for baseline
            
        Returns:
            Absolute Z-score (0 = at mean, >3 = anomaly)
        """
        if len(historical_values) < 2:
            return 0.0
        
        mean_val = statistics.mean(historical_values)
        
        # Need at least 2 values for stdev
        if len(historical_values) < 2:
            return 0.0
        
        try:
            stdev = statistics.stdev(historical_values)
        except statistics.StatisticsError:
            return 0.0
        
        if stdev == 0:
            return 0.0
        
        z_score = abs((value - mean_val) / stdev)
        return z_score
    
    @staticmethod
    def normalize_z_score_to_plausibility(z_score: float) -> float:
        """
        Convert Z-score to plausibility score [0, 1].
        
        Mapping:
        - Z <= 2: plausibility = 1.0 (normal)
        - Z = 3: plausibility = 0.5 (borderline anomaly)
        - Z >= 4: plausibility = 0.0 (clear anomaly)
        
        Args:
            z_score: Absolute Z-score from historical data
            
        Returns:
            Plausibility score [0, 1]
        """
        if z_score <= 2.0:
            return 1.0
        elif z_score >= 4.0:
            return 0.0
        else:
            # Linear interpolation between Z=2 and Z=4
            return 1.0 - (z_score - 2.0) / 2.0
    
    @staticmethod
    def check_row_count_plausibility(
        result_count: int,
        historical_row_counts: List[int],
        max_expected_increase: float = 10.0
    ) -> Tuple[bool, float]:
        """
        Check if result row count is plausible given historical patterns.
        
        Args:
            result_count: Number of rows in current result
            historical_row_counts: List of historical result counts
            max_expected_increase: Max multiplier vs historical average (default: 10x)
            
        Returns:
            Tuple of (is_plausible, plausibility_score)
        """
        if not historical_row_counts:
            return True, 1.0
        
        avg_historical = statistics.mean(historical_row_counts)
        
        if avg_historical == 0:
            return True, 1.0
        
        multiplier = result_count / avg_historical if avg_historical > 0 else 1.0
        
        # Penalize if result is 10x+ larger than historical average
        if multiplier > max_expected_increase:
            score = 1.0 / multiplier  # Score proportional to how far over limit
            return False, max(0.0, min(1.0, score))
        elif multiplier < 0.1:
            # Also penalize if 90%+ lower than historical (likely query error)
            return False, multiplier
        
        return True, 1.0
    
    @staticmethod
    def calculate_result_plausibility(
        result_count: int,
        aggregate_values: Dict[str, float],
        historical_counts: List[int],
        historical_aggregates: Dict[str, List[float]]
    ) -> float:
        """
        Aggregate plausibility score from multiple dimensions.
        
        Args:
            result_count: Number of rows in result
            aggregate_values: Dict of aggregate metrics (SUM, AVG, etc.)
            historical_counts: List of historical result row counts
            historical_aggregates: Dict of historical aggregate values by key
            
        Returns:
            Overall plausibility score [0, 1]
        """
        # 50% weight on row count, 50% on aggregate values
        count_is_plausible, count_score = ResultPlausibilityCalculator.check_row_count_plausibility(
            result_count,
            historical_counts
        )
        
        # Calculate aggregate plausibility
        aggregate_scores = []
        for key, value in aggregate_values.items():
            if key in historical_aggregates:
                z_score = ResultPlausibilityCalculator.calculate_z_score_anomaly(
                    value,
                    historical_aggregates[key]
                )
                plaus = ResultPlausibilityCalculator.normalize_z_score_to_plausibility(z_score)
                aggregate_scores.append(plaus)
        
        if not aggregate_scores:
            aggregate_score = 1.0
        else:
            aggregate_score = sum(aggregate_scores) / len(aggregate_scores)
        
        return 0.5 * count_score + 0.5 * aggregate_score


class SemanticDriftMetric:
    """
    Main Semantic Drift Metric implementation.
    
    Combines three weighted components:
    - Intent Alignment (40%)
    - Constraint Adherence (30%)
    - Result Plausibility (30%)
    """
    
    def __init__(
        self,
        intent_weight: float = 0.4,
        constraint_weight: float = 0.3,
        plausibility_weight: float = 0.3,
        convergence_threshold: float = 0.15
    ):
        """
        Initialize drift metric with configurable weights.
        
        Args:
            intent_weight: Weight for intent alignment component
            constraint_weight: Weight for constraint adherence component
            plausibility_weight: Weight for result plausibility component
            convergence_threshold: Target drift score for convergence
        """
        total_weight = intent_weight + constraint_weight + plausibility_weight
        assert abs(total_weight - 1.0) < 0.01, "Weights must sum to 1.0"
        
        self.intent_weight = intent_weight
        self.constraint_weight = constraint_weight
        self.plausibility_weight = plausibility_weight
        self.convergence_threshold = convergence_threshold
        
        self.intent_calculator = IntentAlignmentCalculator()
        self.constraint_calculator = ConstraintAdherenceCalculator()
        self.plausibility_calculator = ResultPlausibilityCalculator()
    
    def calculate(
        self,
        extraction_confidences: Dict[str, float],
        mapping_similarities: List[float],
        constraints_list: List[Dict[str, Any]],
        result_count: int,
        aggregate_values: Dict[str, float],
        historical_counts: List[int],
        historical_aggregates: Dict[str, List[float]]
    ) -> DriftMetricComponents:
        """
        Calculate complete drift metric with all components.
        
        Args:
            extraction_confidences: Confidence scores from intent parser
            mapping_similarities: Similarity scores from ontology mapper
            constraints_list: List of validated constraints
            result_count: Number of rows in query result
            aggregate_values: Aggregate metrics (SUM, AVG, COUNT, etc.)
            historical_counts: Historical result row counts for baseline
            historical_aggregates: Historical aggregate values by key
            
        Returns:
            DriftMetricComponents with complete breakdown
        """
        # Calculate each component
        intent_align = self.intent_calculator.calculate_alignment_score(
            extraction_confidences,
            mapping_similarities
        )
        
        constraint_adhere = self.constraint_calculator.calculate_adherence_score(
            constraints_list
        )
        
        result_plaus = self.plausibility_calculator.calculate_result_plausibility(
            result_count,
            aggregate_values,
            historical_counts,
            historical_aggregates
        )
        
        # Composite drift score
        composite_drift = (
            self.intent_weight * (1 - intent_align) +
            self.constraint_weight * (1 - constraint_adhere) +
            self.plausibility_weight * (1 - result_plaus)
        )
        
        # Ensure within [0, 1] bounds
        composite_drift = max(0.0, min(1.0, composite_drift))
        
        return DriftMetricComponents(
            intent_alignment=intent_align,
            constraint_adherence=constraint_adhere,
            result_plausibility=result_plaus,
            composite_drift=composite_drift,
            timestamp=datetime.utcnow(),
            breakdown={
                "intent_alignment": {
                    "score": intent_align,
                    "weight": self.intent_weight,
                    "contribution": self.intent_weight * (1 - intent_align),
                },
                "constraint_adherence": {
                    "score": constraint_adhere,
                    "weight": self.constraint_weight,
                    "contribution": self.constraint_weight * (1 - constraint_adhere),
                    "violations": self.constraint_calculator.categorize_constraint_violations(constraints_list),
                },
                "result_plausibility": {
                    "score": result_plaus,
                    "weight": self.plausibility_weight,
                    "contribution": self.plausibility_weight * (1 - result_plaus),
                },
            }
        )
    
    def has_converged(self, drift_score: float) -> bool:
        """Check if drift score indicates convergence."""
        return drift_score <= self.convergence_threshold
    
    def get_status_message(self, drift_score: float) -> str:
        """Generate human-readable status message for drift score."""
        if drift_score < 0.05:
            return "EXCELLENT: Near-perfect query resolution"
        elif drift_score < 0.10:
            return "VERY GOOD: Minor intent/constraint misalignment"
        elif drift_score < 0.15:
            return "GOOD: Acceptable semantic drift (convergence)"
        elif drift_score < 0.25:
            return "ACCEPTABLE: Moderate drift, recommend review"
        elif drift_score < 0.50:
            return "CONCERNING: Significant misalignment detected"
        else:
            return "CRITICAL: Severe semantic drift, query unreliable"
