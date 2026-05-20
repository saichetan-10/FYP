# Design and Implementation Report

## 1. Incorporation of Suggestions

### Key feedback from earlier phases
- Need to document project scope, architecture, and traceability clearly.
- Improve alignment between natural language input handling and SQL generation.
- Show how semantic drift is measured and reduced.
- Provide explicit mapping from requirements to components.
- Add more detail on implementation status and completed features.

### How suggestions were incorporated
- Added detailed architectural descriptions in `project_detailed_overview.md` and this report.
- Established a multi-agent pipeline with explicit agent responsibilities to improve semantic alignment.
- Implemented a semantic drift metric in `src/engine/semantic_drift.py` to quantify and control drift.
- Used a business ontology in `src/engine/ontology.py` to enforce rule-based validation and constraint adherence.
- Documented the system structure, inputs, outputs, and design decisions in source comments and project docs.

### Improvements made (before vs after)
- Before: Natural language queries were handled in a monolithic or unclear flow.
- After: Query processing now follows a structured pipeline of IntentParser, OntologyMapper, ConstraintValidator, ExecutionPlanner, and ResultVerifier.
- Before: No formal drift metric or convergence logic.
- After: Semantic drift is now computed and used to drive iterative refinement in `src/engine/orchestrator.py`.
- Before: Design documentation was minimal.
- After: Project now includes detailed architecture overview, module descriptions, and component traceability.

## 2. Level of Complexity

### Problem statement and complexity level
- The system must convert natural language queries into executable SQL while minimizing semantic drift.
- It must enforce business rules, validate outputs, and maintain provenance and auditability.
- Complexity is moderate to high due to the need for natural language understanding, ontology grounding, constraint validation, iterative refinement, and semantic scoring.

### Approach and solution
- Use a constraint-driven multi-agent architecture to break the problem into focused subprocesses.
- Define a business ontology representing entities, metrics, constraints, and join rules.
- Compute semantic drift through a composite metric of alignment, constraint adherence, and result plausibility.
- Iterate through query refinement until drift meets a threshold or a maximum number of iterations is reached.
- Provide API and evaluation modes for repeated testing and benchmarking.

### Innovative methods, algorithms, or techniques
- Multi-agent pipeline for separating intent parsing, ontology mapping, execution planning, and verification.
- Composite semantic drift metric with weighted components for intent alignment, constraint adherence, and result plausibility.
- Business ontology using a property graph to represent entities, metrics, temporal constraints, and valid joins.
- Critic-loop orchestration that refines query output based on drift measurement.

### Justification for complexity
- Natural language to SQL mapping is inherently ambiguous and requires semantic grounding.
- The project integrates language understanding, graph-based ontology mapping, business rule validation, and statistical plausibility checks.
- The iterative loop adds algorithmic complexity beyond one-shot translation.
- The design supports traceability and explainability, which strengthens the system non-functionally.

## 3. Detailed Design

### System architecture and component interactions
- User query enters the system through the API or CLI.
- `src/agents/pipeline.py` executes a sequence of agents:
  - `IntentParserAgent`
  - `OntologyMapperAgent`
  - `ConstraintValidatorAgent`
  - `ExecutionPlannerAgent`
  - `ResultVerifierAgent`
- `src/engine/ontology.py` provides structured business knowledge for grounding and validation.
- `src/engine/semantic_drift.py` computes drift metrics after query planning and execution.
- `src/engine/orchestrator.py` manages the critic loop and convergence logic.
- `src/db/manager.py` handles synthetic dataset creation, schema management, and query execution.
- `src/api/backend.py` exposes the query service and schema/status endpoints.

### Design representations
- The design is expressed through module decomposition and workflow descriptions rather than formal UML artifacts.
- Component responsibilities are mapped to source modules and classes.
- Data flow is defined through typed state objects in `src/agents/state.py` and Pydantic models in `src/types.py`.

### Module-wise design mapping
- `src/agents/pipeline.py`
  - Inputs: parsed natural language state, user query text
  - Outputs: validated query plan, SQL template, execution parameters
- `src/engine/ontology.py`
  - Inputs: extracted entities and metrics
  - Outputs: ontology mappings, validation results, join paths
- `src/engine/semantic_drift.py`
  - Inputs: query state, constraint results, execution outputs
  - Outputs: drift score, metric details, convergence decisions
- `src/engine/orchestrator.py`
  - Inputs: initial query request, system configuration
  - Outputs: final query result, drift history, provenance data
- `src/db/manager.py`
  - Inputs: SQL query and parameters
  - Outputs: query results, sample records, schema info
- `src/api/backend.py`
  - Inputs: API requests
  - Outputs: JSON responses, query execution provenance, system health data

### Data flow and processing design
- Natural language query → agent pipeline → ontology grounding → constraint validation → SQL generation → execution → drift evaluation.
- A typed `QueryState` object carries state across agents, and each agent updates state in sequence.
- The database layer stores synthetic data and returns results for verification.

### Interface and integration design
- FastAPI provides REST endpoints for query execution and system metadata.
- API models ensure typed request/response contracts.
- The orchestrator integrates pipeline agents with drift scoring and loop control.

### Key design decisions, assumptions, and constraints
- Decision: Use a modular agent pipeline for better traceability and maintainability.
- Decision: Represent business rules in an ontology to support validation and explainability.
- Assumption: Input queries can be resolved with ontology mapping and constraint grounding.
- Constraint: Iteration is bounded by a maximum loop count to avoid indefinite refinement.
- Constraint: The current implementation uses synthetic data for development and evaluation.

### Non-functional aspects
- Performance: Modular agents allow focused optimization and easier profiling.
- Scalability: Component separation enables future distribution of agents or microservices.
- Security: Input validation and typed models reduce the risk of malformed data.
- Maintainability: Clear module boundaries and documentation improve future extension.

### Traceability from SRS
- User query handling maps to the API and orchestrator modules.
- Semantic validation requirements map to ontology and drift metric components.
- Explainability and provenance map to state tracking in the agent pipeline and orchestrator.
- Business rule enforcement maps to `ConstraintValidatorAgent`.

## 4. Implementation Level

### Current implementation status
- Completed multi-agent pipeline in `src/agents/pipeline.py`.
- Completed business ontology management in `src/engine/ontology.py`.
- Completed semantic drift metric in `src/engine/semantic_drift.py`.
- Completed orchestrator with critic loop logic in `src/engine/orchestrator.py`.
- Completed FastAPI backend endpoints in `src/api/backend.py`.
- Completed synthetic data and database manager in `src/db/manager.py`.
- Unit and integration tests exist under `tests/`.

### Key functionalities with examples
- Query processing through agent pipeline and convergence control.
- Drift scoring across alignment, adherence, and plausibility.
- Business ontology mapping and constraint checking.
- SQL execution against synthetic data.
- API support for query execution and schema metadata.

### Translation from design to implementation
- Each pipeline agent implements a discrete stage from the design.
- The ontology layer enforces rules and provides structured domain semantics.
- The drift metric is directly derived from the described composite scoring model.
- The orchestrator executes the workflow and manages iterative refinement.

### Tools, technologies, and environment used
- Python 3.12 in `venv_new`
- FastAPI for REST API
- NetworkX for ontology graph modeling
- Pydantic for typed state and model validation
- pytest for automated testing
- Docker support available in `docker/`
- Project dependency management via `requirements.txt`

### Module integration and system working
- API requests flow into the orchestrator, which runs the pipeline and drift evaluation.
- The database manager executes queries and returns results for verification.
- Drift metrics and provenance are attached to final responses.
- The system is structured for end-to-end query processing from NL input to SQL result.

## 5. Summary

This document summarizes how early feedback was incorporated, describes project complexity, explains detailed design decisions, and presents the current implementation status. The repository now supports a traceable, agent-based solution for minimizing semantic drift in text-to-SQL systems.
