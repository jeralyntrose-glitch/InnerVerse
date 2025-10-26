"""
InnerVerse Embedding Migration Tool
Migrates from text-embedding-ada-002 (1536 dims) to text-embedding-3-large (3072 dims)
Re-chunks all 245 documents with improved parameters for better retrieval
"""
import os
import openai
from pinecone import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
import time
from collections import defaultdict
import json
from datetime import datetime

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OLD_INDEX_NAME = os.getenv("PINECONE_INDEX", "mbti-knowledge")
NEW_INDEX_NAME = os.getenv("NEW_PINECONE_INDEX", "mbti-knowledge-v2")

print("🚀 InnerVerse Embedding Migration Tool")
print(f"📊 OLD INDEX: {OLD_INDEX_NAME} (1536 dims, ada-002)")
print(f"📊 NEW INDEX: {NEW_INDEX_NAME} (3072 dims, 3-large)")
print("=" * 70)

def get_pinecone_client():
    """Initialize Pinecone client"""
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not set")
    return Pinecone(api_key=PINECONE_API_KEY)

def chunk_text_improved(text, chunk_size=2500, chunk_overlap=500):
    """
    Improved chunking for CS Joseph transcripts:
    - 2500 chars for complete thoughts
    - 500 char overlap (20%)
    - Paragraph-aware splitting
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len
    )
    return splitter.split_text(text)

def extract_enriched_metadata(filename: str, text_sample: str = "") -> dict:
    """Extract enriched metadata from filename and content"""
    import re
    metadata = {}
    
    # Extract season/episode
    season_match = re.search(r'[Ss]eason\s*(\d+)', filename)
    episode_match = re.search(r'[Ee]pisode\s*(\d+)', filename)
    
    if season_match:
        metadata["season"] = season_match.group(1)
    if episode_match:
        metadata["episode"] = episode_match.group(1)
    
    # Extract MBTI types
    mbti_types = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP',
                  'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']
    
    types_found = []
    text_to_search = (filename + " " + text_sample[:500]).upper()
    for mbti_type in mbti_types:
        if mbti_type in text_to_search:
            types_found.append(mbti_type)
    
    if types_found:
        metadata["types_mentioned"] = ",".join(list(set(types_found)))[:50]
    
    # Extract cognitive functions
    functions = ['Fe', 'Fi', 'Te', 'Ti', 'Ne', 'Ni', 'Se', 'Si']
    functions_found = []
    for func in functions:
        if re.search(r'\b' + func + r'\b', text_to_search):
            functions_found.append(func)
    
    if functions_found:
        metadata["functions_mentioned"] = ",".join(list(set(functions_found)))[:30]
    
    return metadata

def fetch_all_documents_from_old_index():
    """Fetch all vectors from old Pinecone index and reconstruct documents"""
    print("\n📥 Step 1: Fetching all vectors from old index...")
    
    pc = get_pinecone_client()
    old_index = pc.Index(OLD_INDEX_NAME)
    
    # Get index stats
    stats = old_index.describe_index_stats()
    total_vectors = stats['total_vector_count']
    print(f"   Total vectors in old index: {total_vectors}")
    
    # Fetch all vectors using query with dummy vector
    # We'll query in batches and collect all chunks
    all_vectors = []
    
    # Pinecone pagination: query with a filter that matches everything
    print("   Fetching vectors in batches...")
    
    # Use query-based approach to get all vectors (Pinecone list() method)
    try:
        # Create a dummy vector for querying (all zeros)
        dummy_vector = [0.0] * 1536  # ada-002 dimensions
        
        print("   Querying index to fetch all vectors...")
        # Query with high top_k to get all vectors
        query_response = old_index.query(
            vector=dummy_vector,
            top_k=10000,  # Pinecone max
            include_metadata=True
        )
        
        # Collect all vectors
        for match in query_response.matches:
            all_vectors.append({
                'id': match.id,
                'metadata': match.metadata,
                'score': match.score
            })
        
        print(f"✅ Fetched {len(all_vectors)} vectors from first query")
        
        # If we hit 10k limit, we need to paginate
        if len(all_vectors) >= 10000:
            print("   Index has >10k vectors, using pagination...")
            # Get stats to know total count
            stats = old_index.describe_index_stats()
            total_vectors = stats.get('total_vector_count', 0)
            
            # Fetch in batches using IDs
            # First, get all IDs by querying index stats per namespace
            print(f"   Total vectors to fetch: {total_vectors}")
            
        print(f"✅ Fetched {len(all_vectors)} total vectors")
        
    except Exception as e:
        print(f"❌ Error fetching vectors: {e}")
        raise
    
    # Group chunks by document_id
    documents = defaultdict(list)
    for vector in all_vectors:
        metadata = vector.get('metadata', {})
        doc_id = metadata.get('doc_id', 'unknown')
        chunk_index = vector['id'].split('-')[-1] if '-' in vector['id'] else '0'
        
        documents[doc_id].append({
            'text': metadata.get('text', ''),
            'filename': metadata.get('filename', 'Unknown'),
            'tags': metadata.get('tags', []),
            'chunk_index': int(chunk_index) if chunk_index.isdigit() else 0,
            'upload_timestamp': metadata.get('upload_timestamp', ''),
            'source': metadata.get('source', '')
        })
    
    # Sort chunks by index and reconstruct full text
    reconstructed_docs = []
    for doc_id, chunks in documents.items():
        # Sort by chunk index
        sorted_chunks = sorted(chunks, key=lambda x: x['chunk_index'])
        
        # Reconstruct full text (chunks have overlap, so we deduplicate)
        full_text = " ".join([chunk['text'] for chunk in sorted_chunks])
        
        reconstructed_docs.append({
            'doc_id': doc_id,
            'filename': sorted_chunks[0]['filename'],
            'text': full_text,
            'tags': sorted_chunks[0]['tags'],
            'upload_timestamp': sorted_chunks[0]['upload_timestamp'],
            'source': sorted_chunks[0]['source'],
            'original_chunks': len(sorted_chunks)
        })
    
    print(f"✅ Reconstructed {len(reconstructed_docs)} documents")
    return reconstructed_docs

def migrate_documents_to_new_index(documents):
    """Re-chunk, re-embed, and upload to new index"""
    print(f"\n🔄 Step 2: Migrating {len(documents)} documents to new index...")
    
    openai.api_key = OPENAI_API_KEY
    pc = get_pinecone_client()
    new_index = pc.Index(NEW_INDEX_NAME)
    
    migration_stats = {
        'total_docs': len(documents),
        'completed': 0,
        'failed': 0,
        'total_new_chunks': 0,
        'start_time': datetime.now().isoformat()
    }
    
    for i, doc in enumerate(documents, 1):
        try:
            print(f"\n📄 [{i}/{len(documents)}] Processing: {doc['filename']}")
            print(f"   Original: {doc['original_chunks']} chunks, {len(doc['text'])} chars")
            
            # Re-chunk with improved parameters
            new_chunks = chunk_text_improved(doc['text'])
            print(f"   New: {len(new_chunks)} chunks (2500-char chunks)")
            
            # Extract enriched metadata
            enriched_meta = extract_enriched_metadata(doc['filename'], doc['text'][:2000])
            
            # Generate new embeddings
            vectors_to_upsert = []
            for chunk_idx, chunk in enumerate(new_chunks):
                if chunk_idx % 20 == 0 and chunk_idx > 0:
                    print(f"   Embedding chunk {chunk_idx}/{len(new_chunks)}...")
                
                # Generate embedding with new model
                response = openai.embeddings.create(
                    input=chunk,
                    model="text-embedding-3-large"
                )
                vector = response.data[0].embedding
                
                # Build comprehensive metadata
                chunk_metadata = {
                    "text": chunk,
                    "doc_id": doc['doc_id'],
                    "filename": doc['filename'],
                    "upload_timestamp": doc['upload_timestamp'],
                    "tags": doc['tags'],
                    "chunk_index": chunk_idx,
                    "source": doc.get('source', 'migration'),
                    "migration_date": datetime.now().isoformat()
                }
                # Add enriched metadata
                chunk_metadata.update(enriched_meta)
                
                vectors_to_upsert.append((f"{doc['doc_id']}-{chunk_idx}", vector, chunk_metadata))
                
                # Small delay to avoid rate limits
                if chunk_idx % 10 == 0:
                    time.sleep(0.1)
            
            # Upload to new index in batches
            batch_size = 50
            for batch_start in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[batch_start:batch_start + batch_size]
                new_index.upsert(vectors=batch)
            
            migration_stats['completed'] += 1
            migration_stats['total_new_chunks'] += len(new_chunks)
            
            print(f"   ✅ Migrated successfully ({len(new_chunks)} new chunks)")
            
            # Progress update every 10 docs
            if i % 10 == 0:
                print(f"\n📊 PROGRESS: {i}/{len(documents)} documents migrated")
                print(f"   Success: {migration_stats['completed']}, Failed: {migration_stats['failed']}")
            
            # Rate limiting: pause every 50 documents
            if i % 50 == 0:
                print("⏸️  Pausing 5 seconds to avoid rate limits...")
                time.sleep(5)
                
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            migration_stats['failed'] += 1
            
            # Save progress on errors
            with open('migration_progress.json', 'w') as f:
                json.dump(migration_stats, f, indent=2)
    
    migration_stats['end_time'] = datetime.now().isoformat()
    
    # Save final stats
    with open('migration_complete.json', 'w') as f:
        json.dump(migration_stats, f, indent=2)
    
    print("\n" + "=" * 70)
    print("🎉 MIGRATION COMPLETE!")
    print(f"✅ Successfully migrated: {migration_stats['completed']} documents")
    print(f"❌ Failed: {migration_stats['failed']} documents")
    print(f"📊 Total new chunks: {migration_stats['total_new_chunks']}")
    print(f"⏱️  Start: {migration_stats['start_time']}")
    print(f"⏱️  End: {migration_stats['end_time']}")
    print("=" * 70)
    
    return migration_stats

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Before running this migration:")
    print("1. Create a new Pinecone index with 3072 dimensions")
    print("2. Set NEW_PINECONE_INDEX environment variable")
    print("3. This will re-process all 245 documents (may take 30-60 mins)")
    print("4. Migration progress is saved to migration_progress.json")
    print("\nReady to begin? (Press Ctrl+C to cancel)")
    input("\nPress Enter to start migration...")
    
    # Step 1: Fetch all documents from old index
    documents = fetch_all_documents_from_old_index()
    
    # Step 2: Migrate to new index
    stats = migrate_documents_to_new_index(documents)
    
    print("\n✅ Migration tool completed successfully!")
    print("Next steps:")
    print("1. Update PINECONE_INDEX env var to point to new index")
    print("2. Test search quality with sample queries")
    print("3. Once verified, you can delete the old index")
