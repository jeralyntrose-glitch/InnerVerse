"""
CLI Runner for Knowledge Graph Concept Merger
"""

import asyncio
import sys
from src.scripts.merge_concepts import merge_similar_concepts, preview_merges, test_threshold


async def main():
    """Run merge with preview and confirmation"""
    print("=" * 80)
    print("🔧 KNOWLEDGE GRAPH CONCEPT MERGER")
    print("=" * 80)
    print()
    
    # Show current state
    from src.services.knowledge_graph_manager import KnowledgeGraphManager
    manager = KnowledgeGraphManager()
    graph = await manager.load_graph()
    
    print(f"📊 Current state:")
    print(f"   Concepts: {len(graph['nodes'])}")
    print(f"   Relationships: {len(graph['edges'])}")
    print()
    
    # Test different thresholds
    print("🎯 Testing different similarity thresholds...")
    print()
    
    for threshold in [0.90, 0.85, 0.80]:
        stats = await test_threshold(threshold)
        print(f"Threshold {threshold}: {stats['final_concepts']} concepts "
              f"({stats['reduction_percentage']:.1f}% reduction)")
    
    print()
    print("-" * 80)
    
    # Get threshold from user
    print()
    print("Recommended starting point: 0.85")
    threshold_input = input("Enter similarity threshold (0.80-0.95) or press Enter for 0.85: ").strip()
    
    if threshold_input:
        try:
            threshold = float(threshold_input)
            if threshold < 0.70 or threshold > 1.0:
                print("❌ Threshold must be between 0.70 and 1.0")
                return
        except ValueError:
            print("❌ Invalid threshold value")
            return
    else:
        threshold = 0.85
    
    print()
    print(f"🎯 Using threshold: {threshold}")
    print()
    
    # Preview merges
    print("📋 Previewing merges...")
    print()
    await preview_merges(threshold)
    print()
    
    # Confirm
    confirm = input("Proceed with merge? (yes/no): ").strip().lower()
    
    if confirm == "yes":
        print()
        await merge_similar_concepts(threshold, create_backup=True)
        print()
        print("✅ Merge complete!")
        print()
        print("Next steps:")
        print("  1. Check /data/merge-report.json for details")
        print("  2. Review merged concepts in /data/knowledge-graph.json")
        print("  3. If unhappy with results, restore from backup")
        print("  4. Run again with different threshold if needed")
    else:
        print()
        print("❌ Merge cancelled")
        print()
        print("Tips:")
        print("  - Use higher threshold (0.90+) for conservative merge")
        print("  - Use lower threshold (0.80) for aggressive merge")
        print("  - Check /src/scripts/manual_merge.py for manual merging")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Merge cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
