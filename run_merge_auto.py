"""
Automated Merge Runner (No Confirmation Required)
For running merge without interactive prompts.
"""

import asyncio
import sys
from src.scripts.merge_concepts import merge_similar_concepts, preview_merges


def main():
    """Run merge automatically with default settings"""
    threshold = 0.85  # Default threshold
    
    print("=" * 80)
    print("🔧 AUTOMATED KNOWLEDGE GRAPH MERGE")
    print("=" * 80)
    print(f"🎯 Threshold: {threshold}")
    print()
    
    # Preview first
    print("📋 Preview:")
    print()
    preview_merges(threshold)
    print()
    
    # Run merge
    print("🚀 Starting merge...")
    print()
    merge_similar_concepts(threshold, create_backup=True)
    print()
    print("✅ Merge complete!")
    print()
    print("Files created:")
    print("  - /data/knowledge-graph.json (updated)")
    print("  - /data/knowledge-graph-backup-*.json (backup)")
    print("  - /data/merge-report.json (detailed report)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
