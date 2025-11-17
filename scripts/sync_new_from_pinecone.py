#!/usr/bin/env python3
"""
Sync NEW lessons from Pinecone to InnerVerse database

SCOPE: Only finds NEW content not yet in database
SAFE: Does not modify existing lessons
USAGE: python scripts/sync_new_from_pinecone.py
"""

import os
import sys
import csv
import re
from pinecone import Pinecone
from dotenv import load_dotenv
import psycopg2

# Load environment
load_dotenv()

def get_pinecone_client():
    """Initialize Pinecone client"""
    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found")
    return Pinecone(api_key=api_key)

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_existing_youtube_ids():
    """Get all YouTube IDs already in database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT transcript_id FROM curriculum WHERE transcript_id IS NOT NULL")
    existing = {row[0] for row in cursor.fetchall()}
    
    cursor.close()
    conn.close()
    
    return existing

def query_pinecone_documents():
    """Query all documents from Pinecone with metadata"""
    pc = get_pinecone_client()
    index = pc.Index('mbti-knowledge-v2')
    
    # Query with dummy vector to get documents
    # (Your existing pattern from match scripts)
    dummy_vector = [0.0] * 3072
    
    results = index.query(
        vector=dummy_vector,
        top_k=10000,
        include_metadata=True
    )
    
    return results.matches

def find_new_lessons(pinecone_docs, existing_youtube_ids):
    """Find documents with YouTube URLs not yet in database"""
    new_lessons = []
    
    for doc in pinecone_docs:
        metadata = doc.metadata or {}
        
        # Check if has YouTube URL in metadata
        youtube_url = metadata.get('youtube_url') or metadata.get('url')
        
        if not youtube_url:
            continue
        
        youtube_id = extract_youtube_id(youtube_url)
        
        if not youtube_id:
            continue
        
        # Skip if already in database
        if youtube_id in existing_youtube_ids:
            continue
        
        # This is a NEW lesson!
        new_lessons.append({
            'document_id': doc.id,
            'title': metadata.get('title', 'Unknown'),
            'youtube_url': youtube_url,
            'youtube_id': youtube_id,
            'season': metadata.get('season') or metadata.get('season_number'),
            'episode': metadata.get('episode') or metadata.get('episode_number')
        })
    
    return new_lessons

def generate_import_csv(new_lessons, output_file='new_lessons_import.csv'):
    """Generate CSV for importing new lessons"""
    if not new_lessons:
        print("No new lessons found!")
        return None
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'lesson_title', 'youtube_url', 'youtube_id', 
            'document_id', 'season_number', 'episode_number'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for lesson in new_lessons:
            writer.writerow({
                'lesson_title': lesson['title'],
                'youtube_url': lesson['youtube_url'],
                'youtube_id': lesson['youtube_id'],
                'document_id': lesson['document_id'],
                'season_number': lesson.get('season', ''),
                'episode_number': lesson.get('episode', '')
            })
    
    return output_file

def main():
    """Main sync process"""
    print("🔄 SYNCING NEW CONTENT FROM PINECONE")
    print("=" * 60)
    
    # Step 1: Get existing lessons
    print("\n📊 Checking existing lessons in database...")
    existing_youtube_ids = get_existing_youtube_ids()
    print(f"   Found {len(existing_youtube_ids)} existing lessons")
    
    # Step 2: Query Pinecone
    print("\n🔍 Querying Pinecone for documents...")
    pinecone_docs = query_pinecone_documents()
    print(f"   Found {len(pinecone_docs)} documents in Pinecone")
    
    # Step 3: Find new lessons
    print("\n🆕 Finding NEW lessons not yet in database...")
    new_lessons = find_new_lessons(pinecone_docs, existing_youtube_ids)
    print(f"   Found {len(new_lessons)} NEW lessons!")
    
    # Step 4: Generate CSV
    if new_lessons:
        print("\n📝 Generating import CSV...")
        csv_file = generate_import_csv(new_lessons)
        print(f"   ✅ Created: {csv_file}")
        
        # Show preview
        print("\n📋 NEW LESSONS PREVIEW:")
        for i, lesson in enumerate(new_lessons[:5], 1):
            print(f"   {i}. {lesson['title']}")
            print(f"      YouTube: {lesson['youtube_id']}")
            print(f"      Season: {lesson.get('season', 'N/A')}")
        
        if len(new_lessons) > 5:
            print(f"   ... and {len(new_lessons) - 5} more")
        
        print("\n" + "=" * 60)
        print("✅ SYNC COMPLETE!")
        print(f"📄 Review CSV: {csv_file}")
        print("📋 Next step: Manually review CSV, then import to database")
    else:
        print("\n✅ No new lessons found - database is up to date!")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
