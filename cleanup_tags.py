#!/usr/bin/env python3
"""
Cleanup script to remove category prefixes from Pinecone tags.
Converts tags like "Compatibility Themes: Sexual Compatibility" to "Sexual Compatibility"
"""
import os
from pinecone import Pinecone

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "mbti-knowledge")

def cleanup_tags():
    """Remove category prefixes from all tags in Pinecone"""
    print("🧹 Starting tag cleanup...")
    
    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX)
    
    # Get index stats
    stats = index.describe_index_stats()
    total_vectors = stats.total_vector_count
    print(f"📊 Total vectors in index: {total_vectors}")
    
    # Fetch all vectors in batches
    updated_count = 0
    batch_size = 100
    
    # Query all vectors (we'll fetch them in chunks using pagination)
    # Pinecone doesn't have a direct "list all" method, so we need to query
    print("\n🔍 Scanning for tags with category prefixes...")
    
    # Get unique document IDs first
    # We'll query with a dummy vector to get all results
    dummy_query = [0.0] * 1536  # OpenAI embedding dimension
    
    results = index.query(
        vector=dummy_query,
        top_k=10000,  # Max allowed
        include_metadata=True
    )
    
    print(f"📝 Found {len(results.matches)} vectors to check")
    
    # Process each vector
    vectors_to_update = []
    
    for match in results.matches:
        vector_id = match.id
        metadata = match.metadata
        
        if 'tags' not in metadata:
            continue
        
        tags = metadata.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        
        # Check if any tags have category prefixes (contain colons)
        cleaned_tags = []
        has_prefix = False
        
        for tag in tags:
            if ':' in tag:
                # Remove category prefix (everything before and including the colon)
                cleaned_tag = tag.split(':', 1)[1].strip()
                cleaned_tags.append(cleaned_tag)
                has_prefix = True
                print(f"  ✂️  '{tag}' → '{cleaned_tag}'")
            else:
                cleaned_tags.append(tag)
        
        # If we found prefixes, prepare update
        if has_prefix:
            updated_metadata = metadata.copy()
            updated_metadata['tags'] = cleaned_tags
            
            vectors_to_update.append({
                'id': vector_id,
                'metadata': updated_metadata
            })
            updated_count += 1
    
    # Update vectors in batches
    if vectors_to_update:
        print(f"\n📤 Updating {len(vectors_to_update)} vectors...")
        
        for i in range(0, len(vectors_to_update), batch_size):
            batch = vectors_to_update[i:i + batch_size]
            
            # Upsert with updated metadata (need to fetch embeddings too)
            upsert_data = []
            for item in batch:
                # Fetch the original vector
                fetch_result = index.fetch(ids=[item['id']])
                if item['id'] in fetch_result.vectors:
                    original_vector = fetch_result.vectors[item['id']]
                    upsert_data.append({
                        'id': item['id'],
                        'values': original_vector.values,
                        'metadata': item['metadata']
                    })
            
            if upsert_data:
                index.upsert(vectors=upsert_data)
                print(f"  ✅ Updated batch {i//batch_size + 1}")
        
        print(f"\n✅ Cleanup complete! Updated {updated_count} vectors with cleaned tags.")
    else:
        print("\n✅ No tags with category prefixes found. All tags are already clean!")

if __name__ == "__main__":
    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not set")
        exit(1)
    
    cleanup_tags()
