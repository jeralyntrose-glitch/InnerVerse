"""
Tests for Health Check Endpoints
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint returns 200"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "app" in data
    assert "version" in data
    assert data["app"] == "InnerVerse"


def test_health_check_includes_database_status(client: TestClient):
    """Test health check includes database status"""
    response = client.get("/health")
    data = response.json()
    
    assert "database" in data
    # Database status should be either "connected" or start with "error:"
    assert data["database"] in ["connected"] or data["database"].startswith("error:")


def test_health_check_includes_config_validation(client: TestClient):
    """Test health check validates configuration"""
    response = client.get("/health")
    data = response.json()
    
    assert "config_validation" in data
    validation = data["config_validation"]
    
    assert "required_keys_present" in validation
    assert "missing_required" in validation
    assert "missing_optional" in validation
    
    assert isinstance(validation["required_keys_present"], bool)
    assert isinstance(validation["missing_required"], list)
    assert isinstance(validation["missing_optional"], list)


def test_api_usage_endpoint(client: TestClient):
    """Test API usage statistics endpoint"""
    response = client.get("/api/usage")
    assert response.status_code == 200
    
    data = response.json()
    
    # Should have these keys even if empty
    if "error" not in data:
        assert "total_cost" in data
        assert "by_operation" in data
        assert "recent" in data
        
        assert isinstance(data["total_cost"], (int, float))
        assert isinstance(data["by_operation"], list)
        assert isinstance(data["recent"], list)

