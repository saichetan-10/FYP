"""
FastAPI Backend: Production-Grade NL Query API

Provides:
- RESTful endpoints for natural language queries
- Request validation and error handling
- Complete provenance trail generation
- Structured response with confidence scores
- Health checks and monitoring
"""

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Deque
from datetime import datetime, timezone
from collections import deque
import os
import threading
import time
import json
import logging

from src.agents.pipeline import AgentPipeline
from src.engine.ontology import BusinessOntology
from src.db.manager import DatabaseManager, DatabaseConfig

# ── Module-level query log (thread-safe) ──────────────────────────────────────
_query_log: Deque[Dict[str, Any]] = deque(maxlen=1000)
_log_lock = threading.Lock()
_start_time = datetime.now(timezone.utc)


# ============================================================================
# Pydantic Models for API
# ============================================================================


class QueryRequest(BaseModel):
    """Natural language query request."""
    query: str = Field(..., description="Natural language data retrieval query")
    database: str = Field(default="sales", description="Target database (sales/inventory/analytics)")
    max_iterations: int = Field(default=5, description="Max refinement iterations")


class ConfidenceScore(BaseModel):
    """Confidence metric for result."""
    intent_alignment: float = Field(description="How well NL intent was understood")
    constraint_adherence: float = Field(description="Business rules satisfied %")
    result_plausibility: float = Field(description="Statistical plausibility score")
    composite_drift: float = Field(description="Overall semantic drift score")


class QueryResponse(BaseModel):
    """Complete query response with provenance."""
    query_id: str
    user_query: str
    status: str  # "success", "partial", "error"
    
    # Results
    results: List[Dict[str, Any]]
    result_count: int
    
    # Quality metrics
    confidence: ConfidenceScore
    execution_time_ms: float
    
    # Provenance trail
    explanation: str  # Plain English "why this answer"
    agent_trace: List[Dict[str, Any]]  # Complete agent handoff log
    
    # Debugging
    final_query: Optional[str] = None
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    databases_available: List[str]
    ontology_entities: int
    timestamp: str


class LiveStatsResponse(BaseModel):
    """Real-time query statistics."""
    total_queries: int
    avg_drift_score: float
    convergence_rate: float
    queries_last_hour: int
    recent_queries: List[Dict[str, Any]]
    uptime_seconds: float


class StatsResponse(BaseModel):
    """Detailed statistics."""
    drift_distribution: Dict[str, int]
    latency_p50_ms: float
    latency_p95_ms: float
    top_entity_types: Dict[str, int]
    uptime_seconds: float
    total_queries: int


# ============================================================================
# FastAPI Application
# ============================================================================


class NLQueryAPI:
    """
    Production-grade natural language query API.
    
    Features:
    - Multi-agent query processing
    - Semantic drift metric monitoring
    - Complete audit trails
    - CORS support
    - Structured error handling
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="NL Data Retrieval System",
            description="Production-grade natural language query API with semantic drift quantification",
            version="1.0.0"
        )
        
        # Initialize core components
        self.ontology = BusinessOntology()

        # Database managers (cached)
        engine_type = os.getenv("DB_DIALECT", "sqlite")
        db_host     = os.getenv("DB_HOST", "localhost")
        db_user     = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "postgres")
        db_port     = int(os.getenv("DB_PORT", "5432"))

        def _db(name: str) -> DatabaseManager:
            pg_db = f"nlretrieval_{name}"
            return DatabaseManager(DatabaseConfig(
                engine_type=engine_type,
                host=db_host     if engine_type == "postgresql" else None,
                user=db_user     if engine_type == "postgresql" else None,
                password=db_password if engine_type == "postgresql" else None,
                port=db_port     if engine_type == "postgresql" else 5432,
                database=pg_db if engine_type == "postgresql" else name,
            ))

        self.databases = {
            "sales":     _db("sales"),
            "inventory": _db("inventory"),
            "analytics": _db("analytics"),
            "hr":        _db("hr"),
            "finance":   _db("finance"),
        }

        self.agent_pipeline = AgentPipeline(self.ontology, db_manager=self.databases["sales"])
        
        # Setup middleware
        self.setup_middleware()
        
        # Setup routes
        self.setup_routes()
        
        self.logger = logging.getLogger(__name__)
    
    def setup_middleware(self):
        """Configure CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Register API routes."""
        
        @self.app.post("/query", response_model=QueryResponse)
        async def process_query(request: QueryRequest) -> QueryResponse:
            """
            Process natural language query.
            
            Takes a natural language query and routes it through the multi-agent
            pipeline, returning structured results with complete provenance trail.
            """
            try:
                # Validate database exists
                if request.database not in self.databases:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Database '{request.database}' not available. Choose from: {list(self.databases.keys())}"
                    )
                
                # Process query through agent pipeline
                query_state = self.agent_pipeline.process_query(
                    user_query=request.query,
                    max_iterations=request.max_iterations
                )
                
                # Generate provenance trail
                explanation = self._generate_explanation(query_state)
                
                # Format agent trace
                agent_trace = [
                    {
                        "timestamp": str(record.timestamp),
                        "agent": record.agent.value,
                        "action": record.action,
                        "details": record.details,
                    }
                    for record in query_state.trace_log
                ]
                
                # Format results
                results = [
                    row.data for row in (query_state.results.rows if query_state.results else [])
                ]
                
                drift_val = query_state.final_drift or 0
                exec_ms = query_state.results.execution_time_ms if query_state.results else 0

                response = QueryResponse(
                    query_id=query_state.query_id,
                    user_query=request.query,
                    status="success" if not query_state.error else "error",
                    results=results,
                    result_count=query_state.results.row_count if query_state.results else 0,
                    confidence=ConfidenceScore(
                        intent_alignment=query_state.drift_scores[-1].intent_alignment if query_state.drift_scores else 0,
                        constraint_adherence=query_state.drift_scores[-1].constraint_adherence if query_state.drift_scores else 0,
                        result_plausibility=query_state.drift_scores[-1].result_plausibility if query_state.drift_scores else 0,
                        composite_drift=drift_val,
                    ),
                    execution_time_ms=exec_ms,
                    explanation=explanation,
                    agent_trace=agent_trace,
                    final_query=query_state.plan.sql_template if query_state.plan else None,
                    error_message=query_state.error,
                )

                # Append to query log
                entities = query_state.intent.entities if query_state.intent else []
                metrics  = query_state.intent.metrics  if query_state.intent else []
                log_entry = {
                    "query_id":       query_state.query_id,
                    "user_query":     request.query,
                    "timestamp":      datetime.now(timezone.utc).isoformat(),
                    "status":         response.status,
                    "drift":          drift_val,
                    "converged":      query_state.converged,
                    "execution_ms":   exec_ms,
                    "result_count":   response.result_count,
                    "entities":       entities,
                    "metrics":        metrics,
                }
                with _log_lock:
                    _query_log.append(log_entry)

                return response
            
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Query processing error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check() -> HealthResponse:
            """
            Health check endpoint.
            
            Returns system status and available resources.
            """
            return HealthResponse(
                status="healthy",
                databases_available=list(self.databases.keys()),
                ontology_entities=len(self.ontology.entities),
                timestamp=datetime.utcnow().isoformat()
            )
        
        @self.app.get("/schema")
        async def get_schema(database: str = Query("sales", description="Database name")):
            """
            Get database schema information.
            
            Returns all tables, columns, and types for the specified database.
            """
            if database not in self.databases:
                raise HTTPException(
                    status_code=400,
                    detail=f"Database '{database}' not found"
                )
            
            try:
                schema = self.databases[database].get_schema()
                return {
                    "database": database,
                    "schema": schema,
                    "tables": list(schema.keys()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/ontology")
        async def get_ontology():
            """Get complete business ontology."""
            return {
                "entities": {k: v.to_dict() for k, v in self.ontology.entities.items()},
                "metrics": {k: v.to_dict() for k, v in self.ontology.metrics.items()},
                "constraints": len(self.ontology.constraints),
                "join_rules": len(self.ontology.joins),
                "timestamp": datetime.utcnow().isoformat()
            }

        @self.app.get("/live", response_model=LiveStatsResponse)
        async def get_live_stats() -> LiveStatsResponse:
            """Real-time pipeline statistics — polled every 5s by dashboards."""
            with _log_lock:
                entries = list(_query_log)

            now = datetime.now(timezone.utc)
            uptime = (now - _start_time).total_seconds()

            if entries:
                avg_drift = sum(e["drift"] for e in entries) / len(entries)
                converged_count = sum(1 for e in entries if e.get("converged"))
                convergence_rate = converged_count / len(entries)
                one_hour_ago = now.timestamp() - 3600
                queries_last_hour = sum(
                    1 for e in entries
                    if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp() >= one_hour_ago
                )
            else:
                avg_drift = 0.0
                convergence_rate = 0.0
                queries_last_hour = 0

            recent = [
                {
                    "query_id":     e["query_id"],
                    "user_query":   e["user_query"],
                    "timestamp":    e["timestamp"],
                    "drift":        round(e["drift"], 4),
                    "converged":    e.get("converged", False),
                    "status":       e.get("status", "unknown"),
                    "execution_ms": round(e.get("execution_ms", 0), 1),
                }
                for e in list(reversed(entries))[:10]
            ]

            return LiveStatsResponse(
                total_queries=len(entries),
                avg_drift_score=round(avg_drift, 4),
                convergence_rate=round(convergence_rate, 4),
                queries_last_hour=queries_last_hour,
                recent_queries=recent,
                uptime_seconds=round(uptime, 1),
            )

        @self.app.get("/history")
        async def get_history(limit: int = Query(50, le=1000)) -> Dict[str, Any]:
            """Full query history (up to last 1000 entries)."""
            with _log_lock:
                entries = list(reversed(list(_query_log)))[:limit]
            return {"count": len(entries), "queries": entries}

        @self.app.get("/stats", response_model=StatsResponse)
        async def get_stats() -> StatsResponse:
            """Aggregated drift distribution, latency percentiles, entity usage."""
            with _log_lock:
                entries = list(_query_log)

            now = datetime.now(timezone.utc)
            uptime = (now - _start_time).total_seconds()

            drift_dist = {"low": 0, "medium": 0, "high": 0}
            latencies: List[float] = []
            entity_counts: Dict[str, int] = {}

            for e in entries:
                d = e["drift"]
                if d < 0.10:
                    drift_dist["low"] += 1
                elif d < 0.20:
                    drift_dist["medium"] += 1
                else:
                    drift_dist["high"] += 1

                ms = e.get("execution_ms", 0)
                if ms:
                    latencies.append(ms)

                for ent in e.get("entities", []):
                    entity_counts[ent] = entity_counts.get(ent, 0) + 1

            latencies.sort()
            p50 = latencies[len(latencies) // 2] if latencies else 0.0
            p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

            return StatsResponse(
                drift_distribution=drift_dist,
                latency_p50_ms=round(p50, 1),
                latency_p95_ms=round(p95, 1),
                top_entity_types=entity_counts,
                uptime_seconds=round(uptime, 1),
                total_queries=len(entries),
            )
    
    def _generate_explanation(self, query_state) -> str:
        """
        Generate human-readable explanation of query results.
        
        Explains:
        - What the system understood
        - What constraints were applied
        - What the results mean
        """
        parts = []
        
        # Intent understanding
        if query_state.intent:
            entities_str = ", ".join(query_state.intent.entities) if query_state.intent.entities else "general"
            metrics_str = ", ".join(query_state.intent.metrics) if query_state.intent.metrics else "count"
            parts.append(f"Understood your question about {entities_str} and {metrics_str}.")
        
        # Constraints applied
        if query_state.constraints:
            satisfied = sum(1 for c in query_state.constraints if c.get("is_satisfied", False))
            parts.append(f"Applied {satisfied} out of {len(query_state.constraints)} business constraints.")
        
        # Results summary
        if query_state.results:
            parts.append(f"Retrieved {query_state.results.row_count} records in {query_state.results.execution_time_ms:.0f}ms.")
        
        # Confidence
        if query_state.final_drift is not None:
            if query_state.final_drift < 0.15:
                parts.append("Result confidence: HIGH (semantic drift < 0.15)")
            elif query_state.final_drift < 0.25:
                parts.append("Result confidence: MODERATE (semantic drift < 0.25)")
            else:
                parts.append("Result confidence: LOW (semantic drift >= 0.25)")
        
        return " ".join(parts) if parts else "Query processed successfully."
    
    def get_app(self) -> FastAPI:
        """Return FastAPI application instance."""
        return self.app


# ============================================================================
# Application Factory
# ============================================================================


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    api = NLQueryAPI()
    return api.get_app()


# Module-level app instance — used by uvicorn in Docker/production
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
