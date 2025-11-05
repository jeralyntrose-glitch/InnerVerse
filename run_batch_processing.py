"""
CLI Runner for Batch Document Processing
Processes all documents from Pinecone and builds the knowledge graph.
"""

import asyncio
import os
from src.scripts.build_initial_graph import process_all_documents, get_all_pinecone_documents


async def estimate_cost():
    """Estimate processing cost based on documents to process"""
    try:
        all_docs = await get_all_pinecone_documents()
        
        with open("data/knowledge-graph.json", "r") as f:
            import json
            graph = json.load(f)
            processed = set(graph.get("metadata", {}).get("processed_documents", []))
        
        to_process = len([doc for doc in all_docs if doc['id'] not in processed])
        
        avg_cost_per_doc = 0.027
        estimated_total = to_process * avg_cost_per_doc
        
        return to_process, estimated_total
    except:
        return None, None


async def main():
    """Main entry point"""
    print("=" * 80)
    print("🚀 KNOWLEDGE GRAPH BATCH PROCESSING")
    print("=" * 80)
    print()
    print("This will process all unprocessed documents from Pinecone and")
    print("extract concepts/relationships using Claude API.")
    print()
    
    to_process, estimated_cost = await estimate_cost()
    
    if to_process is not None:
        print(f"📊 Documents to process: {to_process}")
        print(f"💰 Estimated cost: ${estimated_cost:.2f}")
        print(f"⏱️  Estimated time: {to_process * 15 / 60:.1f} minutes")
    else:
        print("💰 Estimated cost: $8-10")
        print("⏱️  Estimated time: 45-90 minutes")
    
    print()
    print("Features:")
    print("  ✅ Auto-saves progress every 10 documents")
    print("  ✅ Can resume if interrupted")
    print("  ✅ Tracks failed extractions")
    print("  ✅ Generates quality report")
    print()
    
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("❌ Aborted")
        return
    
    print()
    print("🚀 Starting batch processing...")
    print()
    
    try:
        result = await process_all_documents()
        print()
        print("=" * 80)
        print("✅ SUCCESS!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Check /data/graph-quality-report.json for quality metrics")
        print("  2. Check /data/failed-extractions.json for any errors")
        print("  3. View progress at GET /api/batch-progress")
        print("  4. Proceed to Stage 4: Visualization")
        print()
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ BATCH PROCESSING FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Recovery:")
        print("  - Progress is auto-saved every 10 documents")
        print("  - Run this script again to resume from where it left off")
        print("  - Check /data/failed-extractions.json for details")
        print()
        raise


if __name__ == "__main__":
    asyncio.run(main())
