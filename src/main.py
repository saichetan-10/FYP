"""Main entry point for the Semantic Grounding Engine."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import argparse

# Try to import real packages, fall back to mocks
try:
    from pydantic import BaseModel, Field
except ImportError:
    sys.path.insert(0, '..')
    from mock_pydantic import BaseModel, Field

try:
    import sqlalchemy
except ImportError:
    sys.path.insert(0, '..')
    import mock_sqlalchemy as sqlalchemy

try:
    from langgraph import StateGraph
except ImportError:
    sys.path.insert(0, '..')
    from mock_langgraph import StateGraph

from src.config import config
from src.logging_config import StructuredLogger, configure_logging
from src.db.manager import DatabaseManager
from src.engine.ontology import BusinessOntology
from src.engine.orchestrator import SemanticGroundingOrchestrator
from src.api.backend import create_app, StandaloneQueryExecutor
from src.dashboards.manager import DashboardManager

logger = StructuredLogger(__name__)


class SemanticGroundingSystem:
    """Main system class coordinating all components."""

    def __init__(self):
        """Initialize the system."""
        self.db_manager = None
        self.ontology = None
        self.orchestrator = None
        self.executor = None
        self.dashboard_manager = None

    def initialize(self) -> None:
        """Initialize all system components."""
        logger.info("system_initialization_started")

        # Initialize database
        self.db_manager = DatabaseManager()
        self.db_manager.initialize_database()

        # Initialize ontology
        self.ontology = self._build_sample_ontology()

        # Initialize orchestrator
        self.orchestrator = SemanticGroundingOrchestrator(
            ontology=self.ontology,
            config=config,
            db_manager=self.db_manager,
        )

        # Initialize executor
        self.executor = StandaloneQueryExecutor(self.orchestrator)

        # Initialize dashboard manager
        self.dashboard_manager = DashboardManager()

        logger.info("system_initialization_complete")

    def _build_sample_ontology(self) -> BusinessOntology:
        """Build a research ontology for text-to-SQL semantic drift studies."""
        logger.info("building_research_ontology")

        ontology = BusinessOntology()

        # Define core research entities for text-to-SQL studies
        ontology.add_entity(
            "query",
            "Natural Language Query",
            "User-submitted natural language queries for analysis",
            {"primary_key": "query_id", "primary_metric": "complexity_score"},
        )

        ontology.add_entity(
            "sql",
            "Generated SQL",
            "SQL statements generated from natural language",
            {"primary_key": "sql_id", "primary_metric": "execution_time"},
        )

        ontology.add_entity(
            "result",
            "Query Results",
            "Execution results from generated SQL",
            {"primary_key": "result_id", "primary_metric": "row_count"},
        )

        ontology.add_entity(
            "drift",
            "Semantic Drift Metrics",
            "Quantified measures of semantic misalignment",
            {"primary_key": "drift_id", "primary_metric": "drift_score"},
        )

        ontology.add_entity(
            "constraint",
            "Business Constraints",
            "Business rules and validation constraints",
            {"primary_key": "constraint_id", "primary_dimension": "constraint_type"},
        )

        # Define research metrics for semantic drift quantification
        ontology.add_metric(
            "semantic_drift",
            "Composite Semantic Drift Score",
            "0.4×(1-alignment) + 0.3×(1-adherence) + 0.3×(1-plausibility)",
            "drift",
            aggregation_type="AVG",
            unit="drift_score",
            valid_range=(0.0, 1.0),
        )

        ontology.add_metric(
            "intent_alignment",
            "Intent Alignment Score",
            "cosine_similarity(query_embedding, sql_embedding)",
            "query",
            aggregation_type="AVG",
            unit="similarity",
            valid_range=(0.0, 1.0),
        )

        ontology.add_metric(
            "constraint_adherence",
            "Constraint Adherence Rate",
            "COUNT(satisfied_constraints) / COUNT(total_constraints)",
            "constraint",
            aggregation_type="AVG",
            unit="percentage",
            valid_range=(0.0, 1.0),
        )

        ontology.add_metric(
            "result_plausibility",
            "Result Plausibility Score",
            "1 - z_score_anomaly_probability",
            "result",
            aggregation_type="AVG",
            unit="confidence",
            valid_range=(0.0, 1.0),
        )

        ontology.add_metric(
            "query_success_rate",
            "Query Success Rate",
            "COUNT(successful_queries) / COUNT(total_queries)",
            "query",
            aggregation_type="AVG",
            unit="percentage",
            valid_range=(0.0, 1.0),
        )

        ontology.add_metric(
            "execution_accuracy",
            "SQL Execution Accuracy",
            "COUNT(valid_results) / COUNT(total_executions)",
            "sql",
            aggregation_type="AVG",
            unit="percentage",
            valid_range=(0.0, 1.0),
        )

        # Define research constraints for semantic drift studies
        ontology.add_temporal_constraint(
            "experiment_duration",
            "Research experiments completed within time bounds",
            "daily",
            retention_days=90,
        )

        ontology.add_temporal_constraint(
            "data_freshness",
            "Test datasets remain current for research validity",
            "weekly",
            retention_days=30,
        )

        # Define join rules for research data relationships
        ontology.add_join_rule(
            "query_sql_join",
            "query",
            "sql",
            "one_to_one",
            "ON query.query_id = sql.query_id",
            "query_id",
        )

        ontology.add_join_rule(
            "sql_result_join",
            "sql",
            "result",
            "one_to_one",
            "ON sql.sql_id = result.sql_id",
            "sql_id",
        )

        ontology.add_join_rule(
            "query_drift_join",
            "query",
            "drift",
            "one_to_one",
            "ON query.query_id = drift.query_id",
            "query_id",
        )

        logger.info("research_ontology_built", entities=len(ontology.entities),
                   metrics=len(ontology.metrics), constraints=len(ontology.temporal_constraints),
                   join_rules=len(ontology.join_rules))
        return ontology

    async def execute_eval_mode(self, num_queries: int = 10) -> Dict[str, Any]:
        """Execute evaluation mode with test queries."""
        logger.info("eval_mode_started", num_queries=num_queries)

        # Define test queries
        test_queries = [
            "What is the total revenue for the US region this year?",
            "Show me the top 10 customers by profit margin",
            "How many unique customers did we have in Q4?",
            "What products have the highest sales volume?",
            "Calculate the average order value by region",
            "Which departments generated the most revenue?",
            "Show transaction count by transaction type",
            "What is the year-over-year revenue growth?",
            "Identify customers with declining purchase frequency",
            "What is the profit margin by product category?",
        ]

        # Run evaluation
        eval_results = await self.orchestrator.evaluate_on_test_queries(test_queries[:num_queries])

        # Archive results
        results_archive = {
            "timestamp": datetime.utcnow().isoformat(),
            "num_queries": num_queries,
            "eval_results": eval_results,
            "system_stats": self.orchestrator.get_stats(),
        }

        archive_path = Path(config.logging.log_dir) / "eval_results.json"
        with open(archive_path, "w") as f:
            json.dump(results_archive, f, indent=2, default=str)

        logger.info(
            "eval_mode_complete",
            results_archived_to=str(archive_path),
            success_rate=eval_results.get("success_rate"),
        )

        return results_archive

    async def run_query_loop(self) -> None:
        """Run interactive query loop."""
        logger.info("interactive_query_loop_started")

        print("\n" + "=" * 60)
        print("Semantic Grounding Engine - Query Executor")
        print("=" * 60)
        print("Enter 'quit' to exit\n")

        while True:
            try:
                user_query = input("Query> ").strip()

                if user_query.lower() == "quit":
                    break

                if not user_query:
                    continue

                result = self.executor.execute(user_query)

                print("\n" + "-" * 60)
                print(f"Query ID: {result.get('query_id')}")
                print(f"Success: {result.get('success')}")
                print(f"Semantic Drift: {result.get('semantic_drift'):.4f}")
                print(f"Iterations: {result.get('iterations')}")

                if result.get("entities"):
                    print(f"\nExtracted Entities:")
                    for entity in result.get("entities", []):
                        print(f"  - {entity.get('entity_value')} ({entity.get('confidence'):.2%})")

                if result.get("metrics"):
                    print(f"\nIdentified Metrics:")
                    for metric in result.get("metrics", []):
                        print(f"  - {metric.get('metric_name')}")

                print("-" * 60 + "\n")

            except KeyboardInterrupt:
                logger.info("query_loop_interrupted")
                break
            except Exception as e:
                logger.error("query_loop_error", error=str(e))
                print(f"Error: {str(e)}\n")

    async def run_api_server(self) -> None:
        """Run FastAPI server."""
        import uvicorn

        logger.info("api_server_starting", host=config.api.host, port=config.api.port)

        app = create_app(self.orchestrator, self.db_manager)

        uvicorn.run(
            app,
            host=config.api.host,
            port=config.api.port,
            workers=config.api.workers,
        )

    def generate_documentation(self) -> None:
        """Generate MkDocs documentation."""
        logger.info("documentation_generation_started")

        docs_dir = Path(config.logging.log_dir) / "../docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Create mkdocs.yml
        mkdocs_config = {
            "site_name": "Semantic Grounding Engine Documentation",
            "theme": "material",
            "docs_dir": "docs",
            "site_dir": "site",
            "nav": [
                {"Home": "index.md"},
                {"Architecture": "architecture.md"},
                {"Drift Metric": "drift_metric.md"},
                {"Agents": "agents.md"},
                {"API": "api.md"},
                {"Evaluation": "evaluation.md"},
            ],
        }

        with open("mkdocs.yml", "w") as f:
            import yaml
            yaml.dump(mkdocs_config, f)

        logger.info("documentation_generated", docs_dir=str(docs_dir))


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Semantic Grounding Engine - Constraint-driven multi-agent query system"
    )
    parser.add_argument(
        "--mode",
        choices=["eval", "interactive", "api"],
        default="interactive",
        help="Execution mode",
    )
    parser.add_argument(
        "--num-queries",
        type=int,
        default=10,
        help="Number of queries for eval mode",
    )

    args = parser.parse_args()

    # Initialize logging
    configure_logging()

    logger.info("application_started", mode=args.mode)

    # Initialize system
    system = SemanticGroundingSystem()
    system.initialize()

    try:
        if args.mode == "eval":
            logger.info("running_eval_mode", num_queries=args.num_queries)
            results = await system.execute_eval_mode(args.num_queries)
            print("\n" + "=" * 60)
            print("EVALUATION RESULTS")
            print("=" * 60)
            print(json.dumps(results, indent=2, default=str))

        elif args.mode == "interactive":
            await system.run_query_loop()

        elif args.mode == "api":
            await system.run_api_server()

    except Exception as e:
        logger.error("application_error", error=str(e))
        sys.exit(1)
    finally:
        logger.info("application_shutdown")


if __name__ == "__main__":
    asyncio.run(main())
