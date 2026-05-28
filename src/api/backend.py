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
    ai_powered: bool = False
    suggested_database: Optional[str] = None
    auto_rerouted: bool = False
    clarification_options: List[str] = []

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
    ontology_metrics: int
    ontology_rules: int
    ai_powered: bool
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
                
                # Detect if query spans multiple databases
                multi_db_results = self._run_multi_db_query(request.query, request.database, request.max_iterations)

                if multi_db_results:
                    # Cross-DB query: merge results from each DB, use best state for metadata
                    results = multi_db_results["results"]
                    result_count = len(results)
                    query_state = multi_db_results["primary_state"]
                    drift_val = query_state.final_drift or 0
                    exec_ms = sum(multi_db_results["exec_times"])
                    auto_rerouted = False
                    suggested_db = None
                    explanation = f"Cross-database query — results merged from: {', '.join(multi_db_results['dbs_used'])}."
                    agent_trace = [
                        {
                            "timestamp": str(record.timestamp),
                            "agent": record.agent.value,
                            "action": record.action,
                            "details": record.details,
                        }
                        for record in query_state.trace_log
                    ]
                else:
                    # Single-DB query: normal pipeline (cap at 2 iterations to avoid long Claude waits)
                    db_for_query = self.databases.get(request.database, self.databases["sales"])
                    single_pipeline = AgentPipeline(self.ontology, db_manager=db_for_query)
                    query_state = single_pipeline.process_query(
                        user_query=request.query,
                        max_iterations=min(request.max_iterations, 2),
                    )

                    explanation = self._generate_explanation(query_state)
                    agent_trace = [
                        {
                            "timestamp": str(record.timestamp),
                            "agent": record.agent.value,
                            "action": record.action,
                            "details": record.details,
                        }
                        for record in query_state.trace_log
                    ]
                    results = [
                        row.data for row in (query_state.results.rows if query_state.results else [])
                    ]

                    drift_val = query_state.final_drift or 0
                    result_count = query_state.results.row_count if query_state.results else 0
                    exec_ms = query_state.results.execution_time_ms if query_state.results else 0

                    # Auto-reroute when high drift + no results
                    suggested_db = None
                    auto_rerouted = False
                    if drift_val > 0.15 and result_count == 0:
                        suggested_db = self._suggest_database(query_state, self.ontology)
                        if suggested_db and suggested_db != request.database:
                            reroute_pipeline = AgentPipeline(
                                self.ontology, db_manager=self.databases[suggested_db]
                            )
                            query_state2 = reroute_pipeline.process_query(
                                user_query=request.query,
                                max_iterations=request.max_iterations,
                            )
                            if query_state2.results and query_state2.results.row_count > 0:
                                query_state = query_state2
                                drift_val = query_state.final_drift or 0
                                result_count = query_state.results.row_count
                                results = [row.data for row in query_state.results.rows]
                                exec_ms = query_state.results.execution_time_ms
                                auto_rerouted = True
                                explanation = self._generate_explanation(query_state)
                                agent_trace = [
                                    {
                                        "timestamp": str(r.timestamp),
                                        "agent": r.agent.value,
                                        "action": r.action,
                                        "details": r.details,
                                    }
                                    for r in query_state.trace_log
                                ]

                # Generate clarification options whenever drift is high (with or without rows)
                clarification_options: List[str] = []
                if drift_val > 0.15:
                    clarification_options = self._generate_clarifications(request.query, query_state)

                claude_explanation = query_state.context.get("claude_explanation")
                response = QueryResponse(
                    query_id=query_state.query_id,
                    user_query=request.query,
                    status="success" if not query_state.error else "error",
                    ai_powered=getattr(self.agent_pipeline, "ai_powered", False),
                    suggested_database=suggested_db,
                    auto_rerouted=auto_rerouted,
                    clarification_options=clarification_options,
                    results=results,
                    result_count=result_count,
                    confidence=ConfidenceScore(
                        intent_alignment=query_state.drift_scores[-1].intent_alignment if query_state.drift_scores else 0,
                        constraint_adherence=query_state.drift_scores[-1].constraint_adherence if query_state.drift_scores else 0,
                        result_plausibility=query_state.drift_scores[-1].result_plausibility if query_state.drift_scores else 0,
                        composite_drift=drift_val,
                    ),
                    execution_time_ms=exec_ms,
                    explanation=claude_explanation or explanation,
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
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                databases_available=list(self.databases.keys()),
                ontology_entities=len(self.ontology.entities),
                ontology_metrics=len(self.ontology.metrics),
                ontology_rules=len(self.ontology.constraints),
                ai_powered=getattr(self.agent_pipeline, "ai_powered", False),
                timestamp=datetime.utcnow().isoformat(),
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

        @self.app.get("/rules")
        async def get_rules(
            category: Optional[str] = Query(None, description="Filter by category tag"),
            severity: Optional[str] = Query(None, description="Filter by severity (REQUIRED/WARNING/INFO)"),
            limit: int = Query(50, le=500, description="Max rules to return"),
        ):
            """Browse business rules from the ontology."""
            rules = list(self.ontology.constraints.values())
            if severity:
                rules = [r for r in rules if r.severity.upper() == severity.upper()]
            if category:
                rules = [
                    r for r in rules
                    if category.lower() in r.rule_type.lower()
                    or category.lower() in r.rule_id.lower()
                    or any(category.lower() in str(t).lower() for t in getattr(r, "entities_affected", []))
                ]
            rules = rules[:limit]
            return {
                "total_rules": len(self.ontology.constraints),
                "filtered_count": len(rules),
                "rules": [r.to_dict() for r in rules],
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
    
    def _run_multi_db_query(self, query: str, primary_db: str, max_iterations: int) -> Optional[Dict]:
        """
        Detect cross-DB queries and run each relevant DB in parallel, merging results.
        Returns None if the query is single-DB (caller handles it normally).
        """
        import concurrent.futures

        # Quick entity scan using ontology aliases to find which DBs are needed
        query_lower = query.lower()
        db_hits: Dict[str, int] = {}
        for eid, edef in self.ontology.entities.items():
            aliases = [edef.name.lower()] + [a.lower() for a in edef.natural_language_aliases]
            if any(alias in query_lower for alias in aliases):
                db_hits[edef.source_database] = db_hits.get(edef.source_database, 0) + 1

        # Only treat as multi-DB if 2+ distinct databases are needed
        needed_dbs = [db for db, cnt in db_hits.items() if cnt > 0]
        if len(needed_dbs) < 2:
            return None

        # Cap iterations at 1 per DB for cross-DB queries to avoid long waits
        cross_db_iters = 1

        def _run_one(db_name: str):
            if db_name not in self.databases:
                return db_name, None
            pipeline = AgentPipeline(self.ontology, db_manager=self.databases[db_name])
            state = pipeline.process_query(user_query=query, max_iterations=cross_db_iters)
            return db_name, state

        # Run all DBs in parallel with a 45s wall-clock timeout per DB
        states: Dict[str, Any] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(needed_dbs)) as executor:
            futures = {executor.submit(_run_one, db): db for db in needed_dbs}
            for future in concurrent.futures.as_completed(futures, timeout=45):
                try:
                    db_name, state = future.result()
                    states[db_name] = state
                except Exception:
                    pass

        merged_results: List[Dict] = []
        exec_times: List[float] = []
        primary_state = None
        dbs_used: List[str] = []

        for db_name in needed_dbs:
            state = states.get(db_name)
            if state and state.results and state.results.row_count > 0:
                for row in state.results.rows:
                    row_with_source = dict(row.data)
                    row_with_source["_source_db"] = db_name
                    merged_results.append(row_with_source)
                exec_times.append(state.results.execution_time_ms)
                dbs_used.append(db_name)
                if primary_state is None:
                    primary_state = state

        if not merged_results:
            return None

        return {
            "results": merged_results,
            "primary_state": primary_state,
            "exec_times": exec_times,
            "dbs_used": dbs_used,
        }

    def _suggest_database(self, query_state, ontology) -> Optional[str]:
        """Return the most likely source database based on entities in the query intent."""
        import subprocess, shutil
        entities = (query_state.intent.entities if query_state.intent else []) or []
        votes: Dict[str, int] = {}
        for eid in entities:
            entity_def = ontology.entities.get(eid)
            if entity_def:
                db = entity_def.source_database
                votes[db] = votes.get(db, 0) + 1
        if not votes:
            return None
        best_db = max(votes, key=lambda k: votes[k])
        top_count = votes[best_db]
        tied = [k for k, v in votes.items() if v == top_count]
        return best_db if len(tied) == 1 else None

    def _generate_clarifications(self, query: str, query_state) -> List[str]:
        """Ask Claude for 5 plain-English queries grounded in the real DB schema."""
        import subprocess, shutil, json as _json
        claude_bin = os.getenv("CLAUDE_BIN", "claude")
        if not shutil.which(claude_bin):
            return []

        entities = (query_state.intent.entities if query_state.intent else []) or []

        # Determine which database is most relevant
        suggested_db = self._suggest_database(query_state, self.ontology)
        target_db_name = suggested_db or "sales"
        target_db = self.databases.get(target_db_name)

        # Get real schema from the actual database
        schema_lines = []
        if target_db:
            try:
                real_schema = target_db.get_schema()
                for table, cols in real_schema.items():
                    col_str = ", ".join(list(cols.keys())[:8])
                    schema_lines.append(f"  {table}({col_str})")
            except Exception:
                pass

        # Fallback to ontology if db schema unavailable
        if not schema_lines:
            for eid, edef in self.ontology.entities.items():
                if not entities or eid in entities or edef.source_database == target_db_name:
                    cols = ", ".join(list(edef.attributes.keys())[:8])
                    schema_lines.append(f"  {edef.table_name}({cols})")

        schema_str = "\n".join(schema_lines[:30])

        prompt = (
            f"A user asked: \"{query}\"\n"
            f"The system may have returned results but with high semantic drift (poor confidence). "
            f"The target database is '{target_db_name}'.\n"
            f"Available tables:\n{schema_str}\n\n"
            "Write exactly 5 alternative plain-English questions that better match the business data. Rules:\n"
            "1. Each must be a VARIATION of the original question — same subject/intent, just rephrased, narrowed, or more specific.\n"
            "   Good: original='transactions this month' → 'total transaction amount by payment gateway this month'\n"
            "   Bad:  original='transactions this month' → 'show all product categories'  (unrelated!)\n"
            "2. Each must be answerable from the tables listed above (only use existing columns).\n"
            "3. Vary the specificity: broad summary → filtered → grouped → top-N → trend over time.\n"
            "4. Keep entity/domain consistent with the original.\n"
            "5. Phrase each as a clear, concise business question a data analyst would ask.\n\n"
            "Respond with ONLY a JSON array of 5 strings, nothing else.\n"
            "Example for 'transactions this month': "
            "[\"Show total transaction count and amount for this month\", "
            "\"List all completed transactions from this month sorted by amount descending\", "
            "\"What is the total revenue from sales transactions this month?\", "
            "\"Show transactions grouped by payment gateway for this month\", "
            "\"What are the top 10 highest-value transactions made this month?\"]"
        )
        try:
            result = subprocess.run(
                [claude_bin, "-p", prompt],
                capture_output=True, text=True, timeout=30
            )
            raw = result.stdout.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = _json.loads(raw.strip())
            if isinstance(parsed, list):
                return [str(s) for s in parsed[:5]]
        except Exception:
            pass
        return []

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
