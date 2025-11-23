"""
Tests for Custom Exceptions
"""
import pytest
from fastapi import status

from src.core.exceptions import (
    InnerVerseException,
    ConfigurationError,
    DatabaseError,
    APIError,
    ValidationError,
    ResourceNotFoundError,
    RateLimitError,
    http_exception_from_innerverse
)


def test_innerverse_exception_base():
    """Test base InnerVerse exception"""
    exc = InnerVerseException(
        message="Test error",
        error_code="TEST_ERROR",
        details={"key": "value"}
    )
    
    assert exc.message == "Test error"
    assert exc.error_code == "TEST_ERROR"
    assert exc.details == {"key": "value"}
    
    # Test to_dict
    exc_dict = exc.to_dict()
    assert exc_dict["error"] == "TEST_ERROR"
    assert exc_dict["message"] == "Test error"
    assert exc_dict["details"] == {"key": "value"}


def test_configuration_error():
    """Test configuration error exception"""
    exc = ConfigurationError(
        message="Missing config",
        missing_keys=["KEY1", "KEY2"]
    )
    
    assert exc.error_code == "CONFIGURATION_ERROR"
    assert exc.details["missing_keys"] == ["KEY1", "KEY2"]


def test_database_error():
    """Test database error exception"""
    exc = DatabaseError(
        message="Query failed",
        operation="INSERT"
    )
    
    assert exc.error_code == "DATABASE_ERROR"
    assert exc.details["operation"] == "INSERT"


def test_api_error():
    """Test API error exception"""
    exc = APIError(
        message="External API failed",
        service="OpenAI",
        status_code=500
    )
    
    assert exc.error_code == "API_ERROR"
    assert exc.details["service"] == "OpenAI"
    assert exc.details["status_code"] == 500


def test_validation_error():
    """Test validation error exception"""
    exc = ValidationError(
        message="Invalid input",
        field="email"
    )
    
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details["field"] == "email"


def test_resource_not_found_error():
    """Test resource not found exception"""
    exc = ResourceNotFoundError(
        message="Course not found",
        resource_type="course",
        resource_id="123"
    )
    
    assert exc.error_code == "RESOURCE_NOT_FOUND"
    assert exc.details["resource_type"] == "course"
    assert exc.details["resource_id"] == "123"


def test_rate_limit_error():
    """Test rate limit error exception"""
    exc = RateLimitError(
        message="Too many requests",
        retry_after=60
    )
    
    assert exc.error_code == "RATE_LIMIT_EXCEEDED"
    assert exc.details["retry_after"] == 60


def test_http_exception_conversion():
    """Test conversion to HTTPException"""
    exc = ResourceNotFoundError(
        message="Not found",
        resource_type="lesson",
        resource_id="456"
    )
    
    http_exc = http_exception_from_innerverse(exc)
    
    assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    assert "error" in http_exc.detail
    assert http_exc.detail["error"] == "RESOURCE_NOT_FOUND"


def test_http_exception_rate_limit():
    """Test rate limit converts to 429"""
    exc = RateLimitError()
    http_exc = http_exception_from_innerverse(exc)
    
    assert http_exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_http_exception_validation():
    """Test validation error converts to 422"""
    exc = ValidationError(message="Invalid")
    http_exc = http_exception_from_innerverse(exc)
    
    assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

