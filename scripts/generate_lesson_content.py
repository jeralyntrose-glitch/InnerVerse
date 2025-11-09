#!/usr/bin/env python3
"""
Generate lesson content from Pinecone transcripts using Claude.

This script:
1. Loads all lessons from PostgreSQL
2. For each lesson, queries Pinecone for relevant transcript chunks
3. Uses Claude to synthesize structured lesson content
4. Saves the generated content back to the database
"""

import os
import sys
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from anthropic import Anthropic
from pinecone import Pinecone
from openai import OpenAI
import time

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PINECONE_INDEX_NAME = 'mbti-knowledge-v2'

# Initialize clients
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
index = pinecone_client.Index(PINECONE_INDEX_NAME)

# Cost tracking
total_cost = 0.0
total_input_tokens = 0
total_output_tokens = 0

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_all_lessons():
    """Fetch all lessons from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT l.id, l.title, l.description, l.course_id, c.title as course_title
        FROM lessons l
        JOIN courses c ON l.course_id = c.id
        ORDER BY c.id, l.order_index
    """)
    
    lessons = cursor.fetchall()
    conn.close()
    
    return lessons

def get_lesson_concepts(lesson_id):
    """Get assigned concepts for a lesson"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT concept_id, confidence_level, similarity_score
        FROM lesson_concepts
        WHERE lesson_id = %s
        ORDER BY similarity_score DESC
    """, (lesson_id,))
    
    concepts = cursor.fetchall()
    conn.close()
    
    return concepts

def generate_embedding(text):
    """Generate embedding using OpenAI"""
    response = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text,
        dimensions=3072
    )
    return response.data[0].embedding

def search_relevant_transcripts(lesson_title, lesson_description, concepts, top_k=10):
    """Search Pinecone for relevant transcript chunks"""
    # Create search query from lesson info
    search_text = f"{lesson_title}. {lesson_description}"
    
    # Add concept names if available
    if concepts:
        concept_names = [c['concept_id'] for c in concepts[:5]]  # Top 5 concepts
        search_text += f" Related concepts: {', '.join(concept_names)}"
    
    # Generate embedding
    query_vector = generate_embedding(search_text)
    
    # Search Pinecone (exclude concept embeddings, only get document chunks)
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter={"type": {"$ne": "concept"}}  # Exclude concept embeddings
    )
    
    return results.matches

def generate_lesson_content(lesson_title, lesson_description, transcript_chunks):
    """Use Claude to generate structured lesson content from transcripts"""
    global total_cost, total_input_tokens, total_output_tokens
    
    # Build context from transcript chunks
    context_parts = []
    for i, chunk in enumerate(transcript_chunks[:8], 1):  # Use top 8 chunks
        metadata = chunk.metadata
        text = metadata.get('text', '')
        source = metadata.get('filename', 'Unknown source')
        
        context_parts.append(f"[Source {i}: {source}]\n{text}\n")
    
    context = "\n---\n".join(context_parts)
    
    # Claude prompt
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
        # Call Claude
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Extract response
        content = response.content[0].text
        
        # Calculate cost (Claude Sonnet 4 pricing: $3/M input, $15/M output)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
        
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        total_cost += cost
        
        return content, cost, input_tokens, output_tokens
        
    except Exception as e:
        print(f"❌ Error generating content: {e}")
        return None, 0, 0, 0

def save_lesson_content(lesson_id, content):
    """Save generated content to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE lessons
            SET lesson_content = %s
            WHERE id = %s
        """, (content, lesson_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main execution"""
    print("=" * 70)
    print("LESSON CONTENT GENERATOR")
    print("=" * 70)
    print()
    
    # Get all lessons
    print("📚 Loading lessons from database...")
    lessons = get_all_lessons()
    print(f"✅ Found {len(lessons)} lessons\n")
    
    # Ask for confirmation
    print(f"This will generate content for {len(lessons)} lessons.")
    print(f"Estimated cost: ${len(lessons) * 0.015:.2f} (assuming ~$0.015 per lesson)")
    confirm = input("\nContinue? (y/n): ")
    
    if confirm.lower() != 'y':
        print("❌ Cancelled")
        return
    
    print()
    print("=" * 70)
    print("GENERATING CONTENT")
    print("=" * 70)
    print()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, lesson in enumerate(lessons, 1):
        lesson_id = lesson['id']
        lesson_title = lesson['title']
        lesson_description = lesson['description'] or ''
        course_title = lesson['course_title']
        
        print(f"[{i}/{len(lessons)}] {course_title} → {lesson_title[:50]}...")
        
        # Get concepts
        concepts = get_lesson_concepts(lesson_id)
        print(f"  📚 {len(concepts)} concepts assigned")
        
        # Search for relevant transcripts
        print(f"  🔍 Searching Pinecone for relevant content...")
        transcript_chunks = search_relevant_transcripts(
            lesson_title, 
            lesson_description, 
            concepts,
            top_k=10
        )
        
        if not transcript_chunks:
            print(f"  ⚠️  No relevant transcripts found - skipping")
            skip_count += 1
            continue
        
        print(f"  ✅ Found {len(transcript_chunks)} relevant chunks")
        
        # Generate content
        print(f"  🤖 Generating content with Claude...")
        content, cost, input_tokens, output_tokens = generate_lesson_content(
            lesson_title,
            lesson_description,
            transcript_chunks
        )
        
        if not content:
            print(f"  ❌ Failed to generate content")
            error_count += 1
            continue
        
        print(f"  💰 Cost: ${cost:.4f} ({input_tokens} in / {output_tokens} out tokens)")
        
        # Save to database
        if save_lesson_content(lesson_id, content):
            print(f"  ✅ Saved to database")
            success_count += 1
        else:
            print(f"  ❌ Failed to save")
            error_count += 1
        
        print()
        
        # Small delay to avoid rate limits
        time.sleep(0.5)
    
    # Final report
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"✅ Success: {success_count} lessons")
    print(f"⏭️  Skipped: {skip_count} lessons (no transcripts found)")
    print(f"❌ Errors: {error_count} lessons")
    print()
    print(f"📊 Total tokens: {total_input_tokens:,} input / {total_output_tokens:,} output")
    print(f"💰 Total cost: ${total_cost:.4f}")
    print("=" * 70)

if __name__ == '__main__':
    main()
