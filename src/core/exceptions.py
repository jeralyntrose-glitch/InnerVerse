"""
Custom Exception Classes
Provides structured error handling across the application
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class InnerVerseException(Exception):
    """Base exception for all InnerVerse errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ConfigurationError(InnerVerseException):
    """Raised when configuration is invalid or missing"""
    
    def __init__(self, message: str, missing_keys: list = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"missing_keys": missing_keys or []}
        )


class DatabaseError(InnerVerseException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={"operation": operation}
        )


class APIError(InnerVerseException):
    """Raised when external API calls fail"""
    
    def __init__(self, message: str, service: str = None, status_code: int = None):
        super().__init__(
            message=message,
            error_code="API_ERROR",
            details={
                "service": service,
                "status_code": status_code
            }
        )


class AuthenticationError(InnerVerseException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR"
        )


class ValidationError(InnerVerseException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field}
        )


class ResourceNotFoundError(InnerVerseException):
    """Raised when requested resource doesn't exist"""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )


class RateLimitError(InnerVerseException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )


class KnowledgeGraphError(InnerVerseException):
    """Raised when knowledge graph operations fail"""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(
            message=message,
            error_code="KNOWLEDGE_GRAPH_ERROR",
            details={"operation": operation}
        )


class ConceptExtractionError(InnerVerseException):
    """Raised when concept extraction fails"""
    
    def __init__(self, message: str, document_id: str = None):
        super().__init__(
            message=message,
            error_code="CONCEPT_EXTRACTION_ERROR",
            details={"document_id": document_id}
        )


# HTTP Exception factories for FastAPI
def http_exception_from_innerverse(exc: InnerVerseException) -> HTTPException:
    """Convert InnerVerse exception to FastAPI HTTPException"""
    
    status_map = {
        "CONFIGURATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "API_ERROR": status.HTTP_502_BAD_GATEWAY,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "KNOWLEDGE_GRAPH_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CONCEPT_EXTRACTION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = status_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=status_code,
        detail=exc.to_dict()
    )

