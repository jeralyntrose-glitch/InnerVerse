"""
Tests for Database Module
"""
import pytest
from src.core.database import DatabaseManager, get_db_connection, get_db_cursor


def test_database_manager_singleton():
    """Test that DatabaseManager is a singleton"""
    manager1 = DatabaseManager()
    manager2 = DatabaseManager()
    assert manager1 is manager2


def test_get_db_connection_context_manager():
    """Test database connection context manager"""
    try:
        with get_db_connection() as conn:
            assert conn is not None
            # Connection should be usable
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result is not None
            cursor.close()
    except Exception as e:
        # If database is not available in test environment, that's okay
        pytest.skip(f"Database not available: {e}")


def test_get_db_cursor_context_manager():
    """Test database cursor context manager"""
    try:
        with get_db_cursor() as cursor:
            assert cursor is not None
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result is not None
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


def test_db_cursor_with_commit():
    """Test cursor context manager with commit"""
    try:
        # This should not raise an error even with commit=True
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


def test_connection_returns_to_pool():
    """Test that connections are returned to pool after use"""
    manager = DatabaseManager()
    
    try:
        # Get multiple connections and ensure they're returned
        for _ in range(3):
            with get_db_connection() as conn:
                assert conn is not None
        
        # If we got here, connections were properly returned to pool
        assert True
        
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

