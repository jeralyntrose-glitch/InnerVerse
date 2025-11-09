"""
Lesson Content Generator Service
Automatically generates educational content for lessons using Pinecone + Claude
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from anthropic import Anthropic
from pinecone import Pinecone
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor


class LessonContentGenerator:
    """Generates lesson content from Pinecone transcripts using Claude"""
    
    def __init__(
        self,
        database_url: str = None,
        anthropic_api_key: str = None,
        pinecone_api_key: str = None,
        openai_api_key: str = None
    ):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.anthropic_client = Anthropic(api_key=anthropic_api_key or os.getenv('ANTHROPIC_API_KEY'))
        self.openai_client = OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
        
        pinecone_client = Pinecone(api_key=pinecone_api_key or os.getenv('PINECONE_API_KEY'))
        self.index = pinecone_client.Index('mbti-knowledge-v2')
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
    
    def get_lesson_concepts(self, lesson_id: str) -> List[Dict[str, Any]]:
        """Get concepts assigned to a lesson"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT concept_id, confidence, similarity_score
                    FROM lesson_concepts
                    WHERE lesson_id = %s
                    ORDER BY similarity_score DESC
                """, (lesson_id,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=text,
            dimensions=3072
        )
        return response.data[0].embedding
    
    def search_transcripts(
        self,
        lesson_title: str,
        lesson_description: str,
        concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search Pinecone for relevant transcript chunks"""
        search_text = f"{lesson_title}. {lesson_description}"
        if concepts:
            concept_names = [c['concept_id'] for c in concepts[:5]]
            search_text += f" {', '.join(concept_names)}"
        
        query_vector = self.generate_embedding(search_text)
        results = self.index.query(vector=query_vector, top_k=10, include_metadata=True)
        
        # Filter out concept embeddings, only get transcript chunks
        matches = [m for m in results['matches'] if m.get('metadata', {}).get('type') != 'concept']
        return matches
    
    def generate_content_from_chunks(
        self,
        lesson_title: str,
        lesson_description: str,
        chunks: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], float]:
        """
        Generate lesson content from transcript chunks using Claude
        
        Returns:
            Tuple of (content_html, cost_usd)
        """
        context_parts = []
        for i, chunk in enumerate(chunks[:8], 1):
            metadata = chunk.get('metadata', {})
            text = metadata.get('text', '')
            source = metadata.get('filename', 'Unknown')
            if text:
                context_parts.append(f"[Source {i}: {source}]\n{text}\n")
        
        if not context_parts:
            return None, 0.0
        
        context = "\n---\n".join(context_parts)
        
        prompt = f"""You are an expert MBTI educator creating structured lesson content.

LESSON TOPIC: {lesson_title}
LESSON DESCRIPTION: {lesson_description}

TRANSCRIPT EXCERPTS:
{context}

TASK: Create comprehensive, well-structured lesson content based on the transcript excerpts above. The content should:

1. **Be educational and engaging** - Teach the concept clearly
2. **Use proper HTML formatting** - Use <h3>, <h4>, <p>, <ul>, <li>, <strong> tags
3. **Include practical examples** - Real-world applications and scenarios
4. **Be 300-500 words** - Comprehensive but focused
5. **Match the lesson topic** - Stay on theme

Format the output as clean HTML (no outer <html> or <body> tags, just the content).

Begin with a brief introduction, then cover key points with subheadings, and conclude with practical takeaways."""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            cost = (response.usage.input_tokens * 3 / 1_000_000) + (response.usage.output_tokens * 15 / 1_000_000)
            
            return content, cost
            
        except Exception as e:
            print(f"❌ Error generating content: {str(e)}")
            return None, 0.0
    
    def save_lesson_content(self, lesson_id: str, content: str) -> bool:
        """Save generated content to database"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE lessons
                    SET lesson_content = %s
                    WHERE id = %s
                """, (content, lesson_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Error saving content: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def generate_for_lesson(self, lesson_id: str, lesson_title: str, lesson_description: str) -> Dict[str, Any]:
        """
        Generate content for a single lesson
        
        Returns:
            {
                "success": bool,
                "lesson_id": str,
                "lesson_title": str,
                "chunks_found": int,
                "content_generated": bool,
                "cost": float,
                "error": str (optional)
            }
        """
        try:
            # Get concepts for this lesson
            concepts = self.get_lesson_concepts(lesson_id)
            
            # Search for relevant transcript chunks
            chunks = self.search_transcripts(lesson_title, lesson_description, concepts)
            
            if not chunks:
                return {
                    "success": False,
                    "lesson_id": lesson_id,
                    "lesson_title": lesson_title,
                    "chunks_found": 0,
                    "content_generated": False,
                    "cost": 0.0,
                    "error": "No relevant transcript chunks found"
                }
            
            # Generate content from chunks
            content, cost = self.generate_content_from_chunks(lesson_title, lesson_description, chunks)
            
            if not content:
                return {
                    "success": False,
                    "lesson_id": lesson_id,
                    "lesson_title": lesson_title,
                    "chunks_found": len(chunks),
                    "content_generated": False,
                    "cost": cost,
                    "error": "Failed to generate content"
                }
            
            # Save to database
            saved = self.save_lesson_content(lesson_id, content)
            
            return {
                "success": saved,
                "lesson_id": lesson_id,
                "lesson_title": lesson_title,
                "chunks_found": len(chunks),
                "content_generated": True,
                "cost": cost,
                "error": None if saved else "Failed to save content"
            }
            
        except Exception as e:
            return {
                "success": False,
                "lesson_id": lesson_id,
                "lesson_title": lesson_title,
                "chunks_found": 0,
                "content_generated": False,
                "cost": 0.0,
                "error": str(e)
            }
    
    def generate_for_course(self, course_id: str) -> Dict[str, Any]:
        """
        Generate content for all lessons in a course
        
        Returns:
            {
                "success": bool,
                "course_id": str,
                "total_lessons": int,
                "generated": int,
                "skipped": int,
                "total_cost": float,
                "results": List[Dict]
            }
        """
        conn = self._get_db_connection()
        try:
            # Get all lessons for this course
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, description
                    FROM lessons
                    WHERE course_id = %s
                    ORDER BY order_index
                """, (course_id,))
                lessons = cursor.fetchall()
            
            if not lessons:
                return {
                    "success": False,
                    "course_id": course_id,
                    "total_lessons": 0,
                    "generated": 0,
                    "skipped": 0,
                    "total_cost": 0.0,
                    "results": [],
                    "error": "No lessons found for course"
                }
            
            results = []
            generated_count = 0
            skipped_count = 0
            total_cost = 0.0
            
            for lesson in lessons:
                result = self.generate_for_lesson(
                    lesson['id'],
                    lesson['title'],
                    lesson.get('description', '')
                )
                
                results.append(result)
                
                if result['success']:
                    generated_count += 1
                    total_cost += result['cost']
                else:
                    skipped_count += 1
            
            return {
                "success": True,
                "course_id": course_id,
                "total_lessons": len(lessons),
                "generated": generated_count,
                "skipped": skipped_count,
                "total_cost": total_cost,
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "course_id": course_id,
                "total_lessons": 0,
                "generated": 0,
                "skipped": 0,
                "total_cost": 0.0,
                "results": [],
                "error": str(e)
            }
        finally:
            conn.close()
