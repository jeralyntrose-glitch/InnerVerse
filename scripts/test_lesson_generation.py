#!/usr/bin/env python3
"""
Test lesson content generation on a small sample (3 lessons)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from anthropic import Anthropic
from pinecone import Pinecone
from openai import OpenAI
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_sample_lessons(limit=3):
    """Fetch sample lessons"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT l.id, l.title, l.description, l.course_id, c.title as course_title
        FROM lessons l
        JOIN courses c ON l.course_id = c.id
        ORDER BY c.id, l.order_index
        LIMIT {limit}
    """)
    
    lessons = cursor.fetchall()
    conn.close()
    
    return lessons

def get_lesson_concepts(lesson_id):
    """Get assigned concepts for a lesson"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT concept_id, confidence, similarity_score
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
    search_text = f"{lesson_title}. {lesson_description}"
    
    if concepts:
        concept_names = [c['concept_id'] for c in concepts[:5]]
        search_text += f" Related concepts: {', '.join(concept_names)}"
    
    query_vector = generate_embedding(search_text)
    
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )
    
    # Filter out concept embeddings manually
    matches = [m for m in results['matches'] if m.get('metadata', {}).get('type') != 'concept']
    
    return matches

def generate_lesson_content(lesson_title, lesson_description, transcript_chunks):
    """Use Claude to generate structured lesson content"""
    context_parts = []
    for i, chunk in enumerate(transcript_chunks[:8], 1):
        metadata = chunk.get('metadata', {})
        text = metadata.get('text', '')
        source = metadata.get('filename', 'Unknown source')
        
        if text:
            context_parts.append(f"[Source {i}: {source}]\n{text}\n")
    
    if not context_parts:
        return None, 0, 0, 0
    
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
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        content = response.content[0].text
        
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
        
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
    print("=" * 70)
    print("LESSON CONTENT GENERATION - TEST MODE (3 lessons)")
    print("=" * 70)
    print()
    
    lessons = get_sample_lessons(3)
    print(f"✅ Testing with {len(lessons)} lessons\n")
    
    total_cost = 0.0
    
    for i, lesson in enumerate(lessons, 1):
        lesson_id = lesson['id']
        lesson_title = lesson['title']
        lesson_description = lesson['description'] or ''
        
        print(f"[{i}/3] {lesson_title}")
        
        concepts = get_lesson_concepts(lesson_id)
        print(f"  📚 {len(concepts)} concepts")
        
        print(f"  🔍 Searching transcripts...")
        chunks = search_relevant_transcripts(lesson_title, lesson_description, concepts)
        
        if not chunks:
            print(f"  ⚠️  No chunks found")
            continue
        
        print(f"  ✅ Found {len(chunks)} chunks")
        
        print(f"  🤖 Generating content...")
        content, cost, input_tok, output_tok = generate_lesson_content(
            lesson_title, lesson_description, chunks
        )
        
        if not content:
            print(f"  ❌ Generation failed")
            continue
        
        print(f"  💰 ${cost:.4f} ({input_tok} in / {output_tok} out)")
        print(f"  📝 Generated {len(content)} characters")
        
        if save_lesson_content(lesson_id, content):
            print(f"  ✅ Saved!")
        else:
            print(f"  ❌ Save failed")
        
        total_cost += cost
        print()
    
    print(f"💰 Total test cost: ${total_cost:.4f}")

if __name__ == '__main__':
    main()
