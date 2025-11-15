#!/usr/bin/env python3
"""
Map curriculum lessons to Pinecone document UUIDs
"""

import csv
import psycopg2
import os
from difflib import SequenceMatcher

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def load_pinecone_docs(csv_path):
    """Load Pinecone documents from CSV"""
    docs = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            docs.append({
                'document_id': row['document_id'],
                'title': row['title'],
                'season': extract_season(row['title'])
            })
    return docs

def extract_season(title):
    """Extract season number from title like '[1]' -> '1'"""
    if title.startswith('['):
        return title.split(']')[0][1:]
    return None

def find_best_match(lesson_title, season_number, pinecone_docs):
    """Find best matching Pinecone document for a lesson"""
    candidates = [doc for doc in pinecone_docs if doc['season'] == str(season_number)]
    
    if not candidates:
        return None
    
    best_match = None
    best_score = 0
    
    for doc in candidates:
        score = similarity(lesson_title, doc['title'])
        if score > best_score:
            best_score = score
            best_match = doc
    
    return best_match if best_score > 0.3 else None

def main():
    # Load Pinecone documents
    pinecone_docs = load_pinecone_docs('attached_assets/document_report_1763201335230.csv')
    print(f"✅ Loaded {len(pinecone_docs)} Pinecone documents")
    
    # Connect to database
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    # Get all lessons
    cursor.execute("""
        SELECT lesson_id, lesson_title, season_number, lesson_number
        FROM curriculum
        ORDER BY season_number, lesson_number
    """)
    
    lessons = cursor.fetchall()
    print(f"✅ Found {len(lessons)} lessons in curriculum\n")
    
    matched_count = 0
    unmatched = []
    
    # Match each lesson
    for lesson_id, lesson_title, season_number, lesson_number in lessons:
        match = find_best_match(lesson_title, season_number, pinecone_docs)
        
        if match:
            # Update database
            cursor.execute("""
                UPDATE curriculum
                SET document_id = %s
                WHERE lesson_id = %s
            """, (match['document_id'], lesson_id))
            
            print(f"✅ Lesson {lesson_id}: '{lesson_title}'")
            print(f"   → Pinecone: {match['title']}")
            print(f"   → UUID: {match['document_id']}\n")
            matched_count += 1
        else:
            unmatched.append((lesson_id, lesson_title, season_number))
            print(f"❌ No match for Lesson {lesson_id}: '{lesson_title}' (Season {season_number})\n")
    
    # Commit changes
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ Matched: {matched_count}/{len(lessons)} lessons")
    print(f"❌ Unmatched: {len(unmatched)} lessons")
    
    if unmatched:
        print("\nUnmatched lessons (will need manual mapping):")
        for lesson_id, title, season in unmatched:
            print(f"  - Lesson {lesson_id}: {title} (Season {season})")

if __name__ == '__main__':
    main()
