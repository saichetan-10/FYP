"""
Comprehensive test suite for semantic drift metric and constraints.

Tests the mathematical correctness of the drift metric and constraint validation.
"""

import pytest
from src.engine.semantic_drift import (
    SemanticDriftMetric,
    IntentAlignmentCalculator,
    ConstraintAdherenceCalculator,
    ResultPlausibilityCalculator,
)


class TestIntentAlignmentCalculator:
    """Test intent alignment component (40% weight)."""
    
    def test_cosine_similarity_identical_vectors(self):
        """Identical vectors should have similarity = 1.0"""
        vec = [1.0, 0.0, 0.0]
        similarity = IntentAlignmentCalculator.calculate_embedding_similarity(vec, vec)
        assert similarity == pytest.approx(1.0, abs=0.01)
    
    def test_cosine_similarity_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity = 0.0"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = IntentAlignmentCalculator.calculate_embedding_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, abs=0.01)
    
    def test_cosine_similarity_opposite_vectors(self):
        """Opposite vectors should have similarity = -1.0"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = IntentAlignmentCalculator.calculate_embedding_similarity(vec1, vec2)
        assert similarity == pytest.approx(-1.0, abs=0.01)
    
    def test_alignment_score_with_high_confidence(self):
        """High confidence extractions should result in high alignment"""
        confidences = {"entity1": 0.95, "entity2": 0.92}
        similarities = [0.90, 0.88]
        alignment = IntentAlignmentCalculator.calculate_alignment_score(confidences, similarities)
        assert alignment > 0.85
        assert alignment <= 1.0
    
    def test_alignment_score_with_low_confidence(self):
        """Low confidence extractions should result in low alignment"""
        confidences = {"entity1": 0.60, "entity2": 0.55}
        similarities = [0.65, 0.60]
        alignment = IntentAlignmentCalculator.calculate_alignment_score(confidences, similarities)
        assert alignment < 0.70
    
    def test_alignment_score_empty_inputs(self):
        """Empty inputs should return 0.0"""
        alignment = IntentAlignmentCalculator.calculate_alignment_score({}, [])
        assert alignment == 0.0


class TestConstraintAdherenceCalculator:
    """Test constraint adherence component (30% weight)."""
    
    def test_adherence_all_satisfied(self):
        """All satisfied constraints should give adherence = 1.0"""
        constraints = [
            {"is_satisfied": True},
            {"is_satisfied": True},
            {"is_satisfied": True},
        ]
        adherence = ConstraintAdherenceCalculator.calculate_adherence_score(constraints)
        assert adherence == pytest.approx(1.0)
    
    def test_adherence_none_satisfied(self):
        """No satisfied constraints should give adherence = 0.0"""
        constraints = [
            {"is_satisfied": False},
            {"is_satisfied": False},
            {"is_satisfied": False},
        ]
        adherence = ConstraintAdherenceCalculator.calculate_adherence_score(constraints)
        assert adherence == pytest.approx(0.0)
    
    def test_adherence_partial_satisfaction(self):
        """Partial satisfaction should be proportional"""
        constraints = [
            {"is_satisfied": True},
            {"is_satisfied": True},
            {"is_satisfied": False},
        ]
        adherence = ConstraintAdherenceCalculator.calculate_adherence_score(constraints)
        assert adherence == pytest.approx(2.0 / 3.0, abs=0.01)
    
    def test_adherence_empty_constraints(self):
        """Empty constraints should give perfect adherence"""
        adherence = ConstraintAdherenceCalculator.calculate_adherence_score([])
        assert adherence == pytest.approx(1.0)
    
    def test_adherence_with_explicit_count(self):
        """Explicit satisfied count should override calculation"""
        constraints = [
            {"is_satisfied": True},
            {"is_satisfied": False},
            {"is_satisfied": False},
        ]
        adherence = ConstraintAdherenceCalculator.calculate_adherence_score(
            constraints, satisfied_count=2
        )
        assert adherence == pytest.approx(2.0 / 3.0, abs=0.01)


class TestResultPlausibilityCalculator:
    """Test result plausibility component (30% weight)."""
    
    def test_z_score_at_mean(self):
        """Value at mean should have Z-score = 0"""
        historical = [100.0, 100.0, 100.0]
        z_score = ResultPlausibilityCalculator.calculate_z_score_anomaly(100.0, historical)
        assert z_score == pytest.approx(0.0, abs=0.01)
    
    def test_z_score_one_std_above(self):
        """Value at mean + 1*std should have Z-score ≈ 1.0"""
        historical = [100.0, 105.0, 95.0]  # std ≈ 5
        mean = 100.0
        z_score = ResultPlausibilityCalculator.calculate_z_score_anomaly(105.0, historical)
        assert z_score > 0.9  # Approximately 1.0
    
    def test_z_score_normalization(self):
        """Z-score normalization should be between 0-1"""
        # Z <= 2 -> 1.0
        assert ResultPlausibilityCalculator.normalize_z_score_to_plausibility(0) == 1.0
        assert ResultPlausibilityCalculator.normalize_z_score_to_plausibility(2.0) == 1.0
        
        # Z = 3 -> 0.5
        assert ResultPlausibilityCalculator.normalize_z_score_to_plausibility(3.0) == pytest.approx(0.5)
        
        # Z >= 4 -> 0.0
        assert ResultPlausibilityCalculator.normalize_z_score_to_plausibility(4.0) == 0.0
        assert ResultPlausibilityCalculator.normalize_z_score_to_plausibility(5.0) == 0.0
    
    def test_row_count_plausibility_within_range(self):
        """Row count within historical range should be plausible"""
        result_count = 150
        historical = [100, 200, 120, 180]
        is_plausible, score = ResultPlausibilityCalculator.check_row_count_plausibility(
            result_count, historical
        )
        assert is_plausible is True
        assert score > 0.8
    
    def test_row_count_plausibility_extreme_high(self):
        """Row count 10x+ above average should be implausible"""
        result_count = 1500
        historical = [100, 120, 110, 130]  # avg ≈ 115
        is_plausible, score = ResultPlausibilityCalculator.check_row_count_plausibility(
            result_count, historical
        )
        assert is_plausible is False
        assert score < 0.2
    
    def test_row_count_plausibility_extreme_low(self):
        """Row count 90%+ below average should be implausible"""
        result_count = 5
        historical = [100, 120, 110, 130]  # avg ≈ 115
        is_plausible, score = ResultPlausibilityCalculator.check_row_count_plausibility(
            result_count, historical
        )
        assert is_plausible is False
        assert score < 0.15


class TestSemanticDriftMetric:
    """Integration tests for complete semantic drift metric."""
    
    def test_drift_perfect_scenario(self):
        """Perfect alignment, all constraints, plausible results = low drift"""
        metric = SemanticDriftMetric()
        drift = metric.calculate(
            extraction_confidences={"entity": 0.99, "metric": 0.98},
            mapping_similarities=[0.98, 0.97],
            constraints_list=[
                {"is_satisfied": True},
                {"is_satisfied": True},
            ],
            result_count=150,
            aggregate_values={},
            historical_counts=[100, 200, 120, 180],
            historical_aggregates={},
        )
        assert drift.composite_drift < 0.10
        assert metric.has_converged(drift.composite_drift)
    
    def test_drift_poor_scenario(self):
        """Low alignment, failed constraints, implausible = high drift"""
        metric = SemanticDriftMetric()
        drift = metric.calculate(
            extraction_confidences={"entity": 0.55, "metric": 0.60},
            mapping_similarities=[0.50, 0.55],
            constraints_list=[
                {"is_satisfied": False},
                {"is_satisfied": False},
                {"is_satisfied": True},
            ],
            result_count=2000,
            aggregate_values={},
            historical_counts=[100, 200, 120, 180],
            historical_aggregates={},
        )
        assert drift.composite_drift > 0.40
        assert not metric.has_converged(drift.composite_drift)
    
    def test_drift_convergence_threshold(self):
        """Drift < 0.15 should trigger convergence"""
        metric = SemanticDriftMetric(convergence_threshold=0.15)
        
        # Just above threshold
        assert not metric.has_converged(0.16)
        
        # At threshold
        assert metric.has_converged(0.15)
        
        # Well below threshold
        assert metric.has_converged(0.05)
    
    def test_drift_custom_weights(self):
        """Custom weights should be applied correctly"""
        metric = SemanticDriftMetric(
            intent_weight=0.5,
            constraint_weight=0.3,
            plausibility_weight=0.2
        )
        assert metric.intent_weight == 0.5
        assert metric.constraint_weight == 0.3
        assert metric.plausibility_weight == 0.2
    
    def test_drift_weights_sum_to_one(self):
        """Weights must sum to 1.0"""
        with pytest.raises(AssertionError):
            SemanticDriftMetric(
                intent_weight=0.4,
                constraint_weight=0.3,
                plausibility_weight=0.2  # Sum = 0.9, not 1.0
            )
    
    def test_drift_status_messages(self):
        """Status messages should reflect drift levels"""
        metric = SemanticDriftMetric()
        
        assert "EXCELLENT" in metric.get_status_message(0.03)
        assert "VERY GOOD" in metric.get_status_message(0.08)
        assert "GOOD" in metric.get_status_message(0.12)
        assert "ACCEPTABLE" in metric.get_status_message(0.18)
        assert "CONCERNING" in metric.get_status_message(0.35)
        assert "CRITICAL" in metric.get_status_message(0.75)
    
    def test_drift_bounded_output(self):
        """Drift should always be in [0, 1]"""
        metric = SemanticDriftMetric()
        
        # Test with extreme inputs
        drift = metric.calculate(
            extraction_confidences={},
            mapping_similarities=[],
            constraints_list=[],
            result_count=0,
            aggregate_values={},
            historical_counts=[],
            historical_aggregates={},
        )
        
        assert 0.0 <= drift.composite_drift <= 1.0
        assert 0.0 <= drift.intent_alignment <= 1.0
        assert 0.0 <= drift.constraint_adherence <= 1.0
        assert 0.0 <= drift.result_plausibility <= 1.0


class TestDriftMetricBreakdown:
    """Test the detailed breakdown and component contributions."""
    
    def test_breakdown_has_all_components(self):
        """Breakdown should contain all three components"""
        metric = SemanticDriftMetric()
        drift = metric.calculate(
            extraction_confidences={"entity": 0.9},
            mapping_similarities=[0.85],
            constraints_list=[{"is_satisfied": True}],
            result_count=150,
            aggregate_values={},
            historical_counts=[100, 200, 150],
            historical_aggregates={},
        )
        
        assert "intent_alignment" in drift.breakdown
        assert "constraint_adherence" in drift.breakdown
        assert "result_plausibility" in drift.breakdown
    
    def test_breakdown_shows_contributions(self):
        """Breakdown should show weighted contributions"""
        metric = SemanticDriftMetric(
            intent_weight=0.4,
            constraint_weight=0.3,
            plausibility_weight=0.3
        )
        drift = metric.calculate(
            extraction_confidences={"entity": 0.8},
            mapping_similarities=[0.8],
            constraints_list=[{"is_satisfied": True}],
            result_count=150,
            aggregate_values={},
            historical_counts=[100, 200, 150],
            historical_aggregates={},
        )
        
        # Contributions should be: weight * (1 - component)
        intent_contrib = drift.breakdown["intent_alignment"]["contribution"]
        constraint_contrib = drift.breakdown["constraint_adherence"]["contribution"]
        plaus_contrib = drift.breakdown["result_plausibility"]["contribution"]
        
        # Should sum to composite drift
        total_contrib = intent_contrib + constraint_contrib + plaus_contrib
        assert total_contrib == pytest.approx(drift.composite_drift, abs=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
