"""
Concept Assigner Service
========================
Automatically assigns relevant knowledge graph concepts to lessons using:
- Vector similarity from Pinecone (70% weight)
- Prominence in title/description (30% weight)
"""

import logging
from typing import List, Dict, Tuple, Any, Optional
from pinecone import Pinecone
import openai
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class ConceptAssigner:
    """Assigns knowledge graph concepts to lessons using semantic search."""
    
    VECTOR_WEIGHT = 0.70
    PROMINENCE_WEIGHT = 0.30
    
    def __init__(
        self,
        database_url: str,
        pinecone_api_key: str,
        pinecone_index_name: str,
        openai_api_key: str
    ):
        """Initialize ConceptAssigner with API clients."""
        self.database_url = database_url
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.pinecone_index = self.pc.Index(pinecone_index_name)
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        
    def _get_db_connection(self):
        """Get PostgreSQL database connection."""
        return psycopg2.connect(self.database_url)
    
    def create_embedding(self, text: str) -> List[float]:
        """Create OpenAI embedding for text."""
        response = openai.embeddings.create(
            input=text,
            model="text-embedding-3-large"
        )
        return response.data[0].embedding
    
    def calculate_prominence_score(
        self,
        concept_name: str,
        lesson_title: str,
        lesson_description: str
    ) -> float:
        """Calculate prominence score based on concept name appearing in title/description."""
        concept_lower = concept_name.lower()
        title_lower = lesson_title.lower()
        desc_lower = (lesson_description or '').lower()
        
        score = 0.0
        
        if concept_lower in title_lower:
            score = 1.0
        elif concept_lower in desc_lower:
            score = 0.7
        elif any(word in title_lower for word in concept_lower.split()):
            score = 0.5
        elif any(word in desc_lower for word in concept_lower.split()):
            score = 0.3
        
        return score
    
    def assign_concepts_to_lesson(
        self,
        lesson_id: str,
        lesson_title: str,
        lesson_description: str,
        min_concepts: int = 3,
        max_concepts: int = 10,
        min_similarity: float = 0.65
    ) -> Dict[str, Any]:
        """
        Assign relevant concepts to a single lesson.
        
        Args:
            lesson_id: Lesson UUID
            lesson_title: Lesson title
            lesson_description: Lesson description  
            min_concepts: Minimum concepts to assign (default 3)
            max_concepts: Maximum concepts to assign (default 10)
            min_similarity: Minimum similarity threshold (default 0.65)
            
        Returns:
            {
                "success": bool,
                "lesson_id": str,
                "concepts_assigned": int,
                "concept_ids": List[str],
                "cost": float
            }
        """
        try:
            query_text = f"{lesson_title}. {lesson_description or ''}"
            
            embedding = self.create_embedding(query_text)
            embedding_cost = (len(query_text.split()) / 1000) * 0.00013
            
            results = self.pinecone_index.query(
                vector=embedding,
                filter={"type": "concept"},
                top_k=30,
                include_metadata=True
            )
            
            if not results.get('matches'):
                logger.warning(f"No concept matches found for lesson {lesson_id}")
                return {
                    "success": False,
                    "lesson_id": lesson_id,
                    "concepts_assigned": 0,
                    "concept_ids": [],
                    "cost": embedding_cost,
                    "error": "No matching concepts found"
                }
            
            scored_concepts = []
            for match in results['matches']:
                vector_sim = match['score']
                
                if vector_sim < min_similarity:
                    continue
                
                concept_id = match['id']
                concept_name = match.get('metadata', {}).get('name', concept_id)
                
                prominence = self.calculate_prominence_score(
                    concept_name,
                    lesson_title,
                    lesson_description or ''
                )
                
                composite_score = (
                    self.VECTOR_WEIGHT * vector_sim +
                    self.PROMINENCE_WEIGHT * prominence
                )
                
                if vector_sim >= 0.85 or prominence >= 0.7:
                    confidence = 'high'
                elif vector_sim >= 0.75 or prominence >= 0.5:
                    confidence = 'medium'
                else:
                    confidence = 'low'
                
                scored_concepts.append({
                    'concept_id': concept_id,
                    'concept_name': concept_name,
                    'composite_score': composite_score,
                    'vector_similarity': vector_sim,
                    'prominence': prominence,
                    'confidence': confidence
                })
            
            scored_concepts.sort(key=lambda x: x['composite_score'], reverse=True)
            
            num_to_assign = min(max_concepts, max(min_concepts, len(scored_concepts)))
            concepts_to_assign = scored_concepts[:num_to_assign]
            
            conn = self._get_db_connection()
            try:
                with conn.cursor() as cursor:
                    for idx, concept in enumerate(concepts_to_assign):
                        cursor.execute(
                            """
                            INSERT INTO lesson_concepts 
                                (lesson_id, concept_id, confidence, similarity_score, metadata_overlap_score, assignment_rank)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (lesson_id, concept_id) 
                            DO UPDATE SET
                                confidence = EXCLUDED.confidence,
                                similarity_score = EXCLUDED.similarity_score,
                                metadata_overlap_score = EXCLUDED.metadata_overlap_score,
                                assignment_rank = EXCLUDED.assignment_rank
                            """,
                            (
                                lesson_id,
                                concept['concept_id'],
                                concept['confidence'],
                                concept['vector_similarity'],
                                concept['prominence'],
                                idx + 1
                            )
                        )
                    conn.commit()
                    
                logger.info(
                    f"✅ Assigned {len(concepts_to_assign)} concepts to lesson {lesson_id}: "
                    f"{[c['concept_name'][:30] for c in concepts_to_assign[:3]]}"
                )
                
                return {
                    "success": True,
                    "lesson_id": lesson_id,
                    "concepts_assigned": len(concepts_to_assign),
                    "concept_ids": [c['concept_id'] for c in concepts_to_assign],
                    "cost": embedding_cost
                }
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Failed to assign concepts to lesson {lesson_id}: {str(e)}")
            return {
                "success": False,
                "lesson_id": lesson_id,
                "concepts_assigned": 0,
                "concept_ids": [],
                "cost": 0.0,
                "error": str(e)
            }
    
    def assign_concepts_to_course(
        self,
        course_id: str
    ) -> Dict[str, Any]:
        """
        Assign concepts to all lessons in a course.
        
        Args:
            course_id: Course UUID
            
        Returns:
            {
                "success": bool,
                "course_id": str,
                "lessons_processed": int,
                "total_concepts_assigned": int,
                "cost": float
            }
        """
        try:
            conn = self._get_db_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT id, title, description
                        FROM lessons
                        WHERE course_id = %s
                        ORDER BY order_index ASC
                        """,
                        (course_id,)
                    )
                    lessons = cursor.fetchall()
            finally:
                conn.close()
            
            if not lessons:
                logger.warning(f"No lessons found for course {course_id}")
                return {
                    "success": False,
                    "course_id": course_id,
                    "lessons_processed": 0,
                    "total_concepts_assigned": 0,
                    "cost": 0.0,
                    "error": "No lessons found in course"
                }
            
            total_cost = 0.0
            total_concepts = 0
            lessons_processed = 0
            
            for lesson in lessons:
                result = self.assign_concepts_to_lesson(
                    lesson_id=lesson['id'],
                    lesson_title=lesson['title'],
                    lesson_description=lesson['description']
                )
                
                if result['success']:
                    lessons_processed += 1
                    total_concepts += result['concepts_assigned']
                    total_cost += result['cost']
                else:
                    logger.warning(
                        f"Failed to assign concepts to lesson {lesson['id']}: "
                        f"{result.get('error', 'Unknown error')}"
                    )
            
            logger.info(
                f"✅ Concept assignment complete for course {course_id}: "
                f"{lessons_processed} lessons, {total_concepts} concepts, ${total_cost:.4f}"
            )
            
            return {
                "success": True,
                "course_id": course_id,
                "lessons_processed": lessons_processed,
                "total_concepts_assigned": total_concepts,
                "cost": total_cost
            }
            
        except Exception as e:
            logger.error(f"Failed to assign concepts to course {course_id}: {str(e)}")
            return {
                "success": False,
                "course_id": course_id,
                "lessons_processed": 0,
                "total_concepts_assigned": 0,
                "cost": 0.0,
                "error": str(e)
            }
