#!/usr/bin/env python3
"""
DEPRECATED - This script is kept for reference only.

Lesson content is now automatically generated when courses are created via:
- POST /api/courses/generate (creates courses + launches background worker)
- Background worker: generate_lesson_content_worker() in main.py
- Service: LessonContentGenerator in src/services/lesson_content_generator.py

This standalone script can still be used for manual/emergency content generation,
but the integrated background system is preferred for normal operations.

Original purpose: Generate lesson content in batches of 10 lessons
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
BATCH_SIZE = 10

# Initialize clients
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
index = pinecone_client.Index(PINECONE_INDEX_NAME)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_batch_without_content(batch_size=BATCH_SIZE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT l.id, l.title, l.description, c.title as course_title
        FROM lessons l
        JOIN courses c ON l.course_id = c.id
        WHERE l.lesson_content IS NULL
        ORDER BY c.id, l.order_index
        LIMIT {batch_size}
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
        search_text += f" {', '.join(concept_names)}"
    
    query_vector = generate_embedding(search_text)
    results = index.query(vector=query_vector, top_k=10, include_metadata=True)
    matches = [m for m in results['matches'] if m.get('metadata', {}).get('type') != 'concept']
    return matches

def generate_content(lesson_title, lesson_description, chunks):
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
        
        return content, cost
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None, 0

def save_content(lesson_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE lessons SET lesson_content = %s WHERE id = %s", (content, lesson_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"    ❌ DB Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_progress():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total, COUNT(lesson_content) as with_content FROM lessons")
    result = cursor.fetchone()
    conn.close()
    return result['total'], result['with_content']

def main():
    total, completed = get_progress()
    remaining = total - completed
    
    print("=" * 70)
    print("BATCH LESSON GENERATOR")
    print("=" * 70)
    print(f"📊 Progress: {completed}/{total} lessons ({int(completed/total*100)}%)")
    print(f"📋 Remaining: {remaining} lessons")
    print(f"🎯 This batch: Up to {BATCH_SIZE} lessons")
    print("=" * 70)
    print()
    
    lessons = get_batch_without_content(BATCH_SIZE)
    
    if len(lessons) == 0:
        print("🎉 All lessons complete!")
        return
    
    print(f"✅ Processing {len(lessons)} lessons in this batch\n")
    
    batch_cost = 0.0
    success = 0
    skipped = 0
    
    for i, lesson in enumerate(lessons, 1):
        title_short = lesson['title'][:55] + "..." if len(lesson['title']) > 55 else lesson['title']
        print(f"[{i}/{len(lessons)}] {title_short}")
        
        concepts = get_lesson_concepts(lesson['id'])
        print(f"    📚 {len(concepts)} concepts")
        
        chunks = search_transcripts(lesson['title'], lesson['description'] or '', concepts)
        
        if not chunks:
            print(f"    ⚠️  No relevant chunks - skipping\n")
            skipped += 1
            continue
        
        print(f"    ✅ Found {len(chunks)} chunks")
        
        content, cost = generate_content(lesson['title'], lesson['description'] or '', chunks)
        
        if not content:
            print(f"    ❌ Generation failed\n")
            skipped += 1
            continue
        
        print(f"    💰 ${cost:.4f}")
        
        if save_content(lesson['id'], content):
            print(f"    ✅ Saved\n")
            success += 1
            batch_cost += cost
        else:
            print(f"    ❌ Save failed\n")
            skipped += 1
        
        time.sleep(0.3)
    
    # Final batch report
    print("=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)
    print(f"✅ Success: {success} lessons")
    print(f"⏭️  Skipped: {skipped} lessons")
    print(f"💰 Batch cost: ${batch_cost:.4f}")
    print()
    
    # Overall progress
    total, completed = get_progress()
    remaining = total - completed
    print(f"📊 Overall Progress: {completed}/{total} lessons ({int(completed/total*100)}%)")
    print(f"📋 Remaining: {remaining} lessons")
    
    if remaining > 0:
        print(f"\n💡 Run again to process next batch of {min(remaining, BATCH_SIZE)} lessons")
    else:
        print(f"\n🎉 ALL LESSONS COMPLETE!")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
