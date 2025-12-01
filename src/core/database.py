"""
Database Connection Management
Implements connection pooling and context managers for safe database access
"""
import psycopg2
from psycopg2 import pool, extras
from contextlib import contextmanager
from typing import Generator, Optional
import threading

from .config import get_settings
from .logging import setup_logging

logger = setup_logging(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL connection pool and provides safe connection handling
    Implements singleton pattern to ensure single pool per application
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection pool if not already initialized"""
        if not hasattr(self, '_initialized'):
            settings = get_settings()
            
            try:
                logger.info("Initializing database connection pool", extra={
                    "pool_size": settings.DB_POOL_SIZE,
                    "max_overflow": settings.DB_MAX_OVERFLOW
                })
                
                self._pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=settings.DB_POOL_SIZE,
                    dsn=settings.DATABASE_URL,
                    cursor_factory=extras.RealDictCursor
                )
                
                self._initialized = True
                logger.info("Database connection pool initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}", exc_info=True)
                raise
    
    def get_connection(self):
        """
        Get a connection from the pool
        
        Returns:
            Database connection
            
        Raises:
            psycopg2.pool.PoolError: If pool is exhausted
        """
        try:
            conn = self._pool.getconn()
            logger.debug("Database connection acquired from pool")
            return conn
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}", exc_info=True)
            raise
    
    def return_connection(self, conn):
        """
        Return a connection to the pool
        
        Args:
            conn: Database connection to return
        """
        try:
            self._pool.putconn(conn)
            logger.debug("Database connection returned to pool")
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}", exc_info=True)
    
    def close_all_connections(self):
        """Close all connections in the pool (for shutdown)"""
        try:
            self._pool.closeall()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}", exc_info=True)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get the global database manager instance
    
    Returns:
        DatabaseManager singleton
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


@contextmanager
def get_db_connection() -> Generator:
    """
    Context manager for safe database connection handling
    Automatically returns connection to pool when done
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            
    Yields:
        Database connection
    """
    db_manager = get_db_manager()
    conn = None
    
    try:
        conn = db_manager.get_connection()
        yield conn
        
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error("Database error, transaction rolled back", exc_info=True)
        raise
        
    finally:
        if conn:
            db_manager.return_connection(conn)


@contextmanager
def get_db_cursor(commit: bool = False) -> Generator:
    """
    Context manager for database cursor with automatic connection handling
    
    Args:
        commit: Whether to commit transaction on success
        
    Usage:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("INSERT INTO users ...")
            
    Yields:
        Database cursor
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
                logger.debug("Database transaction committed")
        except Exception as e:
            conn.rollback()
            logger.error("Database error, transaction rolled back", exc_info=True)
            raise
        finally:
            cursor.close()


def init_database_tables():
    """
    Initialize database tables if they don't exist
    This should eventually be replaced by Alembic migrations
    """
    settings = get_settings()
    logger.info("Initializing database tables")
    
    tables_sql = """
    -- API Usage Tracking
    CREATE TABLE IF NOT EXISTS api_usage (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        operation VARCHAR(100) NOT NULL,
        model VARCHAR(100) NOT NULL,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost DECIMAL(10, 6) NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp 
    ON api_usage(timestamp DESC);
    
    -- Lesson Concepts (Phase 6)
    CREATE TABLE IF NOT EXISTS lesson_concepts (
        id SERIAL PRIMARY KEY,
        lesson_id UUID NOT NULL,
        concept_id VARCHAR(255) NOT NULL,
        concept_name TEXT NOT NULL,
        confidence DECIMAL(3, 2),
        similarity_score DECIMAL(5, 4),
        assigned_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(lesson_id, concept_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_lesson_concepts_lesson 
    ON lesson_concepts(lesson_id);
    
    CREATE INDEX IF NOT EXISTS idx_lesson_concepts_concept 
    ON lesson_concepts(concept_id);
    
    -- Chat Threads
    CREATE TABLE IF NOT EXISTS chat_threads (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        course_id UUID NOT NULL,
        lesson_id UUID NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        message_count INTEGER DEFAULT 0,
        UNIQUE(course_id, lesson_id)
    );
    
    -- Chat Messages
    CREATE TABLE IF NOT EXISTS chat_messages (
        id SERIAL PRIMARY KEY,
        thread_id UUID NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        tokens_input INTEGER,
        tokens_output INTEGER,
        cost DECIMAL(10, 6),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_chat_messages_thread 
    ON chat_messages(thread_id, created_at);
    
    -- Background Jobs
    CREATE TABLE IF NOT EXISTS background_jobs (
        id SERIAL PRIMARY KEY,
        job_type VARCHAR(50) NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        request_payload JSONB,
        response_result JSONB,
        error_message TEXT,
        conversation_id INTEGER,
        lesson_id UUID,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_background_jobs_status 
    ON background_jobs(status, created_at);
    
    -- Conversations (for claude_api.py)
    CREATE TABLE IF NOT EXISTS conversations (
        id SERIAL PRIMARY KEY,
        title TEXT,
        project_id VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- Messages (for claude_api.py)
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        status VARCHAR(20) DEFAULT 'completed',
        follow_up_question TEXT,
        citations JSONB,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cost DECIMAL(10, 6),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_messages_conversation 
    ON messages(conversation_id, created_at);
    
    -- YouTube Pending Links
    CREATE TABLE IF NOT EXISTS youtube_pending_links (
        id SERIAL PRIMARY KEY,
        youtube_url TEXT NOT NULL UNIQUE,
        video_title TEXT,
        channel TEXT,
        duration TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        document_id TEXT,
        chunks_count INTEGER,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(tables_sql)
        logger.info("Database tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        return False


def shutdown_database():
    """Shutdown database connection pool gracefully"""
    global _db_manager
    if _db_manager:
        _db_manager.close_all_connections()
        _db_manager = None
        logger.info("Database manager shutdown complete")

