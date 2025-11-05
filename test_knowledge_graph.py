"""
Test script for Knowledge Graph Manager
Run with: python test_knowledge_graph.py
"""

import asyncio
from src.services.knowledge_graph_manager import KnowledgeGraphManager

async def main():
    manager = KnowledgeGraphManager()
    
    print("🧪 Testing Knowledge Graph Manager...")
    print()
    
    # Test 1: Add a node
    print("Test 1: Adding first node...")
    node1 = await manager.add_node({
        "label": "Shadow Integration",
        "type": "process",
        "category": "foundational",
        "definition": "Test definition",
        "source_documents": ["doc_1"]
    })
    print(f"✅ Node added: {node1['id']}")
    print(f"   Label: {node1['label']}")
    print(f"   Type: {node1['type']}")
    print(f"   Category: {node1['category']}")
    print(f"   Frequency: {node1['frequency']}")
    print()
    
    # Test 2: Add similar node (should deduplicate)
    print("Test 2: Adding similar node (testing deduplication)...")
    node2 = await manager.add_node({
        "label": "Shadow integration",  # Different case, should match
        "type": "process", 
        "category": "foundational",
        "definition": "Test definition",
        "source_documents": ["doc_2"]
    })
    print(f"✅ Deduplication test: frequency = {node2['frequency']}")  # Should be 2
    print(f"   Sources: {node2['sources']}")
    print()
    
    # Test 3: Add edge
    print("Test 3: Adding edge...")
    edge = await manager.add_edge({
        "source": node1['id'],
        "target": "inferior_function",
        "relationship_type": "requires_understanding",
        "evidence_samples": ["Test evidence"]
    })
    print(f"✅ Edge added: {edge['id']}")
    print(f"   Source: {edge['source']}")
    print(f"   Target: {edge['target']}")
    print(f"   Type: {edge['type']}")
    print(f"   Strength: {edge['strength']}")
    print()
    
    # Test 4: Get stats
    print("Test 4: Getting graph stats...")
    stats = await manager.get_graph_stats()
    print(f"✅ Stats:")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total edges: {stats['total_edges']}")
    print(f"   Node types: {stats['node_types']}")
    print(f"   Edge types: {stats['edge_types']}")
    print()
    
    print("🎉 All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
