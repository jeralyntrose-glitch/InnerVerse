"""
InnerVerse Learning Paths - Course Manager
===========================================
Handles all business logic for courses, lessons, and user progress using PostgreSQL.

Usage:
    from src.services.course_manager import CourseManager
    
    manager = CourseManager(database_url)
    course = manager.create_course(title="ENFP Mastery", category="your_type")
"""

import psycopg2
import psycopg2.extras
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any


class CourseManager:
    """Manages courses, lessons, and user progress for InnerVerse Learning Paths."""
    
    def __init__(self, database_url: str):
        """
        Initialize CourseManager with PostgreSQL connection.
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        
    def _get_connection(self):
        """Get PostgreSQL database connection."""
        return psycopg2.connect(self.database_url)
    
    def _generate_id(self) -> str:
        """Generate UUID for new records."""
        return str(uuid.uuid4())
    
    def _now(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat() + 'Z'
    
    # ========================================================================
    # COURSE CRUD OPERATIONS
    # ========================================================================
    
    def create_course(
        self,
        title: str,
        category: str,
        description: Optional[str] = None,
        estimated_hours: float = 0,
        auto_generated: bool = True,
        generation_prompt: Optional[str] = None,
        source_type: str = 'manual',
        source_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new course (learning track).
        
        Args:
            title: Course title (e.g., "ENFP Mastery")
            category: One of: foundations, your_type, relationships, advanced
            description: Course description
            estimated_hours: Total estimated hours to complete
            auto_generated: Whether AI generated this course
            generation_prompt: Prompt used for AI generation
            source_type: One of: chat, graph, atlas, manual
            source_ids: List of source document/concept IDs
            tags: List of tags for organization
            notes: User notes about the course
            
        Returns:
            Dict with course data including new ID
        """
        valid_categories = ['foundations', 'your_type', 'relationships', 'advanced']
        if category not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        
        course_id = self._generate_id()
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO courses (
                        id, title, category, description, estimated_hours,
                        auto_generated, generation_prompt, source_type, source_ids,
                        tags, notes, status, lesson_count, total_concepts
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', 0, 0
                    )
                    RETURNING *
                """, (
                    course_id, title, category, description, estimated_hours,
                    auto_generated, generation_prompt, source_type,
                    json.dumps(source_ids or []), json.dumps(tags or []), notes
                ))
                
                result = cur.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
                course = cur.fetchone()
                
            conn.commit()
            return dict(course) if course else None
            
        finally:
            conn.close()
    
    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a course by ID.
        
        Args:
            course_id: Course UUID
            
        Returns:
            Course dict or None if not found
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
                course = cur.fetchone()
                return dict(course) if course else None
        finally:
            conn.close()
    
    def list_courses(
        self, 
        category: str = None, 
        status: str = 'active',
        user_id: str = 'jeralyn'
    ) -> List[Dict[str, Any]]:
        """
        List all courses, optionally filtered by category and status.
        
        Args:
            category: Filter by category (optional)
            status: Filter by status (default: 'active')
            user_id: User ID for progress data
            
        Returns:
            List of course dicts with progress info
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                query = """
                    SELECT 
                        c.*,
                        up.current_lesson_id,
                        up.completed_lesson_ids,
                        up.total_time_minutes,
                        up.last_accessed
                    FROM courses c
                    LEFT JOIN user_progress up ON c.id = up.course_id AND up.user_id = %s
                    WHERE c.status = %s
                """
                params = [user_id, status]
                
                if category:
                    query += " AND c.category = %s"
                    params.append(category)
                
                query += " ORDER BY c.created_at DESC"
                
                cur.execute(query, params)
                courses = cur.fetchall()
                return [dict(course) for course in courses]
        finally:
            conn.close()
    
    def update_course(self, course_id: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update a course.
        
        Args:
            course_id: Course UUID
            **updates: Fields to update
            
        Returns:
            Updated course dict or None
        """
        if not updates:
            return self.get_course(course_id)
        
        allowed_fields = {
            'title', 'category', 'description', 'estimated_hours',
            'generation_prompt', 'source_type', 'source_ids', 'tags',
            'status', 'notes', 'custom_order'
        }
        
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not updates:
            return self.get_course(course_id)
        
        # Serialize JSONB fields
        jsonb_fields = {'source_ids', 'tags'}
        for field in jsonb_fields:
            if field in updates and updates[field] is not None:
                updates[field] = json.dumps(updates[field])
        
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [course_id]
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"""
                    UPDATE courses 
                    SET {set_clause}
                    WHERE id = %s
                    RETURNING *
                """, values)
                
                course = cur.fetchone()
                
            conn.commit()
            return dict(course) if course else None
        finally:
            conn.close()
    
    def delete_course(self, course_id: str) -> bool:
        """
        Soft delete a course (sets status to 'deleted').
        
        Args:
            course_id: Course UUID
            
        Returns:
            True if successful
        """
        return self.update_course(course_id, status='deleted') is not None
    
    # ========================================================================
    # LESSON CRUD OPERATIONS
    # ========================================================================
    
    def create_lesson(
        self,
        course_id: str,
        title: str,
        concept_ids: List[str],
        description: Optional[str] = None,
        order_index: Optional[int] = None,
        prerequisite_lesson_ids: Optional[List[str]] = None,
        estimated_minutes: int = 30,
        difficulty: str = 'foundational',
        video_references: Optional[List[Dict]] = None,
        document_references: Optional[List[str]] = None,
        learning_objectives: Optional[str] = None,
        key_takeaways: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new lesson within a course.
        
        Args:
            course_id: Parent course UUID
            title: Lesson title
            concept_ids: List of knowledge graph concept UUIDs
            description: Lesson description
            order_index: Position in course (auto-increments if not provided)
            prerequisite_lesson_ids: Required lessons before this one
            estimated_minutes: Time to complete
            difficulty: foundational, intermediate, or advanced
            video_references: List of video reference dicts
            document_references: List of document UUIDs
            learning_objectives: What students will learn
            key_takeaways: Important points to remember
            
        Returns:
            Dict with lesson data including new ID
        """
        if not concept_ids:
            raise ValueError("At least one concept_id is required")
        
        lesson_id = self._generate_id()
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Auto-increment order_index if not provided
                if order_index is None:
                    cur.execute("""
                        SELECT COALESCE(MAX(order_index), 0) + 1 as next_index
                        FROM lessons 
                        WHERE course_id = %s
                    """, (course_id,))
                    result = cur.fetchone()
                    order_index = result['next_index'] if result else 1
                
                cur.execute("""
                    INSERT INTO lessons (
                        id, course_id, title, description, order_index,
                        concept_ids, prerequisite_lesson_ids, estimated_minutes,
                        difficulty, video_references, document_references,
                        learning_objectives, key_takeaways
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING *
                """, (
                    lesson_id, course_id, title, description, order_index,
                    json.dumps(concept_ids), 
                    json.dumps(prerequisite_lesson_ids or []),
                    estimated_minutes, difficulty,
                    json.dumps(video_references or []),
                    json.dumps(document_references or []),
                    learning_objectives, key_takeaways
                ))
                
                lesson = cur.fetchone()
                
            conn.commit()
            return dict(lesson) if lesson else None
        finally:
            conn.close()
    
    def get_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get a lesson by ID."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM lessons WHERE id = %s", (lesson_id,))
                lesson = cur.fetchone()
                return dict(lesson) if lesson else None
        finally:
            conn.close()
    
    def list_lessons(self, course_id: str) -> List[Dict[str, Any]]:
        """
        List all lessons for a course, ordered by order_index.
        
        Args:
            course_id: Course UUID
            
        Returns:
            List of lesson dicts
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM lessons 
                    WHERE course_id = %s 
                    ORDER BY order_index ASC
                """, (course_id,))
                lessons = cur.fetchall()
                return [dict(lesson) for lesson in lessons]
        finally:
            conn.close()
    
    def update_lesson(self, lesson_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update a lesson."""
        if not updates:
            return self.get_lesson(lesson_id)
        
        allowed_fields = {
            'title', 'description', 'order_index', 'concept_ids',
            'prerequisite_lesson_ids', 'estimated_minutes', 'difficulty',
            'video_references', 'document_references',
            'learning_objectives', 'key_takeaways'
        }
        
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not updates:
            return self.get_lesson(lesson_id)
        
        # Serialize JSONB fields
        jsonb_fields = {
            'concept_ids', 'prerequisite_lesson_ids', 
            'video_references', 'document_references'
        }
        for field in jsonb_fields:
            if field in updates and updates[field] is not None:
                updates[field] = json.dumps(updates[field])
        
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [lesson_id]
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"""
                    UPDATE lessons 
                    SET {set_clause}
                    WHERE id = %s
                    RETURNING *
                """, values)
                
                lesson = cur.fetchone()
                
            conn.commit()
            return dict(lesson) if lesson else None
        finally:
            conn.close()
    
    def delete_lesson(self, lesson_id: str) -> bool:
        """
        Delete a lesson permanently.
        
        Args:
            lesson_id: Lesson UUID
            
        Returns:
            True if successful
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lessons WHERE id = %s", (lesson_id,))
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()
    
    # ========================================================================
    # USER PROGRESS OPERATIONS
    # ========================================================================
    
    def get_or_create_progress(
        self, 
        course_id: str, 
        user_id: str = 'jeralyn'
    ) -> Dict[str, Any]:
        """
        Get or create user progress for a course.
        
        Args:
            course_id: Course UUID
            user_id: User identifier
            
        Returns:
            User progress dict
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Try to get existing progress
                cur.execute("""
                    SELECT * FROM user_progress 
                    WHERE user_id = %s AND course_id = %s
                """, (user_id, course_id))
                
                progress = cur.fetchone()
                
                if progress:
                    return dict(progress)
                
                # Create new progress record
                progress_id = self._generate_id()
                cur.execute("""
                    INSERT INTO user_progress (
                        id, user_id, course_id, completed_lesson_ids,
                        started_at, lesson_completion_dates, notes,
                        flagged_for_review, ai_validation_status
                    ) VALUES (
                        %s, %s, %s, %s, NOW(), %s, %s, %s, %s
                    )
                    RETURNING *
                """, (
                    progress_id, user_id, course_id, json.dumps([]),
                    json.dumps({}), json.dumps({}), json.dumps([]), json.dumps({})
                ))
                
                progress = cur.fetchone()
                
            conn.commit()
            return dict(progress) if progress else None
        finally:
            conn.close()
    
    def update_progress(
        self,
        course_id: str,
        user_id: str = 'jeralyn',
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        Update user progress for a course.
        
        Args:
            course_id: Course UUID
            user_id: User identifier
            **updates: Fields to update
            
        Returns:
            Updated progress dict
        """
        # Ensure progress exists
        self.get_or_create_progress(course_id, user_id)
        
        allowed_fields = {
            'current_lesson_id', 'completed_lesson_ids', 'last_accessed',
            'completed_at', 'total_time_minutes', 'lesson_completion_dates',
            'notes', 'flagged_for_review', 'ai_validation_status'
        }
        
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not updates:
            return self.get_or_create_progress(course_id, user_id)
        
        # Auto-update last_accessed
        updates['last_accessed'] = datetime.utcnow()
        
        # Serialize JSONB fields
        jsonb_fields = {
            'completed_lesson_ids', 'lesson_completion_dates', 
            'notes', 'flagged_for_review', 'ai_validation_status'
        }
        for field in jsonb_fields:
            if field in updates and updates[field] is not None:
                updates[field] = json.dumps(updates[field])
        
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [user_id, course_id]
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"""
                    UPDATE user_progress 
                    SET {set_clause}
                    WHERE user_id = %s AND course_id = %s
                    RETURNING *
                """, values)
                
                progress = cur.fetchone()
                
            conn.commit()
            return dict(progress) if progress else None
        finally:
            conn.close()
    
    def mark_lesson_complete(
        self,
        course_id: str,
        lesson_id: str,
        user_id: str = 'jeralyn'
    ) -> Dict[str, Any]:
        """
        Mark a lesson as completed.
        
        Args:
            course_id: Course UUID
            lesson_id: Lesson UUID
            user_id: User identifier
            
        Returns:
            Updated progress dict
        """
        progress = self.get_or_create_progress(course_id, user_id)
        
        # Get JSONB fields (already parsed by RealDictCursor)
        completed_ids = progress.get('completed_lesson_ids', [])
        completion_dates = progress.get('lesson_completion_dates', {})
        
        # Ensure they're the right type (in case of None)
        if not isinstance(completed_ids, list):
            completed_ids = []
        if not isinstance(completion_dates, dict):
            completion_dates = {}
        
        # Add lesson to completed list if not already there
        if lesson_id not in completed_ids:
            completed_ids.append(lesson_id)
            completion_dates[lesson_id] = self._now()
        
        return self.update_progress(
            course_id,
            user_id,
            completed_lesson_ids=completed_ids,
            lesson_completion_dates=completion_dates
        )
    
    # ========================================================================
    # STATS & ANALYTICS
    # ========================================================================
    
    def get_stats(self, user_id: str = 'jeralyn') -> Dict[str, Any]:
        """
        Get system-wide statistics for Learning Paths.
        
        Args:
            user_id: User identifier for personalized stats
            
        Returns:
            Dict with comprehensive statistics
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Course counts by category
                cur.execute("""
                    SELECT 
                        category,
                        COUNT(*) as count,
                        SUM(lesson_count) as total_lessons,
                        SUM(estimated_hours) as total_hours
                    FROM courses
                    WHERE status = 'active'
                    GROUP BY category
                """)
                categories = [dict(row) for row in cur.fetchall()]
                
                # Overall totals
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_courses,
                        SUM(lesson_count) as total_lessons,
                        SUM(estimated_hours) as total_hours
                    FROM courses
                    WHERE status = 'active'
                """)
                totals = dict(cur.fetchone())
                
                # User progress stats
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT course_id) as courses_started,
                        COUNT(DISTINCT course_id) FILTER (WHERE completed_at IS NOT NULL) as courses_completed,
                        SUM(total_time_minutes) as total_time_minutes,
                        COUNT(DISTINCT current_lesson_id) as active_lessons
                    FROM user_progress
                    WHERE user_id = %s
                """, (user_id,))
                user_stats = dict(cur.fetchone())
                
                # Recent activity
                cur.execute("""
                    SELECT 
                        c.id,
                        c.title,
                        c.category,
                        up.last_accessed,
                        up.current_lesson_id
                    FROM user_progress up
                    JOIN courses c ON up.course_id = c.id
                    WHERE up.user_id = %s AND up.last_accessed IS NOT NULL
                    ORDER BY up.last_accessed DESC
                    LIMIT 5
                """, (user_id,))
                recent_activity = [dict(row) for row in cur.fetchall()]
                
                return {
                    'by_category': categories,
                    'totals': totals,
                    'user_progress': user_stats,
                    'recent_activity': recent_activity
                }
        finally:
            conn.close()
