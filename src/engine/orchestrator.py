"""LangGraph orchestrator for constraint-driven multi-agent pipeline."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# Try to import real langgraph, fall back to mock
try:
    from langgraph import StateGraph
except ImportError:
    import sys
    sys.path.insert(0, '../..')
    from mock_langgraph import StateGraph

from src.types import PipelineState, AgentType, QueryExecutionPlan
from src.agents.pipeline import (
    IntentParserAgent,
    OntologyMapperAgent,
    ConstraintValidatorAgent,
    ExecutionPlannerAgent,
    ResultVerifierAgent,
)
from src.engine.semantic_drift_pure import SemanticDriftMetricPure as SemanticDriftMetric
from src.logging_config import StructuredLogger

logger = StructuredLogger(__name__)


class SemanticGroundingOrchestrator:
    """
    Orchestrates the constraint-driven multi-agent pipeline with critic loop
    for semantic drift validation.
    """

    def __init__(self, ontology=None, config=None, db_manager=None):
        """Initialize the orchestrator."""
        self.ontology = ontology
        self.config = config
        self.db_manager = db_manager

        # Initialize agents
        self.intent_parser = IntentParserAgent()
        self.ontology_mapper = OntologyMapperAgent(ontology)
        self.constraint_validator = ConstraintValidatorAgent()
        self.execution_planner = ExecutionPlannerAgent()
        self.result_verifier = ResultVerifierAgent()

        # Initialize drift metric calculator
        self.drift_metric = SemanticDriftMetric()

        # Execution statistics
        self.execution_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_iterations": 0.0,
            "total_iterations": 0,
        }

    async def execute_query(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        eval_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute query through the multi-agent pipeline with critic loop.

        Args:
            user_query: Natural language query
            context: Optional context information
            eval_mode: Whether in evaluation mode

        Returns:
            Result dictionary with outcomes and provenance
        """
        query_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        logger.info("query_started", query_id=query_id, eval_mode=eval_mode)

        # Initialize pipeline state
        state = PipelineState(
            query_id=query_id,
            user_query=user_query,
            max_iterations=5,
        )

        try:
            # Main critic loop
            while state.iteration_count < state.max_iterations:
                state.iteration_count += 1

                logger.info(
                    "iteration_started",
                    query_id=query_id,
                    iteration=state.iteration_count,
                )

                # 1. Intent Parsing
                intent_result = await self.intent_parser.execute(state)
                state.parsed_entities.extend(intent_result.get("parsed_entities", []))
                state.parsed_metrics.extend(intent_result.get("parsed_metrics", []))

                if "validation_errors" in intent_result:
                    state.validation_errors.extend(intent_result["validation_errors"])

                # 2. Ontology Mapping
                ontology_result = await self.ontology_mapper.execute(state)
                state.ontology_bindings.update(ontology_result.get("ontology_bindings", {}))

                # 3. Constraint Validation
                constraint_result = await self.constraint_validator.execute(state)
                state.constraints.extend(constraint_result.get("constraints", []))

                # 4. Execution Planning
                planning_result = await self.execution_planner.execute(state)
                state.execution_plan = planning_result.get("execution_plan")

                # 5. Execute Query (if we have a database manager)
                if self.db_manager and state.execution_plan:
                    try:
                        import time
                        query_start = time.time()
                        results = self.db_manager.execute_query(state.execution_plan.sql_template)
                        query_time_ms = (time.time() - query_start) * 1000

                        # Create a mock QueryResult object
                        from src.types import QueryResult
                        state.query_result = QueryResult(
                            query_id=state.query_id,
                            sql_executed=state.execution_plan.sql_template,
                            row_count=len(results),
                            query_time_ms=query_time_ms,
                            data=results[:100],  # Limit to first 100 rows
                            success=True,
                        )
                        logger.info("query_executed", query_id=query_id, row_count=len(results))
                    except Exception as e:
                        logger.error("query_execution_error", query_id=query_id, error=str(e))
                        state.validation_errors.append(f"Query execution failed: {str(e)}")

                # 6. Result Verification
                verification_result = await self.result_verifier.execute(state)
                state.validation_passed = verification_result.get("validation_passed", True)

                if "validation_errors" in verification_result:
                    state.validation_errors.extend(verification_result["validation_errors"])

                # Compute semantic drift metrics
                drift_score, drift_metrics = await self._compute_semantic_drift(state)
                state.semantic_drift = drift_score

                logger.info(
                    "iteration_complete",
                    query_id=query_id,
                    iteration=state.iteration_count,
                    drift=drift_score,
                    drift_passing=drift_metrics.passing_threshold,
                )

                # Check if drift threshold is satisfied
                should_continue, reason = self.drift_metric.validate_drift_threshold(
                    drift_score,
                    state.iteration_count,
                    state.max_iterations,
                )

                if not should_continue:
                    logger.info("drift_converged", query_id=query_id, reason=reason)
                    break

            # Compile final result
            result = {
                "query_id": query_id,
                "success": len(state.validation_errors) == 0 and state.validation_passed,
                "semantic_drift": state.semantic_drift,
                "iterations": state.iteration_count,
                "entities": [e.dict() for e in state.parsed_entities],
                "metrics": [m.dict() for m in state.parsed_metrics],
                "constraints": [c.dict() for c in state.constraints],
                "execution_plan": state.execution_plan.dict() if state.execution_plan else None,
                "agent_messages": len(state.agent_messages),
                "validation_errors": state.validation_errors,
                "eval_mode": eval_mode,
            }

            self.execution_stats["total_queries"] += 1
            if result["success"]:
                self.execution_stats["successful_queries"] += 1
            else:
                self.execution_stats["failed_queries"] += 1

            self.execution_stats["total_iterations"] += state.iteration_count

            elapsed_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                "query_completed",
                query_id=query_id,
                success=result["success"],
                iterations=state.iteration_count,
                elapsed_seconds=elapsed_time,
            )

            return result

        except Exception as e:
            logger.error("query_execution_failed", query_id=query_id, error=str(e))
            self.execution_stats["failed_queries"] += 1
            return {
                "query_id": query_id,
                "success": False,
                "error": str(e),
                "iterations": state.iteration_count,
            }

    async def _compute_semantic_drift(self, state: PipelineState) -> tuple:
        """
        Compute semantic drift metrics for current state.

        Returns:
            Tuple of (drift_score, DriftMetrics object)
        """
        # Intent alignment: based on entity/metric extraction confidence
        extracted_confidence = 0.0
        if state.parsed_entities:
            extracted_confidence = sum(e.confidence for e in state.parsed_entities) / len(
                state.parsed_entities
            )

        # For now, use extracted confidence as proxy for alignment
        intent_alignment = extracted_confidence

        # Constraint adherence: percentage of constraints satisfied
        if state.constraints:
            satisfied_count = sum(1 for c in state.constraints if c.satisfied)
            constraint_adherence = satisfied_count / len(state.constraints)
        else:
            constraint_adherence = 1.0

        # Result plausibility: mock based on validation passing
        result_plausibility = 0.95 if state.validation_passed else 0.5

        # Compute composite drift
        drift_score, drift_metrics = self.drift_metric.compute_composite_drift(
            intent_alignment,
            constraint_adherence,
            result_plausibility,
        )

        return drift_score, drift_metrics

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = self.execution_stats["total_queries"]
        if total > 0:
            success_rate = (
                self.execution_stats["successful_queries"] / total * 100
            )
            avg_iterations = self.execution_stats["total_iterations"] / total
        else:
            success_rate = 0.0
            avg_iterations = 0.0

        return {
            **self.execution_stats,
            "success_rate_percent": success_rate,
            "avg_iterations": avg_iterations,
        }

    async def evaluate_on_test_queries(self, test_queries: List[str]) -> Dict[str, Any]:
        """
        Evaluate system on a set of test queries.

        Args:
            test_queries: List of test queries

        Returns:
            Evaluation results
        """
        logger.info("evaluation_started", num_queries=len(test_queries))

        results = []
        for i, query in enumerate(test_queries):
            logger.info("evaluating_query", query_index=i + 1, total=len(test_queries))
            result = await self.execute_query(query, eval_mode=True)
            results.append(result)

        # Compute aggregate metrics
        successful = sum(1 for r in results if r["success"])
        avg_drift = sum(r.get("semantic_drift", 0.0) for r in results) / len(results)
        avg_iterations = sum(r.get("iterations", 0) for r in results) / len(results)

        eval_result = {
            "total_queries": len(test_queries),
            "successful_queries": successful,
            "success_rate": successful / len(test_queries) * 100,
            "avg_semantic_drift": avg_drift,
            "avg_iterations": avg_iterations,
            "detailed_results": results,
        }

        logger.info(
            "evaluation_completed",
            success_rate=eval_result["success_rate"],
            avg_drift=avg_drift,
        )

        return eval_result
