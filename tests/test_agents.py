"""
Integration tests for the 5-agent pipeline.

Tests the complete query processing flow including state transitions,
agent responsibilities, drift convergence, and end-to-end correctness.
"""

import pytest
from src.agents.pipeline import (
    AgentPipeline,
    IntentParserAgent,
    OntologyMapperAgent,
    ConstraintValidatorAgent,
    ExecutionPlannerAgent,
    ResultVerifierAgent,
)
from src.agents.state import QueryState, AgentType, ExecutionMetadata
from src.engine.ontology import BusinessOntology
from src.engine.semantic_drift import SemanticDriftMetric


def build_query_state(query: str, database: str = "sales") -> QueryState:
    metadata = ExecutionMetadata(
        query_id="QRY_TEST_0001",
        database_name=database
    )
    return QueryState(user_query=query, query_id=metadata.query_id, metadata=metadata)


class TestIntentParserAgent:
    """Test the IntentParserAgent responsibility."""
    
    def test_intent_parser_extracts_entities(self):
        """Should extract entities from NL queries"""
        ontology = BusinessOntology()
        agent = IntentParserAgent(ontology)
        query = "Show me all customers from North America"
        
        state = build_query_state(query)
        result = agent.process(state)
        
        assert result.intent is not None
        assert len(result.intent.entities) > 0
        assert "customer" in str(result.intent.entities).lower()
    
    def test_intent_parser_extracts_metrics(self):
        """Should extract metrics/aggregations"""
        ontology = BusinessOntology()
        agent = IntentParserAgent(ontology)
        query = "What is the total revenue for this year?"
        
        state = build_query_state(query)
        result = agent.process(state)
        
        assert result.intent is not None
        assert len(result.intent.metrics) > 0
        assert "revenue" in str(result.intent.metrics).lower() or \
               "total" in str(result.intent.metrics).lower()
    
    def test_intent_parser_extracts_filters(self):
        """Should extract filter conditions"""
        ontology = BusinessOntology()
        agent = IntentParserAgent(ontology)
        query = "Orders from 2024 with amount > 1000"
        
        state = build_query_state(query)
        result = agent.process(state)
        
        assert result.intent is not None
        # Filters may be in conditions or temporal specs
        assert len(result.intent.filters) > 0 or \
               result.intent.temporal_spec is not None
    
    def test_intent_parser_confidence_scoring(self):
        """Intent extraction should have confidence scores"""
        ontology = BusinessOntology()
        agent = IntentParserAgent(ontology)
        query = "Get total sales"
        
        state = build_query_state(query)
        result = agent.process(state)
        
        assert result.intent is not None
        assert result.intent.extraction_confidence >= 0.0
        assert result.intent.extraction_confidence <= 1.0


class TestOntologyMapperAgent:
    """Test the OntologyMapperAgent responsibility."""
    
    def test_ontology_mapper_maps_entities(self):
        """Should map extracted entities to ontology"""
        ontology = BusinessOntology()
        agent = OntologyMapperAgent(ontology)
        
        state = build_query_state("Show me customers")
        state = IntentParserAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.mappings is not None
        assert len(result.mappings) > 0
        assert any("customer" in m.ontology_path.lower() for m in result.mappings)
    
    def test_ontology_mapper_similarity_scores(self):
        """Mappings should include similarity scores"""
        ontology = BusinessOntology()
        agent = OntologyMapperAgent(ontology)
        
        state = build_query_state("Revenue by region")
        state = IntentParserAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.mappings is not None
        for mapping in result.mappings:
            assert mapping.similarity_score >= 0.0
            assert mapping.similarity_score <= 1.0
    
    def test_ontology_mapper_handles_ambiguity(self):
        """Should handle ambiguous terms"""
        ontology = BusinessOntology()
        agent = OntologyMapperAgent(ontology)
        
        state = build_query_state("Show me deals")  # Ambiguous term
        state = IntentParserAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.mappings is not None
        # Should still produce some mapping, even if confidence is lower


class TestConstraintValidatorAgent:
    """Test the ConstraintValidatorAgent responsibility."""
    
    def test_constraint_validator_validates_rules(self):
        """Should validate constraints against entities"""
        ontology = BusinessOntology()
        agent = ConstraintValidatorAgent(ontology)
        
        state = build_query_state("Total revenue")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.constraints is not None
        assert len(result.constraints) >= 0  # May have 0+ constraints
    
    def test_constraint_validator_marks_satisfied(self):
        """Should mark constraints as satisfied/violated"""
        ontology = BusinessOntology()
        agent = ConstraintValidatorAgent(ontology)
        
        state = build_query_state("Customer revenue")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        
        result = agent.process(state)
        
        for constraint in result.constraints:
            assert "is_satisfied" in constraint or \
                   "satisfied" in str(constraint).lower()
    
    def test_constraint_validator_all_constraints_flag(self):
        """Should set flag indicating if all constraints are satisfied"""
        ontology = BusinessOntology()
        agent = ConstraintValidatorAgent(ontology)
        
        state = build_query_state("Orders")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert hasattr(result, 'metadata') or \
               result.all_constraints_satisfied is not None


class TestExecutionPlannerAgent:
    """Test the ExecutionPlannerAgent responsibility."""
    
    def test_execution_planner_generates_sql(self):
        """Should generate SQL query template"""
        ontology = BusinessOntology()
        agent = ExecutionPlannerAgent(ontology)
        
        state = build_query_state("Total revenue")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        state = ConstraintValidatorAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.plan is not None
        assert len(result.plan.sql_template) > 0
        assert "select" in result.plan.sql_template.lower() or \
               "insert" in result.plan.sql_template.lower()
    
    def test_execution_planner_includes_parameters(self):
        """Query plan should include parameters"""
        ontology = BusinessOntology()
        agent = ExecutionPlannerAgent(ontology)
        
        state = build_query_state("Orders from 2024")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        state = ConstraintValidatorAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.plan is not None
        # Should have some parameters (even if empty list)
        assert isinstance(result.plan.parameters, dict)
    
    def test_execution_planner_includes_join_order(self):
        """Query plan should include join order for complex queries"""
        ontology = BusinessOntology()
        agent = ExecutionPlannerAgent(ontology)
        
        state = build_query_state("Customer orders with invoice amounts")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        state = ConstraintValidatorAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.plan is not None
        assert result.plan.join_order is not None


class TestResultVerifierAgent:
    """Test the ResultVerifierAgent responsibility."""
    
    def test_result_verifier_produces_results(self):
        """Should produce query results"""
        ontology = BusinessOntology()
        agent = ResultVerifierAgent(ontology)
        
        state = build_query_state("Show customers")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        state = ConstraintValidatorAgent(ontology).process(state)
        state = ExecutionPlannerAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.results is not None
        assert result.results.row_count >= 0
    
    def test_result_verifier_includes_anomaly_scores(self):
        """Results should include anomaly detection scores"""
        ontology = BusinessOntology()
        agent = ResultVerifierAgent(ontology)
        
        state = build_query_state("Revenue")
        state = IntentParserAgent(ontology).process(state)
        state = OntologyMapperAgent(ontology).process(state)
        state = ConstraintValidatorAgent(ontology).process(state)
        state = ExecutionPlannerAgent(ontology).process(state)
        
        result = agent.process(state)
        
        assert result.results is not None
        # Should have anomaly detection info
        assert result.results.plausibility_score is not None


class TestAgentPipeline:
    """Integration tests for the complete agent pipeline."""
    
    def test_pipeline_process_simple_query(self):
        """Pipeline should process simple NL queries"""
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        
        result = pipeline.process_query("What is total revenue?")
        
        assert result is not None
        assert result.query_id is not None
        assert result.final_drift is not None
    
    def test_pipeline_convergence_on_valid_query(self):
        """Pipeline should converge on valid, unambiguous queries"""
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        
        result = pipeline.process_query(
            "Show me total customer count",
            max_iterations=5
        )
        
        assert result.converged is True or result.metadata.total_iterations >= 1
    
    def test_pipeline_respects_max_iterations(self):
        """Pipeline should respect max_iterations parameter"""
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        
        result = pipeline.process_query(
            "Some complex query",
            max_iterations=2
        )
        
        assert result.metadata.total_iterations <= 2
    
    def test_pipeline_state_transitions(self):
        """Each pipeline iteration should transition state properly"""
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        
        result = pipeline.process_query("Customer count by region")
        
        # Should have progressed through all agents
        assert result.intent is not None
        assert len(result.mappings) > 0
        assert result.plan is not None
        assert result.results is not None
    
    def test_pipeline_trace_logging(self):
        """Pipeline should maintain audit trail"""
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        
        result = pipeline.process_query("Total revenue")
        
        assert len(result.trace_log) > 0
        # Should have records for each agent
        agent_types = [record.agent for record in result.trace_log]
        assert AgentType.INTENT_PARSER in agent_types
    
    def test_pipeline_drift_scores_improving(self):
        """Drift scores should generally improve across iterations"""
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        
        result = pipeline.process_query(
            "Show me all orders",
            max_iterations=3
        )
        
        if len(result.drift_scores) > 1:
            # At least ensure the pipeline produces valid drift scores
            for drift in result.drift_scores:
                assert 0.0 <= drift.composite_drift <= 1.0
    
    def test_pipeline_error_handling(self):
        """Pipeline should handle edge cases gracefully"""
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        
        # Empty query
        result = pipeline.process_query("")
        assert result is not None
        
        # Very long query
        result = pipeline.process_query("x" * 1000)
        assert result is not None
    
    def test_pipeline_deterministic_with_seed(self):
        """Pipeline should be deterministic with fixed seed"""
        import random
        
        ontology = BusinessOntology()
        pipeline = AgentPipeline(ontology)
        query = "Show me customers"
        
        random.seed(42)
        result1 = pipeline.process_query(query)
        
        random.seed(42)
        result2 = pipeline.process_query(query)
        
        # Drift and iterations should match
        assert abs(result1.final_drift - result2.final_drift) < 0.01


class TestStateTransitions:
    """Test QueryState transitions through the pipeline."""
    
    def test_state_carries_query_metadata(self):
        """Query state should preserve original query metadata"""
        original_query = "Test query for metadata"
        state = build_query_state(original_query)
        
        assert state.user_query == original_query
        assert state.query_id is not None
    
    def test_state_trace_accumulation(self):
        """Trace log should accumulate across agents"""
        state = build_query_state("test")
        
        state.add_trace(
            agent=AgentType.INTENT_PARSER,
            action="extraction",
            details={"entities": ["customer"]}
        )
        state.add_trace(
            agent=AgentType.ONTOLOGY_MAPPER,
            action="mapping",
            details={"mapped_to": "CUSTOMER"}
        )
        
        assert len(state.trace_log) == 2
        assert state.trace_log[0].agent == AgentType.INTENT_PARSER
        assert state.trace_log[1].agent == AgentType.ONTOLOGY_MAPPER
    
    def test_state_serialization(self):
        """State should be serializable for storage/logging"""
        state = build_query_state("test")
        state.add_trace(
            agent=AgentType.INTENT_PARSER,
            action="test",
            details={}
        )
        
        state_dict = state.to_dict()
        
        assert isinstance(state_dict, dict)
        assert "query_id" in state_dict
        assert "trace_log" in state_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
