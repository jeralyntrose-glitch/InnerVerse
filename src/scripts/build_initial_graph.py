"""
Batch Document Processing Script
Processes all documents from Pinecone and builds the knowledge graph.
"""

import asyncio
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pinecone import Pinecone
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.services.concept_extractor import extract_concepts
from src.services.knowledge_graph_manager import KnowledgeGraphManager


BATCH_PROGRESS_FILE = "data/batch-progress.json"
FAILED_EXTRACTIONS_FILE = "data/failed-extractions.json"
QUALITY_REPORT_FILE = "data/graph-quality-report.json"


async def get_all_pinecone_documents() -> List[Dict[str, Any]]:
    """Fetch all document IDs and metadata from Pinecone"""
    print("📥 Fetching documents from Pinecone...")
    
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "mbti-knowledge-v2")
    
    if not api_key:
        raise ValueError("PINECONE_API_KEY not set")
    
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    
    all_docs = []
    
    try:
        stats = index.describe_index_stats()
        total_vectors = stats.get('total_vector_count', 0)
        print(f"📊 Total vectors in Pinecone: {total_vectors:,}")
        
        namespaces = stats.get('namespaces', {})
        default_namespace = namespaces.get('', {})
        vector_count = default_namespace.get('vector_count', 0)
        
        print(f"📊 Vectors in default namespace: {vector_count:,}")
        
        dummy_vector = [0.0] * 3072
        
        query_response = index.query(
            vector=dummy_vector,
            top_k=10000,
            include_metadata=True
        )
        
        doc_map = {}
        for match in query_response.get('matches', []):
            metadata = match.get('metadata', {})
            doc_id = metadata.get('doc_id', '')
            
            if doc_id and doc_id not in doc_map:
                doc_map[doc_id] = {
                    'id': doc_id,
                    'metadata': metadata
                }
        
        all_docs = list(doc_map.values())
        
        print(f"✅ Found {len(all_docs)} unique documents")
        
        if all_docs:
            sample = all_docs[0]
            print(f"📄 Sample document ID: {sample['id']}")
            print(f"   Title: {sample['metadata'].get('title', 'N/A')}")
        
        return all_docs
        
    except Exception as e:
        print(f"❌ Error fetching from Pinecone: {e}")
        raise


async def update_batch_progress(
    status: str,
    current: int,
    total: int,
    current_doc: str = "",
    errors: int = 0,
    start_time: Optional[datetime] = None
) -> None:
    """Update batch progress file"""
    
    progress_data = {
        "status": status,
        "total_documents": total,
        "processed": current,
        "current_document": current_doc,
        "errors": errors,
        "last_updated": datetime.now().isoformat()
    }
    
    if start_time:
        progress_data["started_at"] = start_time.isoformat()
        
        if current > 0 and current < total:
            elapsed = datetime.now() - start_time
            avg_time_per_doc = elapsed.total_seconds() / current
            remaining_docs = total - current
            estimated_seconds = avg_time_per_doc * remaining_docs
            
            eta = datetime.now() + timedelta(seconds=estimated_seconds)
            progress_data["estimated_completion"] = eta.isoformat()
            progress_data["eta_readable"] = eta.strftime("%Y-%m-%d %H:%M:%S")
    
    os.makedirs(os.path.dirname(BATCH_PROGRESS_FILE), exist_ok=True)
    
    with open(BATCH_PROGRESS_FILE, 'w') as f:
        json.dump(progress_data, f, indent=2)


async def log_failed_extraction(doc_id: str, error: str) -> None:
    """Log failed extraction to file"""
    
    os.makedirs(os.path.dirname(FAILED_EXTRACTIONS_FILE), exist_ok=True)
    
    failure_entry = {
        "document_id": doc_id,
        "timestamp": datetime.now().isoformat(),
        "error": str(error)
    }
    
    try:
        with open(FAILED_EXTRACTIONS_FILE, 'r') as f:
            failures = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        failures = []
    
    failures.append(failure_entry)
    
    with open(FAILED_EXTRACTIONS_FILE, 'w') as f:
        json.dump(failures, f, indent=2)


async def generate_quality_report(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Generate quality report for the knowledge graph"""
    
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    metadata = graph.get('metadata', {})
    
    node_ids = {node['id'] for node in nodes}
    
    orphaned_edges = []
    for edge in edges:
        if edge['source'] not in node_ids or edge['target'] not in node_ids:
            orphaned_edges.append(edge)
    
    category_counts = {}
    type_counts = {}
    for node in nodes:
        cat = node.get('category', 'unknown')
        typ = node.get('type', 'unknown')
        category_counts[cat] = category_counts.get(cat, 0) + 1
        type_counts[typ] = type_counts.get(typ, 0) + 1
    
    relationship_type_counts = {}
    for edge in edges:
        rel_type = edge.get('relationship_type', 'unknown')
        relationship_type_counts[rel_type] = relationship_type_counts.get(rel_type, 0) + 1
    
    nodes_with_no_edges = 0
    for node in nodes:
        node_id = node['id']
        has_edge = any(
            edge['source'] == node_id or edge['target'] == node_id
            for edge in edges
        )
        if not has_edge:
            nodes_with_no_edges += 1
    
    avg_relationships_per_concept = len(edges) / len(nodes) if nodes else 0
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_concepts": len(nodes),
            "total_relationships": len(edges),
            "documents_processed": len(metadata.get('processed_documents', [])),
            "avg_relationships_per_concept": round(avg_relationships_per_concept, 2)
        },
        "quality_metrics": {
            "orphaned_edges": len(orphaned_edges),
            "nodes_with_no_edges": nodes_with_no_edges,
            "orphaned_edge_percentage": round(len(orphaned_edges) / len(edges) * 100, 2) if edges else 0,
            "isolated_node_percentage": round(nodes_with_no_edges / len(nodes) * 100, 2) if nodes else 0
        },
        "category_distribution": category_counts,
        "type_distribution": type_counts,
        "relationship_type_distribution": relationship_type_counts,
        "health_status": "healthy" if len(orphaned_edges) == 0 and nodes_with_no_edges < len(nodes) * 0.1 else "needs_attention"
    }
    
    os.makedirs(os.path.dirname(QUALITY_REPORT_FILE), exist_ok=True)
    
    with open(QUALITY_REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report


async def process_all_documents() -> Dict[str, Any]:
    """Main batch processing function"""
    
    start_time = datetime.now()
    error_count = 0
    
    print("=" * 80)
    print("🚀 BATCH DOCUMENT PROCESSING")
    print("=" * 80)
    print()
    
    try:
        all_docs = await get_all_pinecone_documents()
        
        manager = KnowledgeGraphManager()
        graph = manager.load_graph()
        
        if 'metadata' not in graph:
            graph['metadata'] = {}
        if 'processed_documents' not in graph['metadata']:
            graph['metadata']['processed_documents'] = []
        
        processed_ids = set(graph['metadata']['processed_documents'])
        to_process = [doc for doc in all_docs if doc['id'] not in processed_ids]
        
        total_docs = len(all_docs)
        already_processed = len(processed_ids)
        to_process_count = len(to_process)
        
        print(f"📊 Total documents in Pinecone: {total_docs}")
        print(f"✅ Already processed: {already_processed}")
        print(f"⏳ To process: {to_process_count}")
        print()
        
        if to_process_count == 0:
            print("🎉 All documents already processed!")
            await update_batch_progress("complete", total_docs, total_docs, "", error_count, start_time)
            return graph['metadata']
        
        await update_batch_progress("running", already_processed, total_docs, "", error_count, start_time)
        
        for i, doc in enumerate(to_process):
            doc_id = doc['id']
            doc_metadata = doc['metadata']
            doc_text = doc_metadata.get('text', '')
            doc_title = doc_metadata.get('title', doc_id)
            
            current_num = already_processed + i + 1
            
            print(f"\n[{current_num}/{total_docs}] Processing: {doc_title[:60]}")
            
            await update_batch_progress("running", current_num - 1, total_docs, doc_title, error_count, start_time)
            
            if not doc_text or len(doc_text.strip()) < 100:
                print(f"⚠️  Skipping {doc_id}: insufficient text content")
                
                graph = manager.load_graph()
                if 'metadata' not in graph:
                    graph['metadata'] = {}
                if 'processed_documents' not in graph['metadata']:
                    graph['metadata']['processed_documents'] = []
                graph['metadata']['processed_documents'].append(doc_id)
                manager.save_graph(graph)
                continue
            
            try:
                extracted = await extract_concepts(doc_text, doc_id)
                
                if not extracted:
                    print(f"⚠️  Failed to extract from {doc_id}")
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
                
                if (i + 1) % 10 == 0:
                    print(f"   💾 Progress saved: {current_num} documents processed")
                
                await asyncio.sleep(2)
                
            except Exception as error:
                print(f"   ❌ Error processing {doc_id}: {error}")
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
        
        print("\n" + "=" * 80)
        print("🎉 BATCH PROCESSING COMPLETE!")
        print("=" * 80)
        print(f"📈 Total concepts: {len(graph['nodes'])}")
        print(f"🔗 Total relationships: {len(graph['edges'])}")
        print(f"📚 Documents processed: {len(graph['metadata']['processed_documents'])}")
        print(f"❌ Errors: {error_count}")
        print()
        
        print("📊 Generating quality report...")
        report = await generate_quality_report(graph)
        
        print(f"   Health status: {report['health_status']}")
        print(f"   Avg relationships per concept: {report['summary']['avg_relationships_per_concept']}")
        print(f"   Orphaned edges: {report['quality_metrics']['orphaned_edges']}")
        print(f"   Isolated nodes: {report['quality_metrics']['nodes_with_no_edges']}")
        print()
        
        await update_batch_progress("complete", total_docs, total_docs, "", error_count, start_time)
        
        return graph['metadata']
        
    except Exception as e:
        print(f"\n❌ BATCH PROCESSING FAILED: {e}")
        await update_batch_progress("failed", 0, 0, str(e), error_count, start_time)
        raise


if __name__ == "__main__":
    asyncio.run(process_all_documents())
