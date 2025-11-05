"""
Automated Batch Processing (No Confirmation Required)
Processes all documents without interactive prompts.
"""

import asyncio
from src.scripts.build_initial_graph import process_all_documents


async def main():
    """Run batch processing without confirmation"""
    print("=" * 80)
    print("🚀 STARTING AUTOMATED BATCH PROCESSING")
    print("=" * 80)
    print()
    print("Processing all 340 documents from Pinecone...")
    print("Estimated cost: $8-10")
    print("Estimated time: 45-90 minutes")
    print()
    
    try:
        result = await process_all_documents()
        print()
        print("=" * 80)
        print("✅ BATCH PROCESSING COMPLETE!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Check /data/graph-quality-report.json for quality metrics")
        print("  2. Check /data/failed-extractions.json for any errors")
        print("  3. View progress at GET /api/batch-progress")
        print("  4. Proceed to Stage 4: Visualization")
        print()
    except KeyboardInterrupt:
        print("\n⚠️  Batch processing interrupted by user")
        print("Progress is saved. Run again to resume from where you left off.")
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
