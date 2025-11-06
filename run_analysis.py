"""
CLI Runner for Knowledge Graph Analysis
"""

from src.scripts.analyze_graph import analyze_frequency_distribution


if __name__ == "__main__":
    print("🔍 Starting Knowledge Graph Analysis...")
    print()
    
    result = analyze_frequency_distribution()
    
    print()
    print("✅ Analysis complete!")
    print()
    print("Next steps:")
    print("  1. Review the frequency distribution above")
    print("  2. Check the recommended threshold for filtering")
    print("  3. Decide: filter by frequency OR run merge script")
    print("  4. For merge: python run_merge_auto.py")
