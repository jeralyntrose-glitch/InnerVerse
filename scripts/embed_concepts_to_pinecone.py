#!/usr/bin/env python3
"""
PHASE 6 PREREQUISITE: Embed Knowledge Graph Concepts to Pinecone

This script:
1. Loads all concepts from the knowledge graph JSON
2. Creates embeddings for each concept (name + description)
3. Upserts to Pinecone with type='concept' metadata
4. Runs ONCE before the assignment script
"""

import os
import json
import time
from typing import List, Dict
from pinecone import Pinecone
from openai import OpenAI

# Initialize clients
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
pinecone_index = pc.Index(os.environ.get('PINECONE_INDEX', 'mbti-knowledge'))

# Constants
EMBEDDING_MODEL = 'text-embedding-3-large'
EMBEDDING_DIMENSIONS = 1536  # FIXED: Match Pinecone index dimension (was 3072)
BATCH_SIZE = 100


def load_knowledge_graph() -> Dict:
    """Load knowledge graph from JSON file"""
    kg_path = 'data/knowledge-graph.json'
    
    if not os.path.exists(kg_path):
        raise FileNotFoundError(f"Knowledge graph not found at {kg_path}")
    
    with open(kg_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_embedding(text: str) -> List[float]:
    """Create OpenAI embedding for text"""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS
    )
    return response.data[0].embedding


def prepare_concept_for_embedding(concept: Dict) -> Dict:
    """
    Prepare a concept for embedding
    
    Knowledge graph node structure:
    - id: concept ID
    - label: concept name
    - properties.description: short description
    - definition: longer definition
    - category: category like "advanced"
    
    Returns:
        Dict with 'id', 'text', and 'metadata' keys
    """
    # Create rich text for embedding
    text_parts = [concept['label']]
    
    # Add description from properties
    props_desc = concept.get('properties', {}).get('description')
    if props_desc:
        text_parts.append(props_desc)
    
    # Add definition
    if concept.get('definition'):
        text_parts.append(concept['definition'])
    
    embedding_text = ' '.join(text_parts)
    
    # Prepare metadata
    metadata = {
        'type': 'concept',
        'concept_id': concept['id'],
        'concept_name': concept['label'],
        'description': concept.get('definition', props_desc or ''),
        'category': concept.get('category', ''),
    }
    
    return {
        'id': f"concept_{concept['id']}",
        'text': embedding_text,
        'metadata': metadata
    }


def batch_upsert_concepts(concepts: List[Dict]) -> int:
    """
    Embed and upsert concepts to Pinecone in batches
    
    Returns:
        Total number of concepts embedded
    """
    total = len(concepts)
    embedded_count = 0
    total_cost = 0.0
    
    print(f"\n🚀 Starting to embed {total} concepts...")
    print(f"📊 Model: {EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS} dimensions)")
    print(f"📦 Batch size: {BATCH_SIZE}\n")
    
    for i in range(0, total, BATCH_SIZE):
        batch = concepts[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"[Batch {batch_num}/{total_batches}] Processing {len(batch)} concepts...")
        
        # Prepare batch
        prepared_concepts = [prepare_concept_for_embedding(c) for c in batch]
        
        # Create embeddings
        texts = [c['text'] for c in prepared_concepts]
        print(f"  📊 Creating embeddings...")
        
        embeddings_response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
            dimensions=EMBEDDING_DIMENSIONS
        )
        
        # Calculate cost (text-embedding-3-large: $0.13 per 1M tokens)
        tokens_used = embeddings_response.usage.total_tokens
        batch_cost = (tokens_used / 1_000_000) * 0.13
        total_cost += batch_cost
        
        # Prepare vectors for Pinecone
        vectors = []
        for j, prepared_concept in enumerate(prepared_concepts):
            embedding = embeddings_response.data[j].embedding
            vectors.append({
                'id': prepared_concept['id'],
                'values': embedding,
                'metadata': prepared_concept['metadata']
            })
        
        # Upsert to Pinecone with error handling
        print(f"  💾 Upserting to Pinecone...")
        try:
            pinecone_index.upsert(vectors=vectors)
            embedded_count += len(batch)
            print(f"  ✅ Batch {batch_num} upserted successfully")
            print(f"  ✅ Progress: {embedded_count}/{total} concepts (${batch_cost:.4f})\n")
        except Exception as e:
            print(f"❌ ERROR upserting batch {batch_num}: {e}")
            print(f"   Vector dimension: {len(vectors[0]['values']) if vectors else 'N/A'}")
            print(f"   First vector ID: {vectors[0]['id'] if vectors else 'N/A'}")
            raise  # Re-raise to stop script
        
        # Rate limiting
        time.sleep(0.5)
    
    return embedded_count, total_cost


def main():
    print("=" * 70)
    print("EMBED KNOWLEDGE GRAPH CONCEPTS TO PINECONE - PHASE 6 PREREQUISITE")
    print("=" * 70)
    
    # Load knowledge graph
    print("\n📚 Loading knowledge graph...")
    kg = load_knowledge_graph()
    concepts = kg.get('nodes', [])
    print(f"✅ Found {len(concepts)} concepts in knowledge graph\n")
    
    if not concepts:
        print("❌ No concepts found in knowledge graph!")
        return
    
    # Test embedding dimension before starting
    print("🧪 Testing embedding dimension...")
    test_embedding = create_embedding("test")
    print(f"✅ Embedding dimension: {len(test_embedding)}")
    assert len(test_embedding) == 1536, f"Dimension mismatch! Expected 1536, got {len(test_embedding)}"
    print()
    
    # Embed and upsert
    embedded_count, total_cost = batch_upsert_concepts(concepts)
    
    # Summary
    print("=" * 70)
    print("EMBEDDING COMPLETE")
    print("=" * 70)
    print(f"✅ Embedded {embedded_count} concepts")
    print(f"💰 Total cost: ~${total_cost:.4f}")
    print(f"📊 Average: ${(total_cost / embedded_count):.6f} per concept")
    
    # Verification: Test that concepts are queryable with type filter
    print("\n🧪 VERIFICATION: Testing type='concept' filter...")
    test_query = pinecone_index.query(
        vector=[0.01] * 1536,
        filter={'type': 'concept'},
        top_k=5,
        include_metadata=True
    )
    concepts_found = len(test_query.matches)
    print(f"✅ Found {concepts_found} concept vectors with type filter")
    
    if concepts_found > 0:
        print("\nSample concepts:")
        for match in test_query.matches[:3]:
            name = match.metadata.get('concept_name', 'N/A')
            print(f"  - {name}")
    
    assert concepts_found > 0, "❌ Type filter not working! No concepts found."
    
    print("\n🎯 Concepts are now searchable in Pinecone with type='concept'")
    print("🚀 You can now run: python scripts/assign_concepts_to_lessons.py")
    print("=" * 70)


if __name__ == '__main__':
    main()
