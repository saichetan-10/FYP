"""Streamlit dashboards for query results and provenance."""

import json
from typing import Dict, Any, List

from src.logging_config import StructuredLogger

logger = StructuredLogger(__name__)


def generate_dashboard_a_config() -> Dict[str, Any]:
    """Generate Dashboard A configuration for direct data retrieval and visualization."""
    return {
        "dashboard_name": "Dashboard A - Direct Query Interface",
        "description": "Drift-free data retrieval and interactive visualization",
        "pages": [
            {
                "name": "Query Builder",
                "components": [
                    {"type": "text_input", "key": "user_query", "label": "Enter your query"},
                    {"type": "submit_button", "label": "Execute Query"},
                ],
            },
            {
                "name": "Results",
                "components": [
                    {
                        "type": "metric",
                        "key": "result_count",
                        "label": "Rows Returned",
                    },
                    {
                        "type": "dataframe",
                        "key": "query_results",
                        "label": "Query Results",
                    },
                    {
                        "type": "chart",
                        "chart_type": "bar",
                        "key": "result_distribution",
                        "label": "Result Distribution",
                    },
                ],
            },
            {
                "name": "Performance",
                "components": [
                    {
                        "type": "metric",
                        "key": "query_time_ms",
                        "label": "Query Execution Time (ms)",
                    },
                    {
                        "type": "metric",
                        "key": "rows_per_second",
                        "label": "Throughput (rows/sec)",
                    },
                ],
            },
        ],
    }


def generate_dashboard_b_config() -> Dict[str, Any]:
    """Generate Dashboard B configuration for query provenance and confidence."""
    return {
        "dashboard_name": "Dashboard B - Query Provenance & Confidence",
        "description": "Query provenance logs with confidence scores, drift alerts, and explanations",
        "pages": [
            {
                "name": "Query History",
                "components": [
                    {
                        "type": "table",
                        "columns": [
                            {"name": "Query ID", "key": "query_id"},
                            {"name": "Query Text", "key": "user_query"},
                            {"name": "Timestamp", "key": "timestamp"},
                            {"name": "Status", "key": "status"},
                            {"name": "Confidence", "key": "confidence_score"},
                            {"name": "Drift", "key": "semantic_drift"},
                        ],
                        "key": "query_history",
                        "label": "Recent Queries",
                    },
                ],
            },
            {
                "name": "Provenance Details",
                "components": [
                    {
                        "type": "expander",
                        "title": "Query Breakdown",
                        "items": [
                            {
                                "type": "subheader",
                                "text": "Extracted Entities",
                            },
                            {
                                "type": "list",
                                "key": "extracted_entities",
                            },
                            {
                                "type": "subheader",
                                "text": "Identified Metrics",
                            },
                            {
                                "type": "list",
                                "key": "identified_metrics",
                            },
                        ],
                    },
                ],
            },
            {
                "name": "Drift Analysis",
                "components": [
                    {
                        "type": "metric",
                        "key": "semantic_drift_score",
                        "label": "Semantic Drift Score",
                        "delta_key": "drift_delta",
                    },
                    {
                        "type": "gauge_chart",
                        "key": "intent_alignment",
                        "label": "Intent Alignment %",
                        "min": 0,
                        "max": 100,
                    },
                    {
                        "type": "gauge_chart",
                        "key": "constraint_adherence",
                        "label": "Constraint Adherence %",
                        "min": 0,
                        "max": 100,
                    },
                    {
                        "type": "gauge_chart",
                        "key": "result_plausibility",
                        "label": "Result Plausibility %",
                        "min": 0,
                        "max": 100,
                    },
                ],
            },
            {
                "name": "Confidence & Alerts",
                "components": [
                    {
                        "type": "info_box",
                        "key": "confidence_summary",
                        "label": "Confidence Score",
                    },
                    {
                        "type": "warning_box",
                        "key": "drift_alert",
                        "label": "Drift Alert",
                        "condition": "semantic_drift > threshold",
                    },
                    {
                        "type": "metric",
                        "key": "constraint_violations",
                        "label": "Constraint Violations",
                    },
                ],
            },
            {
                "name": "Why This Answer?",
                "components": [
                    {
                        "type": "markdown",
                        "key": "why_explanation",
                        "label": "Query Resolution Explanation",
                    },
                    {
                        "type": "code_block",
                        "language": "sql",
                        "key": "execution_sql",
                        "label": "Executed SQL Template",
                    },
                    {
                        "type": "json_viewer",
                        "key": "agent_traces",
                        "label": "Agent Execution Traces",
                    },
                    {
                        "type": "json_viewer",
                        "key": "applied_constraints",
                        "label": "Applied Business Rules",
                    },
                ],
            },
        ],
    }


class DashboardManager:
    """Manages dashboard configurations and data."""

    def __init__(self):
        """Initialize dashboard manager."""
        self.logger = StructuredLogger(__name__)
        self.dashboard_a_config = generate_dashboard_a_config()
        self.dashboard_b_config = generate_dashboard_b_config()
        self.query_history = []

    def add_query_to_history(self, query_result: Dict[str, Any]) -> None:
        """Add query result to history."""
        self.query_history.append({
            "query_id": query_result.get("query_id"),
            "user_query": query_result.get("user_query"),
            "timestamp": query_result.get("timestamp"),
            "status": "success" if query_result.get("success") else "failed",
            "confidence_score": query_result.get("confidence", 0.0),
            "semantic_drift": query_result.get("semantic_drift", 0.0),
        })

        self.logger.info(
            "query_added_to_history",
            query_id=query_result.get("query_id"),
            status=query_result.get("success"),
        )

    def get_dashboard_a_data(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for Dashboard A."""
        return {
            "query_id": query_result.get("query_id"),
            "result_count": len(query_result.get("results", [])),
            "query_results": query_result.get("results", []),
            "query_time_ms": query_result.get("query_time_ms", 0),
            "rows_per_second": (
                len(query_result.get("results", [])) / (query_result.get("query_time_ms", 1) / 1000)
                if query_result.get("query_time_ms")
                else 0
            ),
        }

    def get_dashboard_b_data(self, provenance_record: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for Dashboard B."""
        drift_score = provenance_record.get("drift_metrics", {}).get("composite_drift", 0.0)
        threshold = 0.15

        return {
            "query_id": provenance_record.get("query_id"),
            "user_query": provenance_record.get("user_query"),
            "timestamp": provenance_record.get("timestamp"),
            "extracted_entities": [e.get("entity_value") for e in provenance_record.get("entities", [])],
            "identified_metrics": [m.get("metric_name") for m in provenance_record.get("metrics", [])],
            "semantic_drift_score": drift_score,
            "drift_delta": drift_score - threshold,
            "intent_alignment": (
                provenance_record.get("drift_metrics", {}).get("intent_alignment", 0.0) * 100
            ),
            "constraint_adherence": (
                provenance_record.get("drift_metrics", {}).get("constraint_adherence", 0.0) * 100
            ),
            "result_plausibility": (
                provenance_record.get("drift_metrics", {}).get("result_plausibility", 0.0) * 100
            ),
            "confidence_summary": f"Confidence: {provenance_record.get('confidence_score', 0.0):.2%}",
            "drift_alert": f"Drift Score: {drift_score:.4f} - {'ALERT' if drift_score > threshold else 'OK'}",
            "constraint_violations": len(
                [c for c in provenance_record.get("applied_constraints", []) if not c.get("satisfied")]
            ),
            "why_explanation": provenance_record.get("why_explanation", ""),
            "execution_sql": provenance_record.get("execution_plan", {}).get("sql_template", ""),
            "agent_traces": provenance_record.get("agent_traces", []),
            "applied_constraints": provenance_record.get("applied_constraints", []),
        }

    def export_to_json(self, output_path: str) -> None:
        """Export dashboard configurations to JSON."""
        import pathlib

        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        configs = {
            "dashboard_a": self.dashboard_a_config,
            "dashboard_b": self.dashboard_b_config,
            "query_history": self.query_history,
        }

        with open(output_path, "w") as f:
            json.dump(configs, f, indent=2, default=str)

        self.logger.info("dashboards_exported", output_path=output_path)
