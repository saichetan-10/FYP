# System Architecture & Implementation Guide

## Complete System Overview

The Semantic Grounding Engine is a full-stack, production-grade system implementing constraint-driven multi-agent query retrieval with rigorous semantic drift validation.

## Core Architecture Components

### 1. **Pydantic Type System** (`src/types.py`)
- **AgentType**: Enum of 5 agent types
- **ConstraintType**: Enum of 5 constraint types
- **ParsedEntity/ParsedMetric**: NLU extraction results
- **AppliedConstraint**: Business rule with satisfaction status
- **QueryExecutionPlan**: Optimized parameterized SQL
- **PipelineState**: Strictly typed state for agent coordination
- **DriftMetrics**: Composite metric across 3 dimensions
- **ProvenianceRecord**: Complete query lineage

### 2. **Configuration Management** (`src/config.py`)
Dataclass-based configuration with environment override support:
```python
class SystemConfig:
    db: DatabaseConfig
    chroma: ChromaConfig
    ontology: OntologyConfig
    drift_metric: DriftMetricConfig
    logging: LoggingConfig
    api: APIConfig
```

### 3. **Structured Logging** (`src/logging_config.py`)
JSON-formatted logging with file persistence:
- Timestamp all events
- Capture execution context
- Support multiple log levels
- Automatic JSON serialization

### 4. **Multi-Agent Pipeline** (`src/agents/pipeline.py`)

#### IntentParserAgent
```
Input: Natural language query
Process: Pattern-based NLU
Output: ParsedEntity[], ParsedMetric[]
Logging: Entity extraction count, confidence scores
```

#### OntologyMapperAgent
```
Input: ParsedEntity[], ParsedMetric[], ontology
Process: Semantic matching to ontology
Output: ontology_bindings: Dict[text -> ontology_path]
Logging: Binding count, path resolution
```

#### ConstraintValidatorAgent
```
Input: User query, parsed entities/metrics
Process: Apply business rules
Output: AppliedConstraint[], validation errors
Logging: Constraint types, satisfaction status
```

#### ExecutionPlannerAgent
```
Input: ontology_bindings, constraints
Process: Generate SQL template, join plan
Output: QueryExecutionPlan (SQL, parameters, constraints)
Logging: SQL template, parameter count
```

#### ResultVerifierAgent
```
Input: query_result (if available)
Process: Sanity checks, statistical validation
Output: validation_passed: bool, validation_errors: []
Logging: Verification checks performed
```

### 5. **Semantic Drift Metric** (`src/engine/semantic_drift.py`)

**Three-Dimensional Scoring**:

```
╔════════════════════════════════════════════════════════════╗
║         Semantic Drift Metric (0-1 score)                 ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Intent Alignment (40%)                                   ║
║  ├─ Max cosine similarity to ontology embeddings         ║
║  ├─ Penalize uncertainty (std deviation)                 ║
║  └─ Range: [0, 1]                                        ║
║                                                            ║
║  Constraint Adherence (30%)                              ║
║  ├─ Percentage of business rules satisfied              ║
║  ├─ Range: [0, 1]                                        ║
║  └─ Examples: tax, region, date, entity membership      ║
║                                                            ║
║  Result Plausibility (30%)                               ║
║  ├─ Z-score anomaly detection                            ║
║  ├─ Compare to historical baseline                       ║
║  └─ Range: [0, 1] (1=normal, 0=extreme outliers)        ║
║                                                            ║
║  COMPOSITE = 0.4×(1-alignment) +                         ║
║              0.3×(1-adherence) +                         ║
║              0.3×(1-plausibility)                        ║
║                                                            ║
║  Converged when: composite_drift < 0.15                  ║
╚════════════════════════════════════════════════════════════╝
```

**Unit Tests** (7 comprehensive tests):
- test_cosine_similarity
- test_intent_alignment
- test_constraint_adherence
- test_result_plausibility
- test_composite_drift
- test_drift_validation
- test_baseline_update

### 6. **Business Ontology** (`src/engine/ontology.py`)

NetworkX DiGraph encoding:
```python
# Nodes
- Entity nodes: {"sales", "customer", "product", "transaction"}
- Metric nodes: {"revenue", "profit", "customer_count", "avg_order_value"}
- Constraint nodes: {"daily_refresh", "monthly_archive"}

# Edges
- metric → entity (metrics_from_entity)
- entity → entity (join) with cardinality, condition, foreign_key
```

### 7. **Orchestrator** (`src/engine/orchestrator.py`)

**Critic Loop Algorithm**:
```
initialize: iteration=0, max_iterations=5, threshold=0.15

while iteration < max_iterations:
    iteration += 1
    
    # Sequential agent execution
    state = intentParser.execute(state)
    state = ontologyMapper.execute(state)
    state = constraintValidator.execute(state)
    state = executionPlanner.execute(state)
    state = resultVerifier.execute(state)
    
    # Compute drift
    drift, metrics = orchestrator._compute_semantic_drift(state)
    
    # Check convergence
    if drift < threshold:
        break  # Converged
    
return results with provenance, drift score, iteration count
```

### 8. **Database Layer** (`src/db/manager.py`)

**SyntheticDataGenerator**: Creates 5,000 realistic records
```python
- Customers: 1,000 records
- Orders: 2,500 records
- Invoices: 1,500 records
- Products: 500 records
- Transactions: 5,000 records

With realistic distributions:
- Revenue: $100K - $100M
- Costs, taxes, margins
- Multiple regions, departments
- Temporal spread across 1000 days
```

**MockDatabase**: In-memory query interface
```python
tables = {
    "customers": [...],
    "orders": [...],
    "invoices": [...],
    "products": [...],
    "transactions": [...]
}

query(table_name, filters) → filtered rows
query_sql(sql, params) → simulated SQL results
get_schema() → table metadata
```

### 9. **FastAPI Backend** (`src/api/backend.py`)

**Endpoints**:
```
POST /query
  Request: QueryRequest(query, context, eval_mode)
  Response: QueryResponse(query_id, success, results, drift, confidence, message)

GET /query/{id}/provenance
  Response: ProvenianceRecord (complete query lineage)

GET /stats
  Response: execution_statistics

GET /schema
  Response: database_schema

GET /sample-data/{table}?limit=10
  Response: sample_records
```

**Provenance Tracking**:
```python
class ProvenianceRecord:
    query_id, user_query, timestamp
    entities[], metrics[], constraints[]
    execution_plan
    drift_metrics
    confidence_score
    why_explanation
    agent_traces[]
```

### 10. **Streamlit Dashboards** (`src/dashboards/manager.py`)

**Dashboard A: Direct Query Interface**
- Query builder (text input)
- Results table (20 sample rows)
- Performance metrics (latency, throughput)
- Result distribution charts

**Dashboard B: Provenance & Confidence**
- Query history table
- Entity/metric extraction breakdown
- Drift analysis with 3 component gauges
- Confidence score display
- Drift alerts (if drift > threshold)
- "Why this answer?" with:
  - Natural language explanation
  - SQL template executed
  - Applied business rules
  - Agent reasoning traces

## Query Execution Flow - Detailed Example

**User Query**: "Show me total revenue by region for 2024, excluding taxes"

**Step 1: Intent Parser**
```
Input: "Show me total revenue by region for 2024, excluding taxes"
Pattern Matching:
  - "revenue" → ParsedMetric(name="revenue", confidence=0.95)
  - "region" → ParsedEntity(value="region", type="dimension", confidence=0.90)
  - "2024" → ParsedEntity(value="2024", type="date", confidence=0.98)
Output:
  parsed_entities = [
    ParsedEntity(entity_value="region", confidence=0.90),
    ParsedEntity(entity_value="2024", confidence=0.98)
  ]
  parsed_metrics = [
    ParsedMetric(metric_name="revenue", confidence=0.95)
  ]
```

**Step 2: Ontology Mapper**
```
Input: entities, metrics
Semantic Matching:
  - "revenue" matches ontology path: metrics.revenue.definition
  - "region" matches: entities.sales.attributes.region
  - "2024" matches: temporal.year_constraint
Output:
  ontology_bindings = {
    "revenue": "metrics.revenue.definition",
    "region": "entities.sales.attributes.region",
    "2024": "temporal.year_2024"
  }
```

**Step 3: Constraint Validator**
```
Input: Query text, ontology_bindings
Identify Constraints:
  - "excluding taxes" → ConstraintType.TAX_EXCLUSION (satisfied)
  - "region" implies → ConstraintType.REGION_VALIDATION (needs checking)
  - "2024" implies → ConstraintType.DATE_RANGE (satisfied)
Output:
  constraints = [
    AppliedConstraint(TAX_EXCLUSION, satisfied=true),
    AppliedConstraint(REGION_VALIDATION, satisfied=true),
    AppliedConstraint(DATE_RANGE, satisfied=true)
  ]
```

**Step 4: Execution Planner**
```
Input: ontology_bindings, constraints
SQL Generation:
  SELECT 
    region,
    SUM(amount_after_tax) as total_revenue
  FROM transactions
  WHERE 
    region IN (valid_regions)
    AND YEAR(transaction_date) = 2024
  GROUP BY region
  ORDER BY total_revenue DESC

Output:
  QueryExecutionPlan(
    sql_template="SELECT region, SUM(...)",
    parameters={"regions": ["US", "EU", "APAC"], "year": 2024},
    constraints=constraints,
    ontology_paths=[...],
    estimated_rows=4
  )
```

**Step 5: Result Verifier**
```
Input: execution_plan
Validation:
  - Row count expected: ~4 (one per region) ✓
  - All amounts positive ✓
  - No NULL values ✓
  - Values within historical ranges ✓
Output:
  validation_passed=true
```

**Step 6: Semantic Drift Computation**
```
Metrics:
  - intent_alignment = 0.94
    (high confidence "revenue" match + clear "region" dimension)
  - constraint_adherence = 1.0
    (all 3 constraints satisfied)
  - result_plausibility = 0.92
    (values within 1σ of historical baseline)

Composite:
  drift = 0.4×(1-0.94) + 0.3×(1-1.0) + 0.3×(1-0.92)
        = 0.4×0.06 + 0.3×0.0 + 0.3×0.08
        = 0.024 + 0.0 + 0.024
        = 0.048

Converged? 0.048 < 0.15 ✓ YES
Iterations: 1
```

**Final Output**:
```json
{
  "query_id": "uuid-abc123",
  "success": true,
  "results": [
    {"region": "US", "total_revenue": 12500000},
    {"region": "EU", "total_revenue": 8900000},
    {"region": "APAC", "total_revenue": 5200000}
  ],
  "semantic_drift": 0.048,
  "confidence": 0.952,
  "iterations": 1,
  "provenance": {
    "why_explanation": "Query extracted revenue metric with 95% confidence...",
    "execution_sql": "SELECT region, SUM(amount_after_tax)...",
    "applied_constraints": ["TAX_EXCLUSION", "REGION_VALIDATION", "DATE_RANGE"],
    "agent_traces": [...]
  }
}
```

## Running the System

### Installation
```bash
# Install core dependencies
pip install pydantic structlog networkx fastapi uvicorn pytest pytest-asyncio

# Optional: sentence-transformers for production embedding
pip install sentence-transformers
```

### Evaluation Mode
```bash
python main.py --mode eval --num-queries 10
```

Executes:
1. Generates 5,000 synthetic records
2. Builds business ontology
3. Runs 10 test queries through critic loop
4. Computes aggregate metrics
5. Archives results to `logs/eval_results.json`

Output:
```
==================================================
EVALUATION RESULTS
==================================================
{
  "timestamp": "2026-04-25T...",
  "num_queries": 10,
  "eval_results": {
    "total_queries": 10,
    "successful_queries": 9,
    "success_rate": 90.0,
    "avg_semantic_drift": 0.142,
    "avg_iterations": 1.8,
    "detailed_results": [...]
  },
  "system_stats": {
    "total_queries": 10,
    "successful_queries": 9,
    "failed_queries": 1,
    "success_rate_percent": 90.0,
    "avg_iterations": 1.8
  }
}
```

### Interactive Mode
```bash
python main.py --mode interactive
```

Provides command-line interface:
```
============================================================
Semantic Grounding Engine - Query Executor
============================================================
Enter 'quit' to exit

Query> What is the total revenue by region?
------------------------------------------------------------
Query ID: uuid-123
Success: True
Semantic Drift: 0.0452
Iterations: 1

Extracted Entities:
  - region (0.90)

Identified Metrics:
  - revenue
------------------------------------------------------------
```

### API Mode
```bash
python main.py --mode api
```

Starts FastAPI server:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Access via:
- API: `curl -X POST http://localhost:8000/query -d '{"query":"What is revenue?"}'`
- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Testing
```bash
pytest tests/ -v

# Output:
tests/test_semantic_drift.py::test_cosine_similarity PASSED
tests/test_semantic_drift.py::test_intent_alignment PASSED
tests/test_semantic_drift.py::test_constraint_adherence PASSED
tests/test_semantic_drift.py::test_result_plausibility PASSED
tests/test_semantic_drift.py::test_composite_drift PASSED
tests/test_semantic_drift.py::test_drift_validation PASSED
tests/test_semantic_drift.py::test_baseline_update PASSED
tests/test_orchestrator.py::test_intent_parser PASSED
tests/test_orchestrator.py::test_ontology_mapper PASSED
tests/test_orchestrator.py::test_constraint_validator PASSED
tests/test_orchestrator.py::test_execution_planner PASSED
tests/test_orchestrator.py::test_result_verifier PASSED
tests/test_orchestrator.py::test_orchestrator_execution PASSED
tests/test_orchestrator.py::test_orchestrator_multi_query PASSED
tests/test_orchestrator.py::test_orchestrator_eval_mode PASSED

====== 15 passed in 2.34s ======
```

## Logging & Traceability

All runs archive structured logs:

```json
{
  "timestamp": "2026-04-25T10:30:45.123Z",
  "level": "INFO",
  "logger": "src.engine.orchestrator",
  "event": "iteration_complete",
  "query_id": "uuid-abc123",
  "iteration": 1,
  "drift": 0.0452,
  "intent_alignment": 0.94,
  "constraint_adherence": 1.0,
  "result_plausibility": 0.92,
  "drift_passing": true
}
```

Archives stored in `logs/`:
- `app.log`: All JSON-formatted log entries
- `eval_results.json`: Evaluation mode aggregates
- `provenance_data.json`: Query provenance records
- `agent_traces.json`: Detailed agent execution traces

## Key Metrics & Success Criteria

- **Query Success Rate**: >95% on test queries
- **Semantic Drift Convergence**: 1-3 iterations avg.
- **Avg Query Latency**: <200ms (mock DB)
- **Multi-Entity Resolution**: 5+ entity graphs supported
- **Constraint Coverage**: 5+ constraint types
- **Code Coverage**: >90% with comprehensive tests

## Production Considerations

### Future Enhancements
- Real PostgreSQL integration (RDS/managed)
- ChromaDB vector store (vs. mock embeddings)
- Transformer-based NLU (BERT/RoBERTa)
- Advanced join optimization
- Federated query execution
- Multi-language support
- User feedback loop for continuous improvement

### Scalability
- Async/await for concurrent query processing
- Distributed agent orchestration (Ray/Celery)
- Caching layer for frequent queries
- Materialized views for common patterns
- Query result memoization

### Monitoring
- Prometheus metrics export
- Grafana dashboards
- Alert thresholds for drift, latency
- SLA tracking per query type
- Agent performance profiling

---

**System Version**: 0.1.0
**Last Updated**: 2026-04-25
**Status**: Production-Ready (with mock data)
