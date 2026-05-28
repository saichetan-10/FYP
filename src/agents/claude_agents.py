"""
Claude-powered drop-in replacements for the five pipeline agents.

Each class mirrors the interface of its regex counterpart:
  - __init__(self, ontology, ...)
  - process(self, state: QueryState) -> QueryState

Uses the local `claude` CLI (Claude Code) via subprocess — no API key or
network SSL required. On any failure the corresponding regex agent is the fallback.
"""

import json
import os
import subprocess
from typing import Any, Dict, List, Optional

from src.agents.state import (
    AgentType,
    ConstraintType,
    ExecutionPlan,
    ExtractedIntent,
    OntologyMapping,
    QueryResult,
    QueryResults,
    QueryState,
    ValidatedConstraint,
)
from src.engine.ontology import BusinessOntology

# ---------------------------------------------------------------------------
# Claude CLI caller
# ---------------------------------------------------------------------------

_CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")


def _call(system: str, user: str, tools: Optional[List[dict]] = None, max_tokens: int = 1024) -> Any:
    """
    Call the local `claude` CLI and return a pseudo content-block dict.

    When tools are provided the prompt instructs Claude to respond with a
    JSON object matching the first tool's input_schema, wrapped in a fake
    tool_use block so the callers don't need to change.
    """
    if tools:
        tool = tools[0]
        schema_str = json.dumps(tool["input_schema"], indent=2)
        prompt = (
            f"{system}\n\n"
            f"You MUST respond with ONLY a valid JSON object matching this schema "
            f"(no markdown, no explanation):\n{schema_str}\n\n"
            f"{user}"
        )
        result = subprocess.run(
            [_CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True, timeout=60,
        )
        raw = result.stdout.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract first {...} block
            import re
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            parsed = json.loads(m.group()) if m else {}

        # Return a fake tool_use block (dict with .type, .name, .input)
        class _Block:
            type = "tool_use"
            name = tool["name"]
            input = parsed
        return _Block()
    else:
        prompt = f"{system}\n\n{user}"
        result = subprocess.run(
            [_CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True, timeout=60,
        )

        class _TextBlock:
            type = "text"
            text = result.stdout.strip()
        return _TextBlock()


# ---------------------------------------------------------------------------
# Helper: compact ontology context for prompts
# ---------------------------------------------------------------------------

def _ontology_summary(ontology: BusinessOntology) -> str:
    entities = list(ontology.entities.keys())[:30]
    metrics = list(ontology.metrics.keys())[:30]
    return (
        f"ENTITIES ({len(ontology.entities)} total, sample): {', '.join(entities)}\n"
        f"METRICS ({len(ontology.metrics)} total, sample): {', '.join(metrics)}\n"
        f"RULES ({len(ontology.constraints)} total)"
    )


def _rules_for_entities(ontology: BusinessOntology, entity_ids: List[str], limit: int = 40) -> str:
    applicable = ontology.get_applicable_constraints(entity_ids)[:limit]
    lines = []
    for r in applicable:
        lines.append(f"[{r.rule_id}] {r.name} ({r.severity}): {r.description}")
    return "\n".join(lines) if lines else "No specific rules found."


# ============================================================================
# 1. Claude Intent Parser
# ============================================================================

_INTENT_TOOL = {
    "name": "extract_intent",
    "description": "Extract structured business query intent from natural language",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Business entity names referenced (e.g. CUSTOMER, ORDER, PRODUCT)",
            },
            "metrics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Metric keys requested (e.g. REVENUE, CHURN, AVG_ORDER_VALUE)",
            },
            "filters": {
                "type": "object",
                "description": "Key-value pairs: group_by, period_type, top_n, top_dir, region, customer_tier, order_status, product_category, year, compare_period, having_threshold, minimum_amount",
            },
            "confidence": {
                "type": "number",
                "description": "Overall parsing confidence 0-1",
            },
        },
        "required": ["entities", "metrics", "filters", "confidence"],
    },
}

_INTENT_SYSTEM = (
    "You are an expert business analytics query parser. "
    "Extract structured intent from natural language data queries. "
    "Map to the ontology keys provided. "
    "For group_by use one of: region, tier, category, month, year, status, product, supplier, region_and_tier. "
    "For period_type use one of: last_week, last_month, last_quarter, last_year, ytd. "
    "For metrics use ontology metric IDs or common aliases like REVENUE, COUNT, AVERAGE, PROFIT, GROSS_MARGIN, "
    "NEW_CUSTOMERS, CHURN, LTV, RETURN_RATE, INVENTORY, CONVERSION, RETENTION."
)


class ClaudeIntentParser:
    """Claude-powered intent parser with regex fallback."""

    def __init__(self, ontology: BusinessOntology = None):
        self.ontology = ontology
        from src.agents.pipeline import IntentParserAgent
        self._fallback = IntentParserAgent(ontology)

    def process(self, state: QueryState) -> QueryState:
        try:
            ontology_ctx = _ontology_summary(self.ontology) if self.ontology else ""
            user_msg = (
                f"Ontology context:\n{ontology_ctx}\n\n"
                f"Query: {state.user_query}"
            )
            block = _call(_INTENT_SYSTEM, user_msg, tools=[_INTENT_TOOL])
            if block.type == "tool_use" and block.name == "extract_intent":
                inp = block.input
                entities = [str(e).upper() for e in inp.get("entities", [])]
                metrics = [str(m).upper() for m in inp.get("metrics", [])]
                filters = {str(k): v for k, v in inp.get("filters", {}).items()}
                confidence = float(inp.get("confidence", 0.8))
                intent = ExtractedIntent(
                    entities=entities,
                    metrics=metrics,
                    filters=filters,
                    temporal_spec={"period": filters.get("period_type")} if filters.get("period_type") else None,
                    confidence_scores={m.lower(): confidence for m in metrics},
                    raw_text=state.user_query,
                )
                state.intent = intent
                state.add_trace(
                    AgentType.INTENT_PARSER,
                    "Claude extracted intent",
                    {"entities": entities, "metrics": metrics, "filters": filters, "confidence": confidence, "ai_powered": True},
                    include_state_snapshot=True,
                )
                return state
        except Exception as exc:
            state.add_trace(AgentType.INTENT_PARSER, f"Claude failed, using fallback: {exc}", {})
        return self._fallback.process(state)


# ============================================================================
# 2. Claude Ontology Mapper
# ============================================================================

_MAPPER_TOOL = {
    "name": "map_to_ontology",
    "description": "Map extracted terms to formal ontology paths with confidence scores",
    "input_schema": {
        "type": "object",
        "properties": {
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "term": {"type": "string"},
                        "ontology_path": {"type": "string"},
                        "similarity_score": {"type": "number"},
                        "resolution_method": {"type": "string"},
                    },
                    "required": ["term", "ontology_path", "similarity_score", "resolution_method"],
                },
            }
        },
        "required": ["mappings"],
    },
}

_MAPPER_SYSTEM = (
    "You are an ontology alignment specialist. "
    "Given extracted business terms and the available ontology, map each term to the most "
    "appropriate ontology path. Paths follow the pattern ontology.entities.ENTITY_ID or "
    "ontology.metrics.METRIC_ID. Provide a similarity score 0-1 and resolution method "
    "(exact, semantic, alias, inferred)."
)


class ClaudeOntologyMapper:
    """Claude-powered ontology mapper with fallback."""

    def __init__(self, ontology: BusinessOntology = None):
        self.ontology = ontology
        from src.agents.pipeline import OntologyMapperAgent
        self._fallback = OntologyMapperAgent(ontology)

    def process(self, state: QueryState) -> QueryState:
        if not state.intent:
            return state
        try:
            ontology_ctx = _ontology_summary(self.ontology) if self.ontology else ""
            terms = state.intent.entities + state.intent.metrics
            user_msg = (
                f"Ontology:\n{ontology_ctx}\n\n"
                f"Terms to map: {terms}"
            )
            block = _call(_MAPPER_SYSTEM, user_msg, tools=[_MAPPER_TOOL])
            if block.type == "tool_use" and block.name == "map_to_ontology":
                raw_mappings = block.input.get("mappings", [])
                mappings = [
                    OntologyMapping(
                        entity_name=m["term"],
                        ontology_path=m["ontology_path"],
                        similarity_score=float(m["similarity_score"]),
                        aliases_matched=[m["term"]],
                        is_valid=True,
                        resolution_method=m.get("resolution_method", "semantic"),
                    )
                    for m in raw_mappings
                ]
                state.mappings = mappings
                state.add_trace(
                    AgentType.ONTOLOGY_MAPPER,
                    "Claude mapped to ontology",
                    {"mappings_count": len(mappings), "paths": [m.ontology_path for m in mappings], "ai_powered": True},
                    include_state_snapshot=True,
                )
                return state
        except Exception as exc:
            state.add_trace(AgentType.ONTOLOGY_MAPPER, f"Claude failed, using fallback: {exc}", {})
        return self._fallback.process(state)


# ============================================================================
# 3. Claude Constraint Validator
# ============================================================================

_VALIDATOR_TOOL = {
    "name": "validate_constraints",
    "description": "Determine which business rules are satisfied or violated by this query",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string"},
                        "rule_name": {"type": "string"},
                        "is_satisfied": {"type": "boolean"},
                        "severity": {"type": "string"},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["rule_id", "rule_name", "is_satisfied", "severity"],
                },
            },
            "all_satisfied": {"type": "boolean"},
        },
        "required": ["results", "all_satisfied"],
    },
}

_VALIDATOR_SYSTEM = (
    "You are a business rules compliance expert. "
    "Evaluate which constraints are satisfied or violated by a given analytics query. "
    "For each applicable rule, determine: is the intent of this query compliant? "
    "Consider PII rules, data freshness, region filters, fiscal calendars, etc. "
    "Return all_satisfied=true if no REQUIRED rules are violated."
)


class ClaudeConstraintValidator:
    """Claude-powered constraint validator with fallback."""

    def __init__(self, ontology: BusinessOntology = None):
        self.ontology = ontology
        from src.agents.pipeline import ConstraintValidatorAgent
        self._fallback = ConstraintValidatorAgent(ontology)

    def process(self, state: QueryState) -> QueryState:
        if not state.mappings or not self.ontology:
            state.all_constraints_satisfied = True
            return state
        try:
            entity_ids = [m.entity_name for m in state.mappings]
            rules_text = _rules_for_entities(self.ontology, entity_ids, limit=50)
            user_msg = (
                f"Query: {state.user_query}\n\n"
                f"Extracted intent entities: {entity_ids}\n\n"
                f"Applicable rules:\n{rules_text}"
            )
            block = _call(_VALIDATOR_SYSTEM, user_msg, tools=[_VALIDATOR_TOOL], max_tokens=2048)
            if block.type == "tool_use" and block.name == "validate_constraints":
                inp = block.input
                raw = inp.get("results", [])
                constraints = [
                    {
                        "type": r.get("rule_id", "UNKNOWN"),
                        "description": r.get("rule_name", ""),
                        "is_satisfied": bool(r.get("is_satisfied", True)),
                        "severity": r.get("severity", "INFO"),
                        "reasoning": r.get("reasoning", ""),
                    }
                    for r in raw
                ]
                all_satisfied = bool(inp.get("all_satisfied", True))
                state.constraints = constraints
                state.all_constraints_satisfied = all_satisfied
                state.add_trace(
                    AgentType.CONSTRAINT_VALIDATOR,
                    "Claude validated constraints",
                    {
                        "total": len(constraints),
                        "satisfied": sum(1 for c in constraints if c["is_satisfied"]),
                        "all_satisfied": all_satisfied,
                        "ai_powered": True,
                    },
                    include_state_snapshot=True,
                )
                return state
        except Exception as exc:
            state.add_trace(AgentType.CONSTRAINT_VALIDATOR, f"Claude failed, using fallback: {exc}", {})
        return self._fallback.process(state)


# ============================================================================
# 4. Claude Execution Planner
# ============================================================================

_PLANNER_TOOL = {
    "name": "generate_sql",
    "description": "Generate optimized SQL for a business analytics query",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "Complete, executable SQL query"},
            "join_order": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tables in join order",
            },
            "optimization_notes": {"type": "string"},
        },
        "required": ["sql", "join_order"],
    },
}


class ClaudeExecutionPlanner:
    """Claude-powered SQL planner with fallback."""

    def __init__(self, ontology: BusinessOntology = None, dialect: str = "sqlite", db_manager=None):
        self.ontology = ontology
        self.dialect = dialect
        self.db_manager = db_manager
        from src.agents.pipeline import ExecutionPlannerAgent, _build_sql
        self._fallback = ExecutionPlannerAgent(ontology, dialect=dialect)
        self._build_sql = _build_sql

    def _schema_hint(self) -> str:
        """Return real schema from db_manager if available, else fall back to ontology."""
        if self.db_manager:
            try:
                schema = self.db_manager.get_schema()
                lines = []
                for table, cols in schema.items():
                    col_str = ", ".join(list(cols.keys())[:10])
                    lines.append(f"  {table}({col_str})")
                return "\n".join(lines)
            except Exception:
                pass
        if not self.ontology:
            return ""
        lines = []
        for eid, e in list(self.ontology.entities.items())[:30]:
            cols = ", ".join(list(e.attributes.keys())[:8])
            lines.append(f"  {e.table_name}({cols})")
        return "\n".join(lines)

    def process(self, state: QueryState) -> QueryState:
        # Always attempt Claude SQL generation — even with no ontology mappings
        try:
            schema = self._schema_hint()
            user_msg = (
                f"Dialect: {self.dialect}\n"
                f"Query: \"{state.user_query}\"\n\n"
                f"Intent:\n"
                f"  entities={state.intent.entities if state.intent else []}\n"
                f"  metrics={state.intent.metrics if state.intent else []}\n"
                f"  filters={state.intent.filters if state.intent else {}}\n\n"
                f"Available tables and columns in this database:\n{schema}\n\n"
                "Write SQL using ONLY the tables listed above. "
                "Use JOINs where needed (e.g. employees JOIN salaries ON employee_id). "
                "Do NOT reference tables that are not in the schema above. "
                "If the query asks for data not available in any of the tables above, "
                "write the closest possible query using the available tables."
            )
            system = (
                f"You are an expert SQL engineer for {self.dialect}. "
                "Write an optimized, correct SQL query for the given business analytics request. "
                "Use table aliases. Use proper JOINs between related tables. "
                f"Return valid {self.dialect} syntax only. "
                "ONLY use tables that exist in the schema provided. "
                "Never use tables like 'orders' for employee queries — use 'employees' and 'salaries'."
            )
            block = _call(system, user_msg, tools=[_PLANNER_TOOL], max_tokens=1024)
            if block.type == "tool_use" and block.name == "generate_sql":
                inp = block.input
                fallback_sql = self._build_sql(state.intent, dialect=self.dialect)
                sql = inp.get("sql", "").strip() or fallback_sql
                join_order = inp.get("join_order", ["orders"])
                notes = inp.get("optimization_notes", f"Claude-generated SQL (dialect={self.dialect})")
                plan = ExecutionPlan(
                    sql_template=sql,
                    parameters={},
                    join_order=join_order,
                    estimated_rows=500,
                    query_dag={t: [] for t in join_order},
                    optimization_notes=notes,
                )
                state.plan = plan
                state.add_trace(
                    AgentType.EXECUTION_PLANNER,
                    "Claude generated SQL",
                    {"sql_preview": sql[:300], "dialect": self.dialect, "ai_powered": True},
                    include_state_snapshot=True,
                )
                return state
        except Exception as exc:
            state.add_trace(AgentType.EXECUTION_PLANNER, f"Claude failed, using fallback: {exc}", {})
        return self._fallback.process(state)


# ============================================================================
# 5. Claude Result Verifier
# ============================================================================

_VERIFIER_TOOL = {
    "name": "verify_results",
    "description": "Verify query results and generate a plain-English explanation",
    "input_schema": {
        "type": "object",
        "properties": {
            "explanation": {"type": "string", "description": "Plain-English summary of the results"},
            "anomalies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of anomalies or concerns detected",
            },
            "plausibility_score": {
                "type": "number",
                "description": "Result plausibility 0-1",
            },
        },
        "required": ["explanation", "anomalies", "plausibility_score"],
    },
}

_VERIFIER_SYSTEM = (
    "You are a senior data analyst verifying business query results. "
    "Given a SQL query, its results (sample rows), and a semantic drift score, "
    "provide: a plain-English explanation of what the results mean, any anomalies or "
    "data quality concerns, and a plausibility score (0=implausible, 1=fully plausible). "
    "Be concise and business-friendly."
)


class ClaudeResultVerifier:
    """Claude-powered result verifier with fallback."""

    def __init__(self, ontology: BusinessOntology = None):
        self.ontology = ontology
        from src.agents.pipeline import ResultVerifierAgent
        self._fallback = ResultVerifierAgent(ontology)

    def process(self, state: QueryState) -> QueryState:
        # First run the regex verifier to populate state.results
        state = self._fallback.process(state)

        # Then enrich with Claude explanation if we have results
        if not state.results or not state.results.rows:
            return state
        try:
            sql = state.plan.sql_template[:500] if state.plan else "N/A"
            sample = [r.data for r in state.results.rows[:5]]
            drift = state.final_drift or 0.0
            user_msg = (
                f"Original query: {state.user_query}\n\n"
                f"SQL:\n{sql}\n\n"
                f"Row count: {state.results.row_count}\n"
                f"Sample rows: {json.dumps(sample, default=str)}\n\n"
                f"Semantic drift score: {drift:.4f}"
            )
            block = _call(_VERIFIER_SYSTEM, user_msg, tools=[_VERIFIER_TOOL], max_tokens=512)
            if block.type == "tool_use" and block.name == "verify_results":
                inp = block.input
                explanation = inp.get("explanation", "")
                anomalies = inp.get("anomalies", [])
                plausibility = float(inp.get("plausibility_score", 1.0))
                state.results.plausibility_score = plausibility
                state.add_trace(
                    AgentType.RESULT_VERIFIER,
                    "Claude verified results",
                    {
                        "explanation": explanation,
                        "anomalies": anomalies,
                        "plausibility_score": plausibility,
                        "ai_powered": True,
                    },
                    include_state_snapshot=True,
                )
                # Store explanation for use by the API layer
                state.context["claude_explanation"] = explanation
                state.context["claude_anomalies"] = anomalies
        except Exception as exc:
            state.add_trace(AgentType.RESULT_VERIFIER, f"Claude enrichment failed: {exc}", {})
        return state
