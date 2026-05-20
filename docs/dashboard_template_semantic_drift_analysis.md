# Dashboard Template: Semantic Drift Analysis

## Purpose
This dashboard visualizes the semantic drift metric and its component breakdown, helping stakeholders understand query quality, confidence, and areas of semantic loss during execution.

## Layout

### Header
- Title: `Semantic Drift Analysis Dashboard`
- Subtitle: `Monitoring query drift, validation, and output plausibility`
- Run stamp or dashboard refresh time

### Section 1: Drift Snapshot
- Overall semantic drift score card
- Component cards:
  - Intent Alignment
  - Constraint Adherence
  - Result Plausibility
- Confidence status: `High`, `Moderate`, `Low`
- Drift alert indicator if score exceeds threshold

### Section 2: Component Breakdown
A grouped panel showing each drift component with gauges or progress bars.

#### Intent Alignment
- Similarity percentage
- Confidence interval
- Top matched ontology paths
- Notes on ambiguous mappings

#### Constraint Adherence
- Percentage of constraints satisfied
- Total constraints applied
- List of any violations
- Types of constraints triggered

#### Result Plausibility
- Z-score range
- Historical baseline comparison
- Anomaly flag
- Sample plausibility metrics (e.g. expected row count vs actual)

### Section 3: Drift History and Trends
- Line chart: Drift score over time or over iterations
- Bar chart: Component scores over past queries
- Table: Recent queries with drift, status, and confidence

### Section 4: Query Provenance & Explanation
- Query text
- Executed SQL statement
- Key extracted entities / metrics
- Applied business rules
- Explanation block: `Why this answer?`
- Agent traces summary

### Section 5: Performance and Reliability
- Query execution time distribution
- Average drift by query category
- Top error or violation types
- System health indicators (throughput, success rate)

## Recommended Visuals
- Gauge charts for each drift component
- Line chart for drift convergence over time
- Heatmap or bar chart of frequent constraint violations
- Table of recent query provenance and drift status

## Notes for Presentation
- Use this dashboard to communicate system trustworthiness.
- Demonstrate how low drift corresponds to higher confidence and more stable query outputs.
- Point out how the component breakdown helps diagnose semantic failures.
- Reserve the detailed provenance panel for after the summary metrics.
