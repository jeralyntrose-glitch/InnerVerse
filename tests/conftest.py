"""
Pytest Configuration and Fixtures
Shared test fixtures for the entire test suite
"""
import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/innerverse_test")

from app import app
from src.core.database import get_db_connection, DatabaseManager
from src.core.config import get_settings


@pytest.fixture(scope="session")
def test_settings():
    """Get test settings"""
    return get_settings()


@pytest.fixture(scope="session")
def test_db_url(test_settings):
    """Get test database URL"""
    return test_settings.DATABASE_URL


@pytest.fixture(scope="function")
def test_db(test_db_url):
    """
    Create a fresh test database for each test
    Automatically rolls back changes after test
    """
    engine = create_engine(test_db_url)
    connection = engine.connect()
    transaction = connection.begin()
    
    yield connection
    
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client():
    """
    FastAPI test client
    Use this to make requests to your API endpoints
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('src.api.dependencies.get_openai_client') as mock:
        mock_client = Mock()
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    with patch('src.api.dependencies.get_anthropic_client') as mock:
        mock_client = Mock()
        mock_client.messages.create.return_value = Mock(
            content=[Mock(text="Test response")],
            usage=Mock(input_tokens=100, output_tokens=50)
        )
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_pinecone_client():
    """Mock Pinecone client for testing"""
    with patch('src.api.dependencies.get_pinecone_client') as mock:
        mock_pc = Mock()
        mock_index = Mock()
        mock_index.query.return_value = Mock(
            matches=[
                Mock(id="1", score=0.9, metadata={"text": "test"}),
            ]
        )
        mock_pc.Index.return_value = mock_index
        mock.return_value = mock_pc
        yield mock_pc


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing uploads"""
    return b"%PDF-1.4 sample content"


@pytest.fixture
def sample_course_data():
    """Sample course data for testing"""
    return {
        "title": "Test Course",
        "description": "A test course",
        "category": "test",
        "difficulty": "beginner",
        "estimated_duration": "1 hour"
    }


@pytest.fixture
def sample_lesson_data():
    """Sample lesson data for testing"""
    return {
        "title": "Test Lesson",
        "content": "This is test lesson content",
        "order": 1,
        "duration": 30
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    # Clear any cached dependencies
    from functools import lru_cache
    from src.api.dependencies import get_kg_manager, get_pinecone_client, get_openai_client, get_anthropic_client
    
    # Clear LRU caches
    get_kg_manager.cache_clear()
    get_pinecone_client.cache_clear()
    get_openai_client.cache_clear()
    get_anthropic_client.cache_clear()
    
    yield
    
    # Cleanup after test
    pass

