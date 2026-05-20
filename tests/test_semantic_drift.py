"""Unit tests for Semantic Drift Metric."""

import pytest
from src.engine.semantic_drift_pure import SemanticDriftMetric
from src.types import DriftMetrics


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    metric = SemanticDriftMetric()

    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    sim = metric._cosine_similarity(vec1, vec2)
    assert sim == pytest.approx(1.0)

    vec3 = [1.0, 0.0, 0.0]
    vec4 = [0.0, 1.0, 0.0]
    sim2 = metric._cosine_similarity(vec3, vec4)
    assert sim2 == pytest.approx(0.0)


def test_intent_alignment():
    """Test intent alignment computation."""
    metric = SemanticDriftMetric()

    query_emb = [1.0, 0.0, 0.0]
    onto_embs = [
        [1.0, 0.0, 0.0],
        [0.9, 0.1, 0.0],
        [0.8, 0.2, 0.0],
    ]

    alignment, details = metric.compute_intent_alignment(query_emb, onto_embs, [])

    assert 0.0 <= alignment <= 1.0
    assert "max_similarity" in details
    assert "mean_similarity" in details
    assert details["num_paths_evaluated"] == 3


def test_constraint_adherence():
    """Test constraint adherence computation."""
    metric = SemanticDriftMetric()

    # All constraints satisfied
    adherence, details = metric.compute_constraint_adherence(10, 10)
    assert adherence == 1.0

    # Half constraints satisfied
    adherence2, details2 = metric.compute_constraint_adherence(10, 5)
    assert adherence2 == 0.5

    # No constraints required
    adherence3, details3 = metric.compute_constraint_adherence(0, 0)
    assert adherence3 == 1.0


def test_result_plausibility():
    """Test result plausibility computation."""
    metric = SemanticDriftMetric()

    # Normal distribution
    results = [100.0, 105.0, 95.0, 110.0, 90.0]
    plausibility, details = metric.compute_result_plausibility(results, "test_metric")

    assert 0.0 <= plausibility <= 1.0
    assert "max_z_score" in details
    assert "baseline_mean" in details

    # Outlier detection
    results_with_outlier = [100.0, 105.0, 95.0, 1000.0]  # Large outlier
    plausibility2, details2 = metric.compute_result_plausibility(results_with_outlier, "test_outlier")

    assert plausibility2 < plausibility  # Lower plausibility with outlier


def test_composite_drift():
    """Test composite drift computation."""
    metric = SemanticDriftMetric()

    alignment = 0.85
    adherence = 0.90
    plausibility = 0.95

    drift, metrics = metric.compute_composite_drift(alignment, adherence, plausibility)

    assert isinstance(metrics, DriftMetrics)
    assert 0.0 <= drift <= 1.0
    assert metrics.intent_alignment == alignment
    assert metrics.constraint_adherence == adherence
    assert metrics.result_plausibility == plausibility


def test_drift_validation():
    """Test drift threshold validation."""
    metric = SemanticDriftMetric()

    # Drift below threshold
    should_continue, reason = metric.validate_drift_threshold(0.1, 1, 5)
    assert should_continue is False

    # Drift above threshold, not max iterations
    should_continue2, reason2 = metric.validate_drift_threshold(0.5, 1, 5)
    assert should_continue2 is True

    # Max iterations reached
    should_continue3, reason3 = metric.validate_drift_threshold(0.5, 5, 5)
    assert should_continue3 is False


def test_baseline_update():
    """Test baseline statistics update."""
    metric = SemanticDriftMetric()

    historical = [100.0, 110.0, 90.0, 105.0]
    metric.update_baseline("test_metric", historical)

    baseline = metric.get_baseline("test_metric")
    assert baseline is not None
    assert "mean" in baseline
    assert "std" in baseline
    assert baseline["mean"] == pytest.approx(101.25)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
