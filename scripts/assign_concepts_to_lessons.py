#!/usr/bin/env python3
"""
Assign Concepts to Lessons - Phase 6
====================================
Automatically assigns 3-10 relevant concepts to each lesson using:
- Vector similarity from Pinecone (50% weight)
- Metadata overlap (35% weight)
- Prominence in title/description (15% weight)

Usage:
    python scripts/assign_concepts_to_lessons.py
"""

import os
import sys
import psycopg2
import psycopg2.extras
from pinecone import Pinecone
import openai
import json
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_INDEX = os.getenv('PINECONE_INDEX')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize clients
openai.api_key = OPENAI_API_KEY
pc = Pinecone(api_key=PINECONE_API_KEY)
pinecone_index = pc.Index(PINECONE_INDEX)


def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(DATABASE_URL)


def create_embedding(text: str) -> List[float]:
    """Create OpenAI embedding for text"""
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    return response.data[0].embedding


def calculate_metadata_overlap(lesson_metadata: Dict, concept_metadata: Dict) -> float:
    """
    Calculate metadata overlap score between lesson and concept
    
    Args:
        lesson_metadata: Metadata from lesson (types_discussed, functions_covered, etc.)
        concept_metadata: Metadata from Pinecone concept chunk
    
    Returns:
        Overlap score from 0.0 to 1.0
    """
    overlap_scores = []
    
    # Fields to compare
    fields_to_compare = [
        'types_discussed',
        'functions_covered',
        'primary_category',
        'quadra',
        'temple'
    ]
    
    for field in fields_to_compare:
        lesson_value = lesson_metadata.get(field, [])
        concept_value = concept_metadata.get(field, [])
        
        # Handle both list and single value cases
        if not isinstance(lesson_value, list):
            lesson_value = [lesson_value] if lesson_value else []
        if not isinstance(concept_value, list):
            concept_value = [concept_value] if concept_value else []
        
        # Calculate overlap
        if lesson_value and concept_value:
            lesson_set = set(str(v).lower() for v in lesson_value if v)
            concept_set = set(str(v).lower() for v in concept_value if v)
            
            if lesson_set and concept_set:
                intersection = len(lesson_set & concept_set)
                union = len(lesson_set | concept_set)
                overlap = intersection / union if union > 0 else 0
                overlap_scores.append(overlap)
    
    # Return average overlap across all fields (or 0 if no overlaps)
    return sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0.0


def calculate_prominence_score(concept_name: str, lesson_title: str, lesson_description: str) -> float:
    """
    Calculate prominence score based on concept name appearing in title/description
    
    Args:
        concept_name: Name of the concept
        lesson_title: Lesson title
        lesson_description: Lesson description
    
    Returns:
        Prominence score from 0.0 to 1.0
    """
    concept_lower = concept_name.lower()
    title_lower = lesson_title.lower()
    desc_lower = (lesson_description or '').lower()
    
    score = 0.0
    
    # Exact match in title: 1.0
    if concept_lower in title_lower:
        score = 1.0
    # Exact match in description: 0.7
    elif concept_lower in desc_lower:
        score = 0.7
    # Partial match using fuzzy matching
    else:
        title_similarity = SequenceMatcher(None, concept_lower, title_lower).ratio()
        desc_similarity = SequenceMatcher(None, concept_lower, desc_lower).ratio()
        score = max(title_similarity, desc_similarity) * 0.5
    
    return min(score, 1.0)


def calculate_composite_score(
    similarity_score: float,
    metadata_overlap: float,
    prominence: float
) -> float:
    """
    Calculate composite score from all factors
    
    UPDATED: Since lessons don't have MBTI metadata, weights adjusted:
    - Vector similarity: 70% (increased from 50%)
    - Prominence: 30% (increased from 15%)
    - Metadata overlap: 0% (lessons lack MBTI metadata fields)
    
    Args:
        similarity_score: Pinecone vector similarity (0-1)
        metadata_overlap: Metadata overlap score (0-1) - UNUSED for lessons
        prominence: Prominence score (0-1)
    
    Returns:
        Composite score from 0.0 to 1.0
    """
    return (
        similarity_score * 0.70 +
        prominence * 0.30
    )


def assign_confidence(score: float) -> str:
    """
    Assign confidence level based on composite score
    
    UPDATED: Lowered thresholds to account for lack of lesson metadata:
    - high: >= 0.60 (was 0.75)
    - medium: >= 0.45 (was 0.60)
    - low: >= 0.30 (was 0.45)
    """
    if score >= 0.60:
        return 'high'
    elif score >= 0.45:
        return 'medium'
    elif score >= 0.30:
        return 'low'
    else:
        return None  # Skip


def get_all_lessons():
    """Get all lessons from database"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    id, 
                    title, 
                    description,
                    learning_objectives,
                    key_takeaways,
                    course_id,
                    order_index
                FROM lessons
                ORDER BY course_id, order_index
            """)
            lessons = cur.fetchall()
            return [dict(lesson) for lesson in lessons]
    finally:
        conn.close()


def assign_concepts_to_lesson(lesson: Dict) -> List[Tuple[str, str, float, float, int]]:
    """
    Assign concepts to a single lesson
    
    Args:
        lesson: Lesson dict with id, title, description, learning_objectives, key_takeaways
    
    Returns:
        List of tuples: (concept_id, confidence, similarity_score, metadata_overlap, rank)
    """
    # Create search text: title + description + learning_objectives + key_takeaways
    search_text = f"{lesson['title']} {lesson.get('description', '')}"
    if lesson.get('learning_objectives'):
        search_text += f" {lesson['learning_objectives']}"
    if lesson.get('key_takeaways'):
        search_text += f" {lesson['key_takeaways']}"
    
    # Create embedding
    print(f"  📊 Creating embedding for lesson text...")
    embedding = create_embedding(search_text)
    
    # Query Pinecone
    print(f"  🔍 Querying Pinecone (top_k=50)...")
    results = pinecone_index.query(
        vector=embedding,
        top_k=50,
        include_metadata=True
    )
    
    # Filter to concept-type chunks and calculate scores
    concept_scores = {}  # concept_id -> {score, similarity, metadata, prominence}
    lesson_metadata = lesson.get('metadata') or {}
    
    # DEBUG: Log first few results to see what we're getting
    if len(results.matches) > 0:
        print(f"  📋 DEBUG: Received {len(results.matches)} total matches from Pinecone")
        first_match = results.matches[0]
        print(f"      First match type: {first_match.metadata.get('type') if first_match.metadata else 'NO METADATA'}")
        print(f"      First match keys: {list(first_match.metadata.keys()) if first_match.metadata else 'NO METADATA'}")
    
    for match in results.matches:
        metadata = match.metadata or {}
        
        # Only process concept chunks
        chunk_type = metadata.get('type', '')
        if chunk_type != 'concept':
            continue
        
        concept_id = metadata.get('concept_id') or metadata.get('id')
        if not concept_id:
            continue
        
        concept_name = metadata.get('concept_name') or metadata.get('name', '')
        
        # Calculate scores
        similarity = float(match.score)
        metadata_overlap = calculate_metadata_overlap(lesson_metadata, metadata)
        prominence = calculate_prominence_score(
            concept_name, 
            lesson['title'], 
            lesson.get('description', '')
        )
        
        composite = calculate_composite_score(similarity, metadata_overlap, prominence)
        
        # Keep highest score for each concept (in case multiple chunks per concept)
        if concept_id not in concept_scores or composite > concept_scores[concept_id]['composite']:
            concept_scores[concept_id] = {
                'composite': composite,
                'similarity': similarity,
                'metadata_overlap': metadata_overlap,
                'prominence': prominence
            }
    
    # Sort by composite score
    sorted_concepts = sorted(
        concept_scores.items(), 
        key=lambda x: x[1]['composite'], 
        reverse=True
    )
    
    # Select top 3-10 concepts with acceptable confidence
    assignments = []
    for rank, (concept_id, scores) in enumerate(sorted_concepts, 1):
        confidence = assign_confidence(scores['composite'])
        
        # Skip concepts below threshold
        if confidence is None:
            continue
        
        assignments.append((
            concept_id,
            confidence,
            scores['similarity'],
            scores['metadata_overlap'],
            rank
        ))
        
        # Stop at 10 concepts
        if len(assignments) >= 10:
            break
    
    # Ensure at least 3 concepts (even if low confidence)
    if len(assignments) < 3 and sorted_concepts:
        for rank, (concept_id, scores) in enumerate(sorted_concepts[len(assignments):], len(assignments) + 1):
            # Force at least 'low' confidence for top 3
            confidence = assign_confidence(scores['composite']) or 'low'
            
            assignments.append((
                concept_id,
                confidence,
                scores['similarity'],
                scores['metadata_overlap'],
                rank
            ))
            
            if len(assignments) >= 3:
                break
    
    print(f"  ✅ Found {len(assignments)} concepts for assignment")
    return assignments


def save_assignments(lesson_id: str, assignments: List[Tuple]):
    """Save concept assignments to database"""
    if not assignments:
        return
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Clear existing assignments for this lesson
            cur.execute("""
                DELETE FROM lesson_concepts WHERE lesson_id = %s
            """, (lesson_id,))
            
            # Insert new assignments
            for concept_id, confidence, similarity, metadata_overlap, rank in assignments:
                cur.execute("""
                    INSERT INTO lesson_concepts (
                        lesson_id, 
                        concept_id, 
                        confidence, 
                        similarity_score, 
                        metadata_overlap_score, 
                        assignment_rank
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (lesson_id, concept_id, confidence, similarity, metadata_overlap, rank))
            
        conn.commit()
        print(f"  💾 Saved {len(assignments)} concept assignments")
    finally:
        conn.close()


def main():
    """Main execution"""
    print("=" * 70)
    print("ASSIGN CONCEPTS TO LESSONS - PHASE 6")
    print("=" * 70)
    
    # Get all lessons
    print("\n📚 Loading lessons from database...")
    lessons = get_all_lessons()
    print(f"✅ Found {len(lessons)} lessons")
    
    if not lessons:
        print("❌ No lessons found. Please create some lessons first.")
        return
    
    # Process each lesson
    total_concepts = 0
    for i, lesson in enumerate(lessons, 1):
        print(f"\n[{i}/{len(lessons)}] Processing: {lesson['title']}")
        
        try:
            assignments = assign_concepts_to_lesson(lesson)
            save_assignments(lesson['id'], assignments)
            total_concepts += len(assignments)
        except Exception as e:
            print(f"  ❌ Error processing lesson: {str(e)}")
            continue
    
    # Print final stats
    print("\n" + "=" * 70)
    print("ASSIGNMENT COMPLETE")
    print("=" * 70)
    print(f"Total lessons processed: {len(lessons)}")
    print(f"Total concepts assigned: {total_concepts}")
    print(f"Average concepts per lesson: {total_concepts / len(lessons):.1f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
