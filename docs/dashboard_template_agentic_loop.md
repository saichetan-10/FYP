# Dashboard Template: Agentic Loop Overview

## Purpose
This dashboard is designed to demonstrate the agentic loop in the system, showing how each agent processes a natural language query, how state flows between agents, and how the system converges on a final SQL execution plan.

## Layout

### Header
- Title: `Agentic Loop Dashboard`
- Subtitle: `Visualizing the sequential pipeline and convergence of the query processing workflow`
- Date/Run stamp

### Section 1: Query Input & Summary
- Free-text query input box
- `Execute Query` button
- Summary cards:
  - Query ID
  - Query status (In progress / Completed / Failed)
  - Iteration count
  - Final drift score
  - Confidence rating

### Section 2: Agent Sequence Overview
A horizontal or vertical step tracker showing the five agents in order:
1. `IntentParserAgent`
2. `OntologyMapperAgent`
3. `ConstraintValidatorAgent`
4. `ExecutionPlannerAgent`
5. `ResultVerifierAgent`

For each agent, display:
- Current status badge (`Success`, `Warning`, `Failed`)
- Execution time
- Key outputs
- Notes (e.g. extracted entities, mapped ontology paths, constraint violations)

### Section 3: Agent Detail Panels
Tabbed or expandable cards for each agent.

#### IntentParserAgent
- Extracted entities
- Parsed metrics
- Detected filters
- Confidence scores

#### OntologyMapperAgent
- Ontology targets
- Similarity scores
- Resolved synonyms
- Mapped schema elements

#### ConstraintValidatorAgent
- Applied business rules
- Validation results
- Pass/fail status per constraint
- Notes on constraint fixes

#### ExecutionPlannerAgent
- Planned SQL template
- Join plan / entity relationships
- Execution parameters

#### ResultVerifierAgent
- Result sanity checks
- Plausibility assessments
- Anomaly detection flags

### Section 4: State Transition Diagram
- A small workflow diagram or table describing state propagation between agents.
- Columns:
  - Agent name
  - Input state
  - Output state
  - Next agent

### Section 5: Final Execution Output
- Executed SQL query
- Result sample table
- Execution metrics:
  - Rows returned
  - Execution time (ms)
  - Throughput

### Section 6: Convergence and Loop Metrics
- Iterations graph showing drift score per iteration
- Convergence indicator: `Converged` / `No convergence`
- Maximum allowed iterations
- Final drift threshold

## Recommended Visuals
- Process flow chart for agent stages
- Iteration vs drift score line chart
- Agent status cards with color-coded success indicators
- Data table for a sample query result

## Notes for Presentation
- Use the dashboard to show the dynamic behavior of the critic loop.
- Emphasize how each agent adds validation or correction to the query.
- Highlight the final convergence criteria and how the system decides completion.
- Keep the design clean and consistent with the overall project branding.
