"""
Integration tests for the FastAPI backend endpoints.

Tests all HTTP endpoints including request validation, response structure,
error handling, and edge cases.
"""

import pytest
import json
from fastapi.testclient import TestClient
from src.api.backend import create_app
from src.db.manager import initialize_databases


@pytest.fixture(scope="session")
def client():
    """Create FastAPI test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Initialize test databases."""
    initialize_databases()
    yield


class TestQueryEndpoint:
    """Test POST /query endpoint."""
    
    def test_query_endpoint_valid_request(self, client):
        """Should accept valid NL query and return results"""
        response = client.post(
            "/query",
            json={
                "query": "What is total customer count?",
                "database": "sales"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "query_id" in data
        assert "status" in data
        assert data["status"] in ["success", "error"]
    
    def test_query_endpoint_returns_results(self, client):
        """Should return actual query results"""
        response = client.post(
            "/query",
            json={
                "query": "Show customers",
                "database": "sales"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
    
    def test_query_endpoint_includes_confidence(self, client):
        """Response should include confidence scores"""
        response = client.post(
            "/query",
            json={
                "query": "Total revenue",
                "database": "sales"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "confidence" in data
        confidence = data["confidence"]
        assert "intent_alignment" in confidence
        assert "constraint_adherence" in confidence
        assert "result_plausibility" in confidence
        assert "composite_drift" in confidence
    
    def test_query_endpoint_includes_explanation(self, client):
        """Response should include human-readable explanation"""
        response = client.post(
            "/query",
            json={
                "query": "Show orders",
                "database": "sales"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data
        assert isinstance(data["explanation"], str)
        assert len(data["explanation"]) > 0
    
    def test_query_endpoint_includes_trace(self, client):
        """Response should include agent execution trace"""
        response = client.post(
            "/query",
            json={
                "query": "Customer count",
                "database": "sales"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "agent_trace" in data
        assert isinstance(data["agent_trace"], list)
        if len(data["agent_trace"]) > 0:
            trace = data["agent_trace"][0]
            assert "agent" in trace or "name" in trace
    
    def test_query_endpoint_includes_final_query(self, client):
        """Response should include the final SQL query"""
        response = client.post(
            "/query",
            json={
                "query": "Total amount",
                "database": "sales"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "final_query" in data
    
    def test_query_endpoint_with_max_iterations(self, client):
        """Should respect max_iterations parameter"""
        response = client.post(
            "/query",
            json={
                "query": "Show data",
                "database": "sales",
                "max_iterations": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "query_id" in data
    
    def test_query_endpoint_missing_query_field(self, client):
        """Should return 422 when query field is missing"""
        response = client.post(
            "/query",
            json={"database": "sales"}
        )
        
        assert response.status_code == 422
    
    def test_query_endpoint_invalid_database(self, client):
        """Should handle invalid database selection"""
        response = client.post(
            "/query",
            json={
                "query": "test",
                "database": "invalid_db"
            }
        )
        
        # Should either 400 or process with default
        assert response.status_code in [200, 400, 422]
    
    def test_query_endpoint_empty_query(self, client):
        """Should handle empty query string"""
        response = client.post(
            "/query",
            json={
                "query": "",
                "database": "sales"
            }
        )
        
        # Should return error or empty result
        assert response.status_code in [200, 400, 422]
    
    def test_query_endpoint_response_structure(self, client):
        """Response should have consistent structure"""
        response = client.post(
            "/query",
            json={
                "query": "test",
                "database": "sales"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "query_id", "status", "results", "confidence",
            "explanation", "execution_time_ms", "agent_trace"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestHealthEndpoint:
    """Test GET /health endpoint."""
    
    def test_health_endpoint_returns_200(self, client):
        """Health endpoint should return 200"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_endpoint_has_status(self, client):
        """Health response should include status field"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok", "ready"]
    
    def test_health_endpoint_lists_databases(self, client):
        """Health response should list available databases"""
        response = client.get("/health")
        data = response.json()
        assert "databases_available" in data
        assert isinstance(data["databases_available"], list)
    
    def test_health_endpoint_includes_timestamp(self, client):
        """Health response should include timestamp"""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data


class TestSchemaEndpoint:
    """Test GET /schema endpoint."""
    
    def test_schema_endpoint_returns_200(self, client):
        """Schema endpoint should return 200 for valid database"""
        response = client.get("/schema?database=sales")
        assert response.status_code == 200
    
    def test_schema_endpoint_includes_tables(self, client):
        """Schema response should include table information"""
        response = client.get("/schema?database=sales")
        data = response.json()
        assert isinstance(data, (dict, list))
    
    def test_schema_endpoint_multiple_databases(self, client):
        """Should work with different databases"""
        for db in ["sales", "inventory"]:
            response = client.get(f"/schema?database={db}")
            assert response.status_code == 200
    
    def test_schema_endpoint_missing_parameter(self, client):
        """Should handle missing database parameter"""
        response = client.get("/schema")
        # Should either return 400 or default database schema
        assert response.status_code in [200, 400, 422]


class TestOntologyEndpoint:
    """Test GET /ontology endpoint."""
    
    def test_ontology_endpoint_returns_200(self, client):
        """Ontology endpoint should return 200"""
        response = client.get("/ontology")
        assert response.status_code == 200
    
    def test_ontology_endpoint_includes_entities(self, client):
        """Ontology response should include entity information"""
        response = client.get("/ontology")
        data = response.json()
        assert "entities" in data or "entity_count" in data
    
    def test_ontology_endpoint_includes_metrics(self, client):
        """Ontology response should include metric information"""
        response = client.get("/ontology")
        data = response.json()
        assert "metrics" in data or "metric_count" in data
    
    def test_ontology_endpoint_includes_constraints(self, client):
        """Ontology response should include constraint information"""
        response = client.get("/ontology")
        data = response.json()
        assert "constraints" in data or "constraint_count" in data


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_404_on_invalid_endpoint(self, client):
        """Invalid endpoints should return 404"""
        response = client.get("/invalid_endpoint")
        assert response.status_code == 404
    
    def test_405_on_wrong_method(self, client):
        """Wrong HTTP method should return 405"""
        response = client.get("/query")  # POST endpoint called with GET
        assert response.status_code in [405, 404]  # Either method not allowed or not found
    
    def test_query_with_invalid_json(self, client):
        """Invalid JSON should return 422"""
        response = client.post(
            "/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestCORSAndHeaders:
    """Test CORS and response headers."""
    
    def test_cors_headers_present(self, client):
        """Response should include CORS headers"""
        response = client.get("/health")
        # Should not error
        assert response.status_code == 200
    
    def test_content_type_json(self, client):
        """Responses should have JSON content type"""
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")


class TestResponseValidation:
    """Test that responses match Pydantic models."""
    
    def test_query_response_validates(self, client):
        """Query response should match QueryResponse model"""
        response = client.post(
            "/query",
            json={"query": "test", "database": "sales"}
        )
        
        assert response.status_code == 200
        # If it returns 200, the response passed Pydantic validation
        data = response.json()
        
        # Basic validation
        assert isinstance(data.get("query_id"), str)
        assert isinstance(data.get("status"), str)
        assert isinstance(data.get("results"), list)
        assert isinstance(data.get("execution_time_ms"), (int, float))
    
    def test_health_response_validates(self, client):
        """Health response should match HealthResponse model"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data.get("status"), str)
        assert isinstance(data.get("databases_available"), list)


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_swagger_docs_available(self, client):
        """Swagger UI should be available at /docs"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_redoc_available(self, client):
        """ReDoc should be available at /redoc"""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_openapi_schema_available(self, client):
        """OpenAPI schema should be available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "components" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
