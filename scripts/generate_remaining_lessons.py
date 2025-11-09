#!/usr/bin/env python3
"""
Generate lesson content for remaining lessons (those without content)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from anthropic import Anthropic
from pinecone import Pinecone
from openai import OpenAI
import time

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

total_cost = 0.0

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_lessons_without_content():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.id, l.title, l.description, c.title as course_title
        FROM lessons l
        JOIN courses c ON l.course_id = c.id
        WHERE l.lesson_content IS NULL
        ORDER BY c.id, l.order_index
    """)
    lessons = cursor.fetchall()
    conn.close()
    return lessons

def get_lesson_concepts(lesson_id):
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
    response = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text,
        dimensions=3072
    )
    return response.data[0].embedding

def search_transcripts(lesson_title, lesson_description, concepts):
    search_text = f"{lesson_title}. {lesson_description}"
    if concepts:
        concept_names = [c['concept_id'] for c in concepts[:5]]
        search_text += f" Related concepts: {', '.join(concept_names)}"
    
    query_vector = generate_embedding(search_text)
    results = index.query(vector=query_vector, top_k=10, include_metadata=True)
    matches = [m for m in results['matches'] if m.get('metadata', {}).get('type') != 'concept']
    return matches

def generate_content(lesson_title, lesson_description, chunks):
    global total_cost
    
    context_parts = []
    for i, chunk in enumerate(chunks[:8], 1):
        metadata = chunk.get('metadata', {})
        text = metadata.get('text', '')
        source = metadata.get('filename', 'Unknown')
        if text:
            context_parts.append(f"[Source {i}: {source}]\n{text}\n")
    
    if not context_parts:
        return None, 0
    
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
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        cost = (response.usage.input_tokens * 3 / 1_000_000) + (response.usage.output_tokens * 15 / 1_000_000)
        total_cost += cost
        
        return content, cost
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None, 0

def save_content(lesson_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE lessons SET lesson_content = %s WHERE id = %s", (content, lesson_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"  ❌ DB Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("=" * 70)
    print("LESSON CONTENT GENERATOR - REMAINING LESSONS ONLY")
    print("=" * 70)
    print()
    
    lessons = get_lessons_without_content()
    print(f"✅ Found {len(lessons)} lessons without content\n")
    
    if len(lessons) == 0:
        print("🎉 All lessons already have content!")
        return
    
    print(f"🚀 Generating content for {len(lessons)} lessons")
    print(f"Estimated cost: ${len(lessons) * 0.024:.2f}\n")
    
    for i, lesson in enumerate(lessons, 1):
        print(f"[{i}/{len(lessons)}] {lesson['title'][:60]}...")
        
        concepts = get_lesson_concepts(lesson['id'])
        print(f"  📚 {len(concepts)} concepts")
        
        chunks = search_transcripts(lesson['title'], lesson['description'] or '', concepts)
        
        if not chunks:
            print(f"  ⚠️  No chunks - skipping")
            continue
        
        print(f"  ✅ {len(chunks)} chunks")
        
        content, cost = generate_content(lesson['title'], lesson['description'] or '', chunks)
        
        if not content:
            print(f"  ❌ Failed")
            continue
        
        print(f"  💰 ${cost:.4f}")
        
        if save_content(lesson['id'], content):
            print(f"  ✅ Saved")
        else:
            print(f"  ❌ Save failed")
        
        time.sleep(0.3)
    
    print()
    print(f"💰 Total cost: ${total_cost:.4f}")

if __name__ == '__main__':
    main()
