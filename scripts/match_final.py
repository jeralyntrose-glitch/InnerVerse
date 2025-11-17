import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from pinecone import Pinecone
from openai import OpenAI
from fuzzywuzzy import fuzz
from typing import Dict, List, Optional, Tuple
import json

DATABASE_URL = os.environ.get("DATABASE_URL")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PINECONE_INDEX = "mbti-knowledge-v2"

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def clean_title(title: str) -> str:
    """Clean title for better matching"""
    if not title:
        return ""
    
    title = title.lower()
    # Remove common suffixes like "| CS Joseph", "| Season X", etc.
    title = re.sub(r'\s*\|\s*.*$', '', title)
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title

def get_all_lessons() -> List[Dict]:
    """Get all lessons from database"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT lesson_id, lesson_title, youtube_url, document_id, 
               module_number, season_number, season_name, lesson_number
        FROM curriculum
        ORDER BY lesson_id
    """)
    
    lessons = cursor.fetchall()
    conn.close()
    
    return [dict(lesson) for lesson in lessons]

def get_all_pinecone_documents() -> List[Dict]:
    """Get all lesson documents from Pinecone (excluding concepts)"""
    print("🔍 Querying Pinecone for all lesson documents...")
    
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX)
    
    # Create a query vector
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(
        input="cognitive functions MBTI personality type theory",
        model="text-embedding-3-large",
        dimensions=3072
    )
    query_vector = response.data[0].embedding
    
    # Query with large top_k to get as many documents as possible
    results = index.query(
        vector=query_vector,
        top_k=10000,  # Maximum allowed
        include_metadata=True,
        filter={"type": {"$ne": "concept"}}  # Exclude concepts
    )
    
    print(f"   Retrieved {len(results.matches)} vector chunks")
    
    # Group by doc_id to get unique documents
    all_docs = {}
    
    for match in results.matches:
        metadata = match.metadata or {}
        doc_id = metadata.get('doc_id')
        
        if doc_id and doc_id not in all_docs:
            # Extract season from filename if available
            filename = metadata.get('filename', '')
            season_match = re.search(r'\[(\d+(?:\.\d+)?)\]', filename)
            season_from_filename = season_match.group(1) if season_match else None
            
            # Extract title from filename (text after [XX])
            title_match = re.search(r'\[\d+(?:\.\d+)?\]\s*(.+)', filename)
            title_from_filename = title_match.group(1).strip() if title_match else filename
            
            all_docs[doc_id] = {
                'document_id': doc_id,
                'filename': filename,
                'title': title_from_filename,
                'season': metadata.get('season') or season_from_filename,
                'content_type': metadata.get('content_type', ''),
                'source': metadata.get('source', '')
            }
    
    print(f"✅ Found {len(all_docs)} unique Pinecone documents")
    return list(all_docs.values())

def match_by_season_and_title(lesson: Dict, pinecone_docs: List[Dict], threshold: int = 65) -> Optional[Tuple[str, int, str]]:
    """Match by season number + fuzzy title"""
    lesson_season = str(lesson.get('season_number', '')).strip()
    lesson_title = clean_title(lesson.get('lesson_title', ''))
    
    if not lesson_season or not lesson_title:
        return None
    
    best_match = None
    best_score = 0
    best_method = ""
    
    for doc in pinecone_docs:
        doc_season = str(doc.get('season', '')).strip()
        
        # Must match season first
        if doc_season != lesson_season:
            continue
        
        # Then check title similarity
        doc_title = clean_title(doc.get('title', ''))
        
        if doc_title:
            score = fuzz.token_sort_ratio(lesson_title, doc_title)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = doc['document_id']
                best_method = f"Season {lesson_season} + Title ({score}%)"
    
    if best_match:
        return (best_match, best_score, best_method)
    
    return None

def update_document_id(lesson_id: int, document_id: str):
    """Update database with matched document_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE curriculum
        SET document_id = %s
        WHERE lesson_id = %s
    """, (document_id, lesson_id))
    
    conn.commit()
    conn.close()

def main():
    """Main matching logic"""
    print("=" * 80)
    print("🔗 FINAL DOCUMENT_ID MATCHING SCRIPT")
    print("=" * 80)
    
    # Step 1: Load data
    print("\n📚 Step 1: Loading data...")
    lessons = get_all_lessons()
    pinecone_docs = get_all_pinecone_documents()
    
    print(f"\n   Total lessons: {len(lessons)}")
    print(f"   Total Pinecone documents: {len(pinecone_docs)}")
    
    # Step 2: Match lessons
    print("\n🔍 Step 2: Matching lessons to documents...")
    
    stats = {
        'total': len(lessons),
        'already_matched': 0,
        'newly_matched': 0,
        'still_missing': 0
    }
    
    unmatched_lessons = []
    matched_lessons = []
    
    for lesson in lessons:
        lesson_id = lesson['lesson_id']
        lesson_title = lesson['lesson_title']
        current_doc_id = lesson['document_id']
        
        # Skip if already has document_id
        if current_doc_id:
            stats['already_matched'] += 1
            continue
        
        # Try season + title matching
        match_result = match_by_season_and_title(lesson, pinecone_docs, threshold=65)
        
        if match_result:
            matched_doc_id, confidence, method = match_result
            
            # Update database
            update_document_id(lesson_id, matched_doc_id)
            
            stats['newly_matched'] += 1
            
            matched_lessons.append({
                'lesson_id': lesson_id,
                'title': lesson_title,
                'season': lesson.get('season_number'),
                'document_id': matched_doc_id,
                'method': method,
                'confidence': confidence
            })
            
            print(f"   ✅ {stats['newly_matched']}. Lesson {lesson_id}: {lesson_title[:50]}... → {method}")
        else:
            stats['still_missing'] += 1
            unmatched_lessons.append({
                'lesson_id': lesson_id,
                'title': lesson_title,
                'season': lesson.get('season_number'),
                'module': lesson.get('module_number')
            })
    
    # Step 3: Generate report
    print("\n" + "=" * 80)
    print("📊 MATCHING REPORT")
    print("=" * 80)
    print(f"\n✅ Total lessons: {stats['total']}")
    print(f"   Already matched: {stats['already_matched']}")
    print(f"   Newly matched: {stats['newly_matched']}")
    print(f"   Still missing: {stats['still_missing']}")
    
    total_with_doc_id = stats['already_matched'] + stats['newly_matched']
    success_rate = (total_with_doc_id / stats['total']) * 100
    print(f"\n🎯 Overall success rate: {success_rate:.1f}%")
    
    # Save unmatched lessons
    if unmatched_lessons:
        print(f"\n⚠️  {len(unmatched_lessons)} lessons still missing document_id")
        
        # Group by season to show patterns
        by_season = {}
        for lesson in unmatched_lessons:
            season = lesson['season']
            if season not in by_season:
                by_season[season] = []
            by_season[season].append(lesson)
        
        print(f"\n📊 Unmatched lessons by season:")
        for season in sorted(by_season.keys(), key=lambda x: (float(x) if x and str(x).replace('.', '', 1).isdigit() else 999, x)):
            count = len(by_season[season])
            print(f"   Season {season}: {count} lessons")
        
        with open('unmatched_lessons_final.json', 'w') as f:
            json.dump(unmatched_lessons, f, indent=2)
        print(f"\n💾 Full unmatched list saved to: scripts/unmatched_lessons_final.json")
    
    # Save matched lessons
    if matched_lessons:
        with open('matched_lessons_final.json', 'w') as f:
            json.dump(matched_lessons, f, indent=2)
        print(f"💾 Matched lessons saved to: scripts/matched_lessons_final.json")
    
    # Save Pinecone docs for reference
    with open('pinecone_documents.json', 'w') as f:
        json.dump(pinecone_docs, f, indent=2)
    print(f"💾 Pinecone documents saved to: scripts/pinecone_documents.json")
    
    print("\n" + "=" * 80)
    print("✅ MATCHING COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()
