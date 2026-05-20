"""Integration tests for multi-agent pipeline."""

import pytest
import asyncio
from src.engine.orchestrator import SemanticGroundingOrchestrator
from src.engine.ontology import BusinessOntology
from src.types import PipelineState, AgentType
from src.agents.pipeline import (
    IntentParserAgent,
    OntologyMapperAgent,
    ConstraintValidatorAgent,
    ExecutionPlannerAgent,
    ResultVerifierAgent,
)


@pytest.fixture
def ontology():
    """Create sample ontology."""
    return BusinessOntology()


@pytest.fixture
def orchestrator(ontology):
    """Create orchestrator."""
    return SemanticGroundingOrchestrator(ontology=ontology)


@pytest.mark.asyncio
async def test_intent_parser():
    """Test intent parser agent."""
    agent = IntentParserAgent()
    state = PipelineState(
        query_id="test_1",
        user_query="What is the total revenue for the US region?",
    )

    result = await agent.execute(state)

    assert "parsed_entities" in result
    assert "parsed_metrics" in result
    assert len(result["parsed_entities"]) > 0 or len(result["parsed_metrics"]) > 0


@pytest.mark.asyncio
async def test_ontology_mapper():
    """Test ontology mapper agent."""
    agent = OntologyMapperAgent()
    state = PipelineState(
        query_id="test_2",
        user_query="What is the total revenue for the US region?",
    )

    # Add some parsed entities
    from src.types import ParsedEntity, ParsedMetric

    state.parsed_entities.append(
        ParsedEntity(
            entity_type="business_unit",
            entity_value="sales",
            confidence=0.95,
        )
    )
    state.parsed_metrics.append(
        ParsedMetric(
            metric_name="revenue",
            metric_definition="Total income",
            aggregation_type="SUM",
            confidence=0.90,
        )
    )

    result = await agent.execute(state)

    assert "ontology_bindings" in result
    assert isinstance(result["ontology_bindings"], dict)


@pytest.mark.asyncio
async def test_constraint_validator():
    """Test constraint validator agent."""
    agent = ConstraintValidatorAgent()
    state = PipelineState(
        query_id="test_3",
        user_query="What is the revenue excluding taxes by region?",
    )

    result = await agent.execute(state)

    assert "constraints" in result
    constraints = result["constraints"]
    assert all(hasattr(c, "satisfied") for c in constraints)


@pytest.mark.asyncio
async def test_execution_planner():
    """Test execution planner agent."""
    agent = ExecutionPlannerAgent()
    state = PipelineState(
        query_id="test_4",
        user_query="Show revenue by region",
    )
    state.ontology_bindings = {"revenue": "metrics.revenue.definition"}

    result = await agent.execute(state)

    assert "execution_plan" in result
    plan = result["execution_plan"]
    assert plan is not None
    assert "sql_template" in plan.dict()


@pytest.mark.asyncio
async def test_result_verifier():
    """Test result verifier agent."""
    agent = ResultVerifierAgent()
    state = PipelineState(query_id="test_5", user_query="test")

    result = await agent.execute(state)

    assert "validation_passed" in result


@pytest.mark.asyncio
async def test_orchestrator_execution(orchestrator):
    """Test full orchestrator pipeline."""
    query = "What is the total revenue?"
    result = await orchestrator.execute_query(query)

    assert "query_id" in result
    assert "success" in result
    assert "semantic_drift" in result
    assert "iterations" in result
    assert result["iterations"] > 0


@pytest.mark.asyncio
async def test_orchestrator_multi_query(orchestrator):
    """Test orchestrator with multiple queries."""
    queries = [
        "What is the total revenue?",
        "Show me the top customers",
        "Calculate profit by region",
    ]

    for query in queries:
        result = await orchestrator.execute_query(query)
        assert result["success"] is not None


@pytest.mark.asyncio
async def test_orchestrator_eval_mode(orchestrator):
    """Test orchestrator in evaluation mode."""
    test_queries = [
        "Revenue for US?",
        "Top 10 customers?",
        "Profit by region?",
    ]

    eval_result = await orchestrator.evaluate_on_test_queries(test_queries)

    assert "total_queries" in eval_result
    assert eval_result["total_queries"] == 3
    assert "success_rate" in eval_result
    assert "detailed_results" in eval_result
    assert len(eval_result["detailed_results"]) == 3


@pytest.mark.asyncio
async def test_orchestrator_statistics(orchestrator):
    """Test orchestrator statistics."""
    await orchestrator.execute_query("Test query 1")
    await orchestrator.execute_query("Test query 2")

    stats = orchestrator.get_stats()

    assert "total_queries" in stats
    assert "successful_queries" in stats
    assert stats["total_queries"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
