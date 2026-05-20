"""Type definitions and Pydantic models for the system."""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

# Try to import real pydantic, fall back to mock
try:
    from pydantic import BaseModel, Field
except ImportError:
    import sys
    sys.path.insert(0, '..')
    from mock_pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents in the pipeline."""

    INTENT_PARSER = "intent_parser"
    ONTOLOGY_MAPPER = "ontology_mapper"
    CONSTRAINT_VALIDATOR = "constraint_validator"
    EXECUTION_PLANNER = "execution_planner"
    RESULT_VERIFIER = "result_verifier"


class ConstraintType(str, Enum):
    """Types of constraints in the system."""

    TAX_EXCLUSION = "tax_exclusion"
    REGION_VALIDATION = "region_validation"
    DATE_RANGE = "date_range"
    METRIC_RANGE = "metric_range"
    ENTITY_MEMBERSHIP = "entity_membership"


class ParsedEntity(BaseModel):
    """Extracted entity from natural language query."""

    entity_type: str
    entity_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    aliases: List[str] = Field(default_factory=list)


class ParsedMetric(BaseModel):
    """Extracted metric from natural language query."""

    metric_name: str
    metric_definition: str
    aggregation_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class AppliedConstraint(BaseModel):
    """Applied constraint in query execution."""

    constraint_type: ConstraintType
    description: str
    parameters: Dict[str, Any]
    satisfied: bool


class QueryExecutionPlan(BaseModel):
    """Execution plan compiled by the Execution Planner agent."""

    query_id: str
    ontology_paths: List[str]
    sql_template: str
    parameters: Dict[str, Any]
    constraints: List[AppliedConstraint]
    estimated_rows: int


class QueryResult(BaseModel):
    """Result set from query execution."""

    result_id: str = ""
    query_id: str = ""
    sql_executed: str = ""
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    query_time_ms: float = 0.0
    data: List[Dict[str, Any]] = Field(default_factory=list)
    success: bool = True


class AgentMessage(BaseModel):
    """Message passed between agents in the pipeline."""

    sender: AgentType
    recipient: Optional[AgentType] = None
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PipelineState(BaseModel):
    """Typed state object for LangGraph pipeline."""

    query_id: str
    user_query: str
    parsed_entities: List[ParsedEntity] = Field(default_factory=list)
    parsed_metrics: List[ParsedMetric] = Field(default_factory=list)
    ontology_bindings: Dict[str, str] = Field(default_factory=dict)
    constraints: List[AppliedConstraint] = Field(default_factory=list)
    execution_plan: Optional[QueryExecutionPlan] = None
    query_result: Optional[QueryResult] = None
    agent_messages: List[AgentMessage] = Field(default_factory=list)
    semantic_drift: float = 0.0
    validation_passed: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 5


class DriftMetrics(BaseModel):
    """Computed semantic drift metrics."""

    intent_alignment: float = Field(ge=0.0, le=1.0)
    constraint_adherence: float = Field(ge=0.0, le=1.0)
    result_plausibility: float = Field(ge=0.0, le=1.0)
    composite_drift: float = Field(ge=0.0, le=1.0)
    components: Dict[str, Any] = Field(default_factory=dict)
    passing_threshold: bool


class ProvenianceRecord(BaseModel):
    """Complete record of query provenance for dashboard display."""

    query_id: str
    user_query: str
    timestamp: datetime
    entities: List[ParsedEntity]
    metrics: List[ParsedMetric]
    applied_constraints: List[AppliedConstraint]
    execution_plan: QueryExecutionPlan
    drift_metrics: DriftMetrics
    result_row_count: int
    confidence_score: float
    why_explanation: str
    agent_traces: List[AgentMessage]


class QueryRequest(BaseModel):
    """API request for query execution."""

    query: str
    context: Optional[Dict[str, Any]] = None
    eval_mode: bool = False


class QueryResponse(BaseModel):
    """API response with query results and metadata."""

    query_id: str
    success: bool
    results: Optional[List[Dict[str, Any]]] = None
    drift_score: float
    confidence: float
    message: str
    provenance_id: Optional[str] = None
