"""
Tests for Configuration Module
"""
import pytest
from src.core.config import Settings, get_settings


def test_settings_singleton():
    """Test that get_settings returns same instance"""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_settings_has_required_fields():
    """Test that settings has all required fields"""
    settings = get_settings()
    
    # Application settings
    assert hasattr(settings, 'APP_NAME')
    assert hasattr(settings, 'APP_VERSION')
    assert hasattr(settings, 'ENVIRONMENT')
    
    # API Keys
    assert hasattr(settings, 'OPENAI_API_KEY')
    assert hasattr(settings, 'ANTHROPIC_API_KEY')
    assert hasattr(settings, 'PINECONE_API_KEY')
    
    # Database
    assert hasattr(settings, 'DATABASE_URL')


def test_validate_required_keys():
    """Test configuration validation"""
    settings = get_settings()
    validation = settings.validate_required_keys()
    
    assert "valid" in validation
    assert "missing_required" in validation
    assert "missing_optional" in validation
    
    assert isinstance(validation["valid"], bool)
    assert isinstance(validation["missing_required"], list)
    assert isinstance(validation["missing_optional"], list)


def test_get_cors_origins_production():
    """Test CORS origins in production mode"""
    settings = get_settings()
    
    # Save original environment
    original_env = settings.ENVIRONMENT
    original_debug = settings.DEBUG
    
    try:
        # Set to production
        settings.ENVIRONMENT = "production"
        settings.DEBUG = False
        
        origins = settings.get_cors_origins()
        assert isinstance(origins, list)
        assert "*" not in origins  # Should not allow all origins in production
        
    finally:
        # Restore original
        settings.ENVIRONMENT = original_env
        settings.DEBUG = original_debug


def test_get_cors_origins_debug():
    """Test CORS origins in debug mode"""
    settings = get_settings()
    
    # Save original
    original_debug = settings.DEBUG
    
    try:
        # Set to debug
        settings.DEBUG = True
        
        origins = settings.get_cors_origins()
        assert isinstance(origins, list)
        
    finally:
        # Restore original
        settings.DEBUG = original_debug

