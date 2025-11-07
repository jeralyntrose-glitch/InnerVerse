"""
Background Job Service - Manages async processing jobs for PWA background support.

This service is completely isolated and doesn't touch existing chat functionality.
It provides job tracking for messages that continue processing when users leave the app.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class BackgroundJobService:
    """Service for managing background processing jobs."""
    
    def __init__(self):
        """Initialize the service with database connection."""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
    
    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.db_url)
    
    def create_job(
        self,
        job_type: str,
        request_payload: Dict[str, Any],
        conversation_id: Optional[int] = None,
        lesson_id: Optional[str] = None
    ) -> int:
        """
        Create a new background job.
        
        Args:
            job_type: Type of job ('main_chat' or 'lesson_chat')
            request_payload: The original request data (message, context, etc.)
            conversation_id: ID of the conversation (for main chat)
            lesson_id: ID of the lesson (for lesson chat)
        
        Returns:
            The new job ID
        
        Raises:
            ValueError: If both or neither conversation_id and lesson_id are provided
        """
        if (conversation_id is None and lesson_id is None) or (conversation_id is not None and lesson_id is not None):
            raise ValueError("Must provide exactly one of conversation_id or lesson_id")
        
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO background_jobs 
                (conversation_id, lesson_id, job_type, status, request_payload, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                conversation_id,
                lesson_id,
                job_type,
                'queued',
                json.dumps(request_payload)
            ))
            
            job_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"Created background job {job_id} of type {job_type}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error creating background job: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the status and details of a background job.
        
        Args:
            job_id: The job ID
        
        Returns:
            Dict with job details or None if not found
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    id,
                    conversation_id,
                    lesson_id,
                    job_type,
                    status,
                    request_payload,
                    response_content,
                    created_at,
                    completed_at,
                    error_message
                FROM background_jobs
                WHERE id = %s
            """, (job_id,))
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting job status for job {job_id}: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def update_job_status(self, job_id: int, status: str) -> bool:
        """
        Update the status of a background job.
        
        Args:
            job_id: The job ID
            status: New status ('queued', 'processing', 'completed', 'failed')
        
        Returns:
            True if successful, False otherwise
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE background_jobs
                SET status = %s
                WHERE id = %s
            """, (status, job_id))
            
            conn.commit()
            logger.info(f"Updated job {job_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating job status for job {job_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def complete_job(
        self,
        job_id: int,
        response_content: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Mark a job as completed with its response.
        
        Args:
            job_id: The job ID
            response_content: The AI response content
            error_message: Optional error message if job failed
        
        Returns:
            True if successful, False otherwise
        """
        status = 'failed' if error_message else 'completed'
        
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE background_jobs
                SET 
                    status = %s,
                    response_content = %s,
                    error_message = %s,
                    completed_at = NOW()
                WHERE id = %s
            """, (status, response_content, error_message, job_id))
            
            conn.commit()
            logger.info(f"Completed job {job_id} with status {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing job {job_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_pending_jobs(
        self,
        conversation_id: Optional[int] = None,
        lesson_id: Optional[str] = None
    ) -> list:
        """
        Get all pending jobs for a conversation or lesson.
        
        Args:
            conversation_id: Filter by conversation ID (for main chat)
            lesson_id: Filter by lesson ID (for lesson chat)
        
        Returns:
            List of pending job dicts
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if conversation_id is not None:
                cursor.execute("""
                    SELECT 
                        id, job_type, status, created_at
                    FROM background_jobs
                    WHERE conversation_id = %s AND status IN ('queued', 'processing')
                    ORDER BY created_at ASC
                """, (conversation_id,))
            elif lesson_id is not None:
                cursor.execute("""
                    SELECT 
                        id, job_type, status, created_at
                    FROM background_jobs
                    WHERE lesson_id = %s AND status IN ('queued', 'processing')
                    ORDER BY created_at ASC
                """, (lesson_id,))
            else:
                return []
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting pending jobs: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """
        Delete completed/failed jobs older than specified days.
        
        Args:
            days_old: Number of days to keep jobs
        
        Returns:
            Number of jobs deleted
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM background_jobs
                WHERE 
                    status IN ('completed', 'failed') AND
                    created_at < NOW() - INTERVAL '%s days'
            """, (days_old,))
            
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} old background jobs")
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
