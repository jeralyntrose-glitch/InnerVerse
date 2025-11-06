"""
InnerVerse Learning Paths - Course Generator
=============================================
Generates structured learning paths from knowledge graph using Claude AI.

Usage:
    from course_generator import CourseGenerator
    
    generator = CourseGenerator(
        anthropic_api_key="your-key",
        knowledge_graph_manager=kg_manager
    )
    
    course_data = generator.generate_curriculum(
        user_goal="Learn ENFP shadow integration",
        relevant_concept_ids=["concept-uuid-1", "concept-uuid-2"]
    )
"""

import json
from typing import List, Dict, Optional, Any
from anthropic import Anthropic
import logging

logger = logging.getLogger(__name__)


class CourseGenerator:
    """Generate course curricula using Claude AI and knowledge graph."""
    
    def __init__(
        self,
        anthropic_api_key: str,
        knowledge_graph_manager,
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        Initialize CourseGenerator.
        
        Args:
            anthropic_api_key: Anthropic API key
            knowledge_graph_manager: Instance of KnowledgeGraphManager
            model: Claude model to use
        """
        self.client = Anthropic(api_key=anthropic_api_key)
        self.kg_manager = knowledge_graph_manager
        self.model = model
        self.generation_cost = 0.0
    
    def generate_curriculum(
        self,
        user_goal: str,
        relevant_concept_ids: Optional[List[str]] = None,
        max_lessons: int = 15,
        target_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete course curriculum from user goal.
        
        Args:
            user_goal: What the user wants to learn
            relevant_concept_ids: Optional list of concept IDs to focus on
            max_lessons: Maximum number of lessons to generate
            target_category: Optional category hint
            
        Returns:
            Dict with course structure including lessons
        """
        if not user_goal or not user_goal.strip():
            raise ValueError("user_goal cannot be empty")
        
        logger.info(f"Generating curriculum for goal: {user_goal}")
        
        # Step 1: Get relevant concepts from knowledge graph
        if relevant_concept_ids:
            concepts = self._get_concepts_by_ids(relevant_concept_ids)
        else:
            concepts = self._search_concepts_by_goal(user_goal)
        
        if not concepts:
            raise ValueError("No relevant concepts found in knowledge graph for this goal")
        
        # Step 2: Get prerequisite relationships
        prerequisite_data = self._build_prerequisite_map(concepts)
        
        # Step 3: Build prompt with knowledge graph context
        prompt = self._build_generation_prompt(
            user_goal=user_goal,
            concepts=concepts,
            prerequisite_data=prerequisite_data,
            max_lessons=max_lessons,
            target_category=target_category
        )
        
        # Step 4: Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Track cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)
            self.generation_cost += cost
            
            logger.info(f"Claude API call: {input_tokens} input, {output_tokens} output tokens. Cost: ${cost:.4f}")
            
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise Exception(f"Failed to generate curriculum: {str(e)}")
        
        # Step 5: Parse response
        # Extract text from response content blocks
        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text = block.text
                break
        
        if not response_text:
            raise Exception("No text content in Claude response")
        
        curriculum = self._parse_claude_response(response_text)
        
        # Step 6: Validate and enhance curriculum
        curriculum = self._validate_curriculum(curriculum, concepts)
        
        # Step 7: Add metadata
        curriculum['source_ids'] = [c['id'] for c in concepts]
        curriculum['generation_metadata'] = {
            'model': self.model,
            'cost': cost,
            'concepts_analyzed': len(concepts),
            'user_goal': user_goal
        }
        
        logger.info(f"Generated curriculum: {curriculum['title']} with {len(curriculum['lessons'])} lessons")
        
        return curriculum
    
    def _get_concepts_by_ids(self, concept_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch concepts from knowledge graph by IDs."""
        concepts = []
        for concept_id in concept_ids:
            concept = self.kg_manager.get_concept(concept_id)
            if concept:
                concepts.append(concept)
        return concepts
    
    def _search_concepts_by_goal(self, user_goal: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Search knowledge graph for concepts relevant to user goal."""
        try:
            results = self.kg_manager.search_concepts(
                query=user_goal,
                top_k=limit
            )
            
            concepts = []
            for result in results:
                concept = {
                    'id': result.get('id'),
                    'name': result.get('name'),
                    'definition': result.get('definition', ''),
                    'category': result.get('category', ''),
                    'related_concepts': result.get('related_concepts', [])
                }
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"Knowledge graph search error: {str(e)}")
            return []
    
    def _build_prerequisite_map(self, concepts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build prerequisite relationships between concepts."""
        prereq_map = {}
        
        for concept in concepts:
            concept_id = concept['id']
            prereq_map[concept_id] = {
                'name': concept['name'],
                'prerequisites': [],
                'dependents': []
            }
            
            related = concept.get('related_concepts', [])
            for rel in related:
                if rel.get('relationship_type') == 'prerequisite':
                    prereq_map[concept_id]['prerequisites'].append(rel['target_id'])
        
        # Build reverse map (dependents)
        for concept_id, data in prereq_map.items():
            for prereq_id in data['prerequisites']:
                if prereq_id in prereq_map:
                    prereq_map[prereq_id]['dependents'].append(concept_id)
        
        return prereq_map
    
    def _build_generation_prompt(
        self,
        user_goal: str,
        concepts: List[Dict[str, Any]],
        prerequisite_data: Dict[str, Any],
        max_lessons: int,
        target_category: Optional[str] = None
    ) -> str:
        """Build the prompt for Claude to generate curriculum."""
        
        # Summarize concepts with IDs
        concept_summary = []
        for concept in concepts[:30]:
            summary = f"- ID: {concept['id']} | Name: {concept['name']}"
            if concept.get('definition'):
                summary += f" | {concept['definition'][:80]}"
            concept_summary.append(summary)
        
        # Summarize prerequisites
        prereq_summary = []
        for concept_id, data in list(prerequisite_data.items())[:20]:
            if data['prerequisites']:
                prereq_names = [prerequisite_data.get(p, {}).get('name', 'unknown') 
                               for p in data['prerequisites']]
                prereq_summary.append(f"- {data['name']} requires: {', '.join(prereq_names)}")
        
        prompt = f"""You are a curriculum designer for an MBTI/Jungian psychology learning system.

USER GOAL: "{user_goal}"

KNOWLEDGE GRAPH DATA:
Total concepts available: {len(concepts)}

Key concepts related to goal:
{chr(10).join(concept_summary[:20])}

Prerequisite relationships:
{chr(10).join(prereq_summary[:15]) if prereq_summary else "No explicit prerequisites found"}

TASK: Create a learning path (course/track) that progresses from foundational to advanced concepts.

ANALYSIS STEPS:
1. Identify the 8-15 most important concepts for achieving this goal
2. Trace prerequisite relationships backward to foundational concepts
3. Group concepts into logical lessons (2-5 concepts per lesson)
4. Order lessons by dependency (prerequisites first)
5. Determine appropriate category: foundations/your_type/relationships/advanced

COURSE DESIGN PRINCIPLES:
- Start with foundational concepts (no prerequisites required)
- Each lesson builds on previous lessons
- Lessons should be 20-45 minutes each
- Group related concepts together
- Maximum {max_lessons} lessons per course
- ALL lessons must match the course category difficulty level:
  * foundations course → ALL lessons "foundational"
  * your_type course → ALL lessons "intermediate"
  * relationships course → ALL lessons "intermediate"
  * advanced course → ALL lessons "advanced"

OUTPUT FORMAT (respond ONLY with valid JSON):
{{
  "title": "Engaging course name (specific, clear)",
  "category": "{target_category if target_category else "foundations/your_type/relationships/advanced"}",
  "description": "One-sentence course overview (what will be mastered)",
  "estimated_hours": 4.5,
  "tags": ["tag1", "tag2", "tag3"],
  "lessons": [
    {{
      "title": "Descriptive lesson title",
      "order_index": 1,
      "concept_ids": ["concept_id_1", "concept_id_2"],
      "description": "What this lesson covers (2-3 sentences)",
      "estimated_minutes": 30,
      "difficulty": "foundational",
      "learning_objectives": "What student will be able to do after this lesson",
      "key_takeaways": "Main points to remember",
      "prerequisite_lesson_ids": [],
      "rationale": "Why this lesson comes at this point in the sequence"
    }}
  ]
}}

IMPORTANT RULES:
- Use ONLY concept IDs from the provided list
- Ensure lesson order respects prerequisites
- Each lesson should have clear learning objectives
- Provide rationale for lesson sequencing
- Total estimated_hours = sum of lesson minutes / 60
- Respond with ONLY the JSON, no other text

Generate the curriculum now:"""

        return prompt
    
    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response."""
        try:
            # Extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in Claude response")
            
            json_text = response_text[start_idx:end_idx]
            curriculum = json.loads(json_text)
            
            return curriculum
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValueError(f"Claude returned invalid JSON: {str(e)}")
    
    def _validate_curriculum(
        self,
        curriculum: Dict[str, Any],
        concepts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate curriculum structure and fix issues."""
        # Validate required fields
        required_fields = ['title', 'category', 'description', 'lessons']
        for field in required_fields:
            if field not in curriculum:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate category
        valid_categories = ['foundations', 'your_type', 'relationships', 'advanced']
        if curriculum['category'] not in valid_categories:
            logger.warning(f"Invalid category {curriculum['category']}, defaulting to 'foundations'")
            curriculum['category'] = 'foundations'
        
        # Create concept ID set for validation
        valid_concept_ids = {c['id'] for c in concepts}
        
        # Validate lessons
        lessons = curriculum['lessons']
        
        for i, lesson in enumerate(lessons):
            # Ensure order_index is sequential
            lesson['order_index'] = i + 1
            
            # Validate concept_ids exist
            invalid_concepts = [cid for cid in lesson['concept_ids'] 
                               if cid not in valid_concept_ids]
            if invalid_concepts:
                logger.warning(f"Lesson '{lesson['title']}' references unknown concepts: {invalid_concepts}")
                # Remove invalid concept IDs
                lesson['concept_ids'] = [cid for cid in lesson['concept_ids'] 
                                        if cid in valid_concept_ids]
        
        # Calculate estimated_hours if not provided
        if 'estimated_hours' not in curriculum:
            total_minutes = sum(lesson.get('estimated_minutes', 30) for lesson in lessons)
            curriculum['estimated_hours'] = round(total_minutes / 60, 1)
        
        # Add default tags if missing
        if 'tags' not in curriculum:
            curriculum['tags'] = []
        
        return curriculum
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost of Claude API call."""
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost
    
    def get_total_cost(self) -> float:
        """Get total cost of all generations in this session."""
        return self.generation_cost
    
    def reset_cost_tracking(self):
        """Reset cost tracking to zero."""
        self.generation_cost = 0.0
