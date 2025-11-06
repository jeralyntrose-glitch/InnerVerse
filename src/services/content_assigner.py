"""
InnerVerse Learning Paths - Content Assigner
=============================================
Automatically assigns new document content to existing learning tracks.

Uses 3-tier confidence system:
- High (90%+): Auto-add silently
- Medium (70-89%): Auto-add with reasoning shown
- Low (<70%): Create new track

Usage:
    from content_assigner import ContentAssigner
    
    assigner = ContentAssigner(
        anthropic_api_key="your-key",
        knowledge_graph_manager=kg_manager,
        course_manager=course_manager
    )
    
    assignment = assigner.assign_content(
        document_id="doc-uuid",
        extracted_concept_ids=["concept-1", "concept-2"]
    )
"""

import json
from typing import List, Dict, Optional, Any, Tuple
from anthropic import Anthropic
import logging

logger = logging.getLogger(__name__)


class ContentAssigner:
    """Assign new content to learning tracks using AI analysis."""
    
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.70
    
    def __init__(
        self,
        anthropic_api_key: str,
        knowledge_graph_manager,
        course_manager,
        model: str = "claude-sonnet-4-20250514"
    ):
        """Initialize ContentAssigner."""
        self.client = Anthropic(api_key=anthropic_api_key)
        self.kg_manager = knowledge_graph_manager
        self.course_manager = course_manager
        self.model = model
        self.assignment_cost = 0.0
    
    def assign_content(
        self,
        document_id: str,
        extracted_concept_ids: List[str],
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Assign new document content to an existing track or create new track."""
        if not extracted_concept_ids:
            raise ValueError("extracted_concept_ids cannot be empty")
        
        logger.info(f"Assigning content for document {document_id} with {len(extracted_concept_ids)} concepts")
        
        # Get all existing courses
        all_courses = self.course_manager.get_all_courses(include_archived=False)
        existing_courses = []
        for category_courses in all_courses.values():
            existing_courses.extend(category_courses)
        
        if not existing_courses:
            return self._create_new_track_recommendation(
                document_id=document_id,
                concept_ids=extracted_concept_ids,
                metadata=document_metadata
            )
        
        # Calculate concept overlap
        overlap_scores = self._calculate_overlap_scores(
            extracted_concept_ids,
            existing_courses
        )
        
        # Get top candidate
        best_course = max(overlap_scores, key=lambda x: x['overlap_percentage'])
        confidence = best_course['overlap_percentage'] / 100.0
        
        logger.info(f"Best match: {best_course['course_title']} ({confidence:.2%} confidence)")
        
        # Decide action based on confidence tier
        if confidence >= self.HIGH_CONFIDENCE:
            return self._high_confidence_assignment(
                document_id=document_id,
                concept_ids=extracted_concept_ids,
                course=best_course,
                confidence=confidence,
                metadata=document_metadata
            )
        
        elif confidence >= self.MEDIUM_CONFIDENCE:
            return self._medium_confidence_assignment(
                document_id=document_id,
                concept_ids=extracted_concept_ids,
                course=best_course,
                confidence=confidence,
                metadata=document_metadata
            )
        
        else:
            return self._create_new_track_recommendation(
                document_id=document_id,
                concept_ids=extracted_concept_ids,
                metadata=document_metadata,
                best_existing_match=best_course
            )
    
    def _calculate_overlap_scores(
        self,
        new_concept_ids: List[str],
        courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate concept overlap percentage for each course."""
        scores = []
        
        for course in courses:
            course_concept_ids = set()
            for lesson in course.get('lessons', []):
                course_concept_ids.update(lesson.get('concept_ids', []))
            
            if not course_concept_ids:
                continue
            
            new_concepts_set = set(new_concept_ids)
            overlap = new_concepts_set.intersection(course_concept_ids)
            overlap_percentage = (len(overlap) / len(new_concepts_set)) * 100 if new_concepts_set else 0
            
            scores.append({
                'course_id': course['id'],
                'course_title': course['title'],
                'course_category': course['category'],
                'course_concept_ids': list(course_concept_ids),
                'overlap_count': len(overlap),
                'new_concept_count': len(new_concepts_set),
                'overlap_percentage': overlap_percentage,
                'overlapping_concepts': list(overlap)
            })
        
        scores.sort(key=lambda x: x['overlap_percentage'], reverse=True)
        return scores
    
    def _high_confidence_assignment(
        self,
        document_id: str,
        concept_ids: List[str],
        course: Dict[str, Any],
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle high confidence assignment (90%+ overlap) - no API call."""
        existing_lessons = self.course_manager.list_lessons(course['course_id'])
        next_order = len(existing_lessons) + 1
        
        lesson_title = self._generate_lesson_title(metadata, concept_ids)
        
        return {
            'action': 'add_to_existing',
            'course_id': course['course_id'],
            'course_title': course['course_title'],
            'confidence': confidence,
            'confidence_tier': 'high',
            'reasoning': f"High confidence match ({confidence:.0%} concept overlap). Auto-added.",
            'suggested_lesson': {
                'title': lesson_title,
                'order_index': next_order,
                'concept_ids': concept_ids,
                'description': f"Content from {metadata.get('title', document_id) if metadata else document_id}",
                'estimated_minutes': metadata.get('duration_minutes', 30) if metadata else 30,
                'difficulty': self._infer_difficulty(next_order),
                'document_references': [document_id]
            },
            'prerequisite_check': {
                'valid': True,
                'issues': []
            },
            'cost': 0.0
        }
    
    def _medium_confidence_assignment(
        self,
        document_id: str,
        concept_ids: List[str],
        course: Dict[str, Any],
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle medium confidence assignment (70-89% overlap) - uses Claude for reasoning."""
        try:
            reasoning_response = self._generate_assignment_reasoning(
                concept_ids=concept_ids,
                course=course,
                confidence=confidence
            )
            
            reasoning = reasoning_response['reasoning']
            cost = reasoning_response['cost']
            self.assignment_cost += cost
            
        except Exception as e:
            logger.error(f"Failed to generate reasoning: {str(e)}")
            reasoning = f"Medium confidence match ({confidence:.0%} overlap). Manual review recommended."
            cost = 0.0
        
        existing_lessons = self.course_manager.list_lessons(course['course_id'])
        next_order = len(existing_lessons) + 1
        
        lesson_title = self._generate_lesson_title(metadata, concept_ids)
        
        return {
            'action': 'add_to_existing',
            'course_id': course['course_id'],
            'course_title': course['course_title'],
            'confidence': confidence,
            'confidence_tier': 'medium',
            'reasoning': reasoning,
            'suggested_lesson': {
                'title': lesson_title,
                'order_index': next_order,
                'concept_ids': concept_ids,
                'description': f"Content from {metadata.get('title', document_id) if metadata else document_id}",
                'estimated_minutes': metadata.get('duration_minutes', 30) if metadata else 30,
                'difficulty': self._infer_difficulty(next_order),
                'document_references': [document_id]
            },
            'prerequisite_check': {
                'valid': True,
                'issues': []
            },
            'cost': cost
        }
    
    def _create_new_track_recommendation(
        self,
        document_id: str,
        concept_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        best_existing_match: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Recommend creating a new track (low confidence or no existing courses)."""
        concept_names = []
        for cid in concept_ids[:5]:
            concept = self.kg_manager.get_concept(cid)
            if concept:
                concept_names.append(concept.get('name', ''))
        
        suggested_title = f"Learning Path: {', '.join(concept_names[:3])}"
        if metadata and metadata.get('title'):
            suggested_title = f"Learning Path: {metadata['title']}"
        
        reasoning = "Low confidence match with existing tracks. Creating new track recommended."
        if best_existing_match:
            reasoning += f" Best existing match was '{best_existing_match['course_title']}' at {best_existing_match['overlap_percentage']:.0f}% overlap."
        
        return {
            'action': 'create_new',
            'course_id': None,
            'course_title': suggested_title,
            'confidence': 0.0,
            'confidence_tier': 'low',
            'reasoning': reasoning,
            'suggested_course': {
                'title': suggested_title,
                'category': 'foundations',
                'description': f"New learning track based on {metadata.get('title', document_id) if metadata else document_id}",
                'tags': self._extract_tags_from_concepts(concept_ids),
                'estimated_hours': 1.0
            },
            'suggested_lesson': {
                'title': metadata.get('title', 'Introduction') if metadata else 'Introduction',
                'order_index': 1,
                'concept_ids': concept_ids,
                'description': "First lesson in new track",
                'estimated_minutes': metadata.get('duration_minutes', 30) if metadata else 30,
                'difficulty': 'foundational',
                'document_references': [document_id]
            },
            'cost': 0.0
        }
    
    def _generate_assignment_reasoning(
        self,
        concept_ids: List[str],
        course: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """Generate detailed reasoning for medium confidence assignments."""
        concept_names = []
        for cid in concept_ids:
            concept = self.kg_manager.get_concept(cid)
            if concept:
                concept_names.append(concept.get('name', cid))
        
        overlapping_ids = set(concept_ids).intersection(set(course['course_concept_ids']))
        overlapping_names = []
        for cid in overlapping_ids:
            concept = self.kg_manager.get_concept(cid)
            if concept:
                overlapping_names.append(concept.get('name', cid))
        
        prompt = f"""You are analyzing whether new content should be added to an existing learning track.

NEW CONTENT CONCEPTS:
{', '.join(concept_names)}

EXISTING TRACK: "{course['course_title']}"
Category: {course['course_category']}

OVERLAP ANALYSIS:
- {len(overlapping_ids)}/{len(concept_ids)} concepts match ({confidence:.0%})
- Matching concepts: {', '.join(overlapping_names[:10])}

TASK: Provide a 1-2 sentence reasoning for why this content fits (or doesn't fit) in this track.

Be specific about which concepts create the connection. Keep it concise and actionable.

Reasoning:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            reasoning = response.content[0].text.strip()
            
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            return {
                'reasoning': reasoning,
                'cost': cost
            }
            
        except Exception as e:
            logger.error(f"Claude reasoning generation failed: {str(e)}")
            raise
    
    def _generate_lesson_title(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        concept_ids: Optional[List[str]] = None
    ) -> str:
        """Generate a lesson title from metadata or concepts."""
        if metadata and metadata.get('title'):
            return metadata['title']
        
        if metadata and metadata.get('video_id'):
            return f"Lesson: {metadata['video_id']}"
        
        if concept_ids:
            concept = self.kg_manager.get_concept(concept_ids[0])
            if concept:
                return f"Understanding {concept.get('name', 'Concepts')}"
        
        return "New Lesson"
    
    def _infer_difficulty(self, order_index: int) -> str:
        """Infer difficulty based on lesson position."""
        if order_index <= 3:
            return 'foundational'
        elif order_index <= 8:
            return 'intermediate'
        else:
            return 'advanced'
    
    def _extract_tags_from_concepts(self, concept_ids: List[str]) -> List[str]:
        """Extract tags from concept categories."""
        tags = set()
        for cid in concept_ids[:10]:
            concept = self.kg_manager.get_concept(cid)
            if concept and concept.get('category'):
                tags.add(concept['category'].lower())
        return list(tags)[:5]
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost of Claude API call."""
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost
    
    def get_total_cost(self) -> float:
        """Get total cost of all assignments in this session."""
        return self.assignment_cost
    
    def reset_cost_tracking(self):
        """Reset cost tracking to zero."""
        self.assignment_cost = 0.0
