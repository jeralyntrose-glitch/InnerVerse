"""
Test Batch Processing with Small Document Subset
Tests the batch processing logic before running on all 340 documents.
"""

import asyncio
import json
import os
from src.scripts.build_initial_graph import (
    get_all_pinecone_documents,
    update_batch_progress,
    log_failed_extraction,
    generate_quality_report
)
from src.services.concept_extractor import extract_concepts
from src.services.knowledge_graph_manager import KnowledgeGraphManager


async def test_batch_processing_subset():
    """Test with first 5 documents"""
    
    print("=" * 80)
    print("🧪 TESTING BATCH PROCESSING (5 DOCUMENT SUBSET)")
    print("=" * 80)
    print()
    
    try:
        print("📥 Fetching documents from Pinecone...")
        all_docs = await get_all_pinecone_documents()
        
        test_docs = all_docs[:5]
        
        print(f"✅ Selected {len(test_docs)} documents for testing:")
        for i, doc in enumerate(test_docs):
            title = doc['metadata'].get('title', doc['id'])
            print(f"   {i+1}. {title[:60]}")
        print()
        
        manager = KnowledgeGraphManager()
        graph = manager.load_graph()
        
        if 'metadata' not in graph:
            graph['metadata'] = {}
        if 'processed_documents' not in graph['metadata']:
            graph['metadata']['processed_documents'] = []
        
        initial_node_count = len(graph.get('nodes', []))
        initial_edge_count = len(graph.get('edges', []))
        
        print(f"📊 Initial graph state:")
        print(f"   Nodes: {initial_node_count}")
        print(f"   Edges: {initial_edge_count}")
        print(f"   Processed docs: {len(graph['metadata']['processed_documents'])}")
        print()
        
        processed_ids = set(graph['metadata']['processed_documents'])
        to_process = [doc for doc in test_docs if doc['id'] not in processed_ids]
        
        print(f"⏳ To process: {len(to_process)}")
        print()
        
        if len(to_process) == 0:
            print("⚠️  All test documents already processed!")
            print("   To retest, clear processed_documents in knowledge-graph.json")
            return
        
        error_count = 0
        
        for i, doc in enumerate(to_process):
            doc_id = doc['id']
            doc_metadata = doc['metadata']
            doc_text = doc_metadata.get('text', '')
            doc_title = doc_metadata.get('title', doc_id)
            
            print(f"[{i+1}/{len(to_process)}] Processing: {doc_title[:60]}")
            
            if not doc_text or len(doc_text.strip()) < 100:
                print(f"   ⚠️  Skipping: insufficient text content")
                
                graph = manager.load_graph()
                if 'metadata' not in graph:
                    graph['metadata'] = {}
                if 'processed_documents' not in graph['metadata']:
                    graph['metadata']['processed_documents'] = []
                graph['metadata']['processed_documents'].append(doc_id)
                manager.save_graph(graph)
                continue
            
            try:
                print(f"   🔍 Extracting concepts...")
                extracted = await extract_concepts(doc_text, doc_id)
                
                if not extracted:
                    print(f"   ⚠️  Extraction failed")
                    error_count += 1
                    await log_failed_extraction(doc_id, "Extraction returned None")
                    
                    graph = manager.load_graph()
                    if 'metadata' not in graph:
                        graph['metadata'] = {}
                    if 'processed_documents' not in graph['metadata']:
                        graph['metadata']['processed_documents'] = []
                    graph['metadata']['processed_documents'].append(doc_id)
                    manager.save_graph(graph)
                    continue
                
                concepts_added = 0
                for concept in extracted.get("concepts", []):
                    await manager.add_node({
                        **concept,
                        "source_documents": [doc_id]
                    })
                    concepts_added += 1
                
                relationships_added = 0
                for rel in extracted.get("relationships", []):
                    source_node = await manager.find_node_by_label(rel["from"])
                    target_node = await manager.find_node_by_label(rel["to"])
                    
                    if source_node and target_node:
                        await manager.add_edge({
                            "source": source_node["id"],
                            "target": target_node["id"],
                            "relationship_type": rel["type"],
                            "evidence_samples": [rel.get("evidence", "")],
                            "source_documents": [doc_id]
                        })
                        relationships_added += 1
                
                print(f"   ✅ {concepts_added} concepts, {relationships_added} relationships")
                
                graph = manager.load_graph()
                if 'metadata' not in graph:
                    graph['metadata'] = {}
                if 'processed_documents' not in graph['metadata']:
                    graph['metadata']['processed_documents'] = []
                graph['metadata']['processed_documents'].append(doc_id)
                manager.save_graph(graph)
                
                await asyncio.sleep(2)
                
            except Exception as error:
                print(f"   ❌ Error: {error}")
                error_count += 1
                await log_failed_extraction(doc_id, str(error))
                
                graph = manager.load_graph()
                if 'metadata' not in graph:
                    graph['metadata'] = {}
                if 'processed_documents' not in graph['metadata']:
                    graph['metadata']['processed_documents'] = []
                graph['metadata']['processed_documents'].append(doc_id)
                manager.save_graph(graph)
        
        manager.save_graph(graph)
        graph = manager.load_graph()
        
        final_node_count = len(graph.get('nodes', []))
        final_edge_count = len(graph.get('edges', []))
        
        print()
        print("=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80)
        print(f"📈 Graph growth:")
        print(f"   Nodes: {initial_node_count} → {final_node_count} (+{final_node_count - initial_node_count})")
        print(f"   Edges: {initial_edge_count} → {final_edge_count} (+{final_edge_count - initial_edge_count})")
        print(f"   Processed docs: {len(graph['metadata']['processed_documents'])}")
        print(f"❌ Errors: {error_count}")
        print()
        
        print("📊 Generating quality report...")
        report = await generate_quality_report(graph)
        
        print(f"   Health status: {report['health_status']}")
        print(f"   Avg relationships per concept: {report['summary']['avg_relationships_per_concept']}")
        print(f"   Orphaned edges: {report['quality_metrics']['orphaned_edges']}")
        print(f"   Isolated nodes: {report['quality_metrics']['nodes_with_no_edges']}")
        print()
        
        if report['health_status'] == 'healthy':
            print("🎉 Batch processing logic working correctly!")
            print("   Ready to run on all 340 documents")
        else:
            print("⚠️  Some issues detected. Review quality report for details.")
        
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(test_batch_processing_subset())
