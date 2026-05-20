# Semantic Drift Metric - Detailed Formulation

## Overview

The Semantic Drift Metric is a rigorous, unit-tested Python class that computes a composite 0-1 score measuring divergence between user intent and system output across three dimensions.

## Components

### 1. Intent Alignment (40% weight)

**Definition**: Cosine similarity between query embedding and ontology paths

$$\text{alignment} = \max_{\text{paths}} \cos(\text{query}, \text{path}) \times \left(1 - \frac{\sigma(\text{sims})}{1 + \sigma(\text{sims})}\right)$$

where:
- $\cos(\cdot)$ = cosine similarity
- $\sigma(\text{sims})$ = standard deviation of all path similarities
- The penalization term ensures confidence when matches are clustered

**Implementation**:
```python
similarities = [cosine_similarity(query_emb, path_emb) for path_emb in ontology_embeddings]
max_similarity = max(similarities)
std_similarity = std(similarities)
alignment = max_similarity * (1 - std_norm)
```

**Interpretation**:
- 1.0 = Query perfectly aligns with single ontology path
- 0.5 = Query moderately aligns with paths (scattered matches)
- 0.0 = Query completely misaligned

### 2. Constraint Adherence (30% weight)

**Definition**: Percentage of business rules satisfied

$$\text{adherence} = \frac{\text{satisfied}}{\text{total}}$$

where:
- Constraint types: tax exclusion, region validation, date ranges, entity membership, metric bounds
- Each constraint returns satisfied/unsatisfied boolean

**Example Constraints**:
- Tax Exclusion: "Is tax_amount properly excluded from revenue?"
- Region Validation: "Are only valid regions included?"
- Date Range: "Do results fall within specified period?"

**Interpretation**:
- 1.0 = All applicable rules satisfied
- 0.5 = Half of rules satisfied
- 0.0 = No rules satisfied

### 3. Result Plausibility (30% weight)

**Definition**: Z-score based deviation from historical distribution

$$\text{plausibility} = \frac{1}{1 + z_{\max} / \tau}$$

where:
- $z_i = \frac{x_i - \mu_{\text{baseline}}}{\sigma_{\text{baseline}}}$
- $z_{\max} = \max(|z_i|)$
- $\tau = 3.0$ (z-score threshold)

**Statistical Detection**:
- Maintains baseline (mean, std) for each metric type
- Compares results against historical distribution
- Flags statistical anomalies

**Interpretation**:
- 1.0 = All results within 1σ of baseline
- 0.5 = Max outlier at ~3σ from baseline
- 0.0 = Extreme outliers (>6σ)

## Composite Drift Metric

**Formula**:
$$\text{drift} = w_i (1 - a_i) + w_c (1 - a_c) + w_p (1 - a_p)$$

where:
- $a_i, a_c, a_p$ are alignment, adherence, plausibility scores
- $w_i=0.4, w_c=0.3, w_p=0.3$ (configurable)

**Clamped to [0, 1]**:
$$\text{drift} = \text{clip}(\text{drift}, 0.0, 1.0)$$

**Passing Criterion**:
$$\text{pass} = \text{drift} < 0.15 \text{ (configurable threshold)}$$

## Unit Tests

The implementation includes comprehensive unit tests:

1. **test_cosine_similarity**: Validates similarity computation
2. **test_intent_alignment**: Tests alignment with known embeddings
3. **test_constraint_adherence**: Tests constraint satisfaction logic
4. **test_result_plausibility**: Tests z-score and anomaly detection
5. **test_composite_drift**: Tests weighted combination
6. **test_drift_validation**: Tests threshold and iteration logic
7. **test_baseline_update**: Tests historical statistics management

## Example Computations

### Query: "What is 2024 revenue by region excluding taxes?"

**Intent Alignment**:
- Query embedding matched to ontology paths
- "revenue" path: 0.92 similarity
- "tax_exclusion" rule: 0.88 similarity
- Mean: 0.90, Std: 0.02
- Alignment = 0.92 * (1 - 0.02/1.02) ≈ 0.90

**Constraint Adherence**:
- Tax Exclusion: satisfied ✓
- Region Validation: satisfied ✓
- Date Range (2024): satisfied ✓
- Adherence = 3/3 = 1.0

**Result Plausibility**:
- Results: [1.2M, 1.3M, 1.1M, 1.4M]
- Baseline: μ=1.0M, σ=0.2M
- Z-scores: [1.0, 1.5, 0.5, 2.0]
- Max z-score: 2.0
- Plausibility = 1/(1 + 2.0/3.0) ≈ 0.60

**Composite Drift**:
- drift = 0.4(1-0.90) + 0.3(1-1.0) + 0.3(1-0.60)
- drift = 0.04 + 0.0 + 0.12 = 0.16

**Result**: Drift = 0.16 > 0.15 threshold → Continue critic loop

## Critic Loop Strategy

The orchestrator iterates agents while drift > threshold:

1. **Iteration 1**: Initial parsing → drift = 0.25 → High
2. **Iteration 2**: Refined mapping → drift = 0.18 → Still high
3. **Iteration 3**: Constraint application → drift = 0.14 → Passed!
4. **Convergence**: Return results after 3 iterations

## Performance Characteristics

- **Computation**: O(n_entities × n_metrics) for embeddings
- **Memory**: O(n_historical) for baseline statistics
- **Latency**: ~5-10ms per drift computation
- **Convergence**: 1-3 iterations for well-formed queries

## Configuration

```python
config.drift_metric.intent_alignment_weight = 0.4
config.drift_metric.constraint_adherence_weight = 0.3
config.drift_metric.result_plausibility_weight = 0.3
config.drift_metric.drift_threshold = 0.15
config.drift_metric.z_score_threshold = 3.0
```
