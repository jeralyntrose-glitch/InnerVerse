"""
Knowledge Graph Frequency Analysis
Analyzes concept frequency distribution to inform filtering/merge decisions.
"""

import json
from src.services.knowledge_graph_manager import KnowledgeGraphManager


def analyze_frequency_distribution():
    """Analyze concept frequency distribution in existing graph"""
    
    manager = KnowledgeGraphManager()
    graph = manager.load_graph()
    
    nodes = graph.get('nodes', [])
    total_concepts = len(nodes)
    
    print("="*80)
    print("📊 KNOWLEDGE GRAPH ANALYSIS")
    print("="*80)
    print(f"Total concepts: {total_concepts}")
    print(f"Total relationships: {len(graph.get('edges', []))}")
    print()
    
    # Get frequency distribution
    freq_dist = {}
    for node in nodes:
        freq = node.get('frequency', 1)
        freq_dist[freq] = freq_dist.get(freq, 0) + 1
    
    print("="*80)
    print("📈 FREQUENCY DISTRIBUTION (Top 30)")
    print("="*80)
    print(f"{'Frequency':<15} {'Count':<10} {'Percentage':<12} {'Cumulative':<12}")
    print("-"*80)
    
    cumulative = 0
    for freq in sorted(freq_dist.keys(), reverse=True)[:30]:
        count = freq_dist[freq]
        percentage = (count / total_concepts) * 100
        cumulative += count
        cumulative_pct = (cumulative / total_concepts) * 100
        print(f"{freq:<15} {count:<10} {percentage:>10.1f}% {cumulative_pct:>10.1f}%")
    
    print("\n" + "="*80)
    print("🎯 THRESHOLD ANALYSIS (What filtering would give us)")
    print("="*80)
    print(f"{'Min Frequency':<20} {'Concepts Shown':<20} {'Reduction':<15}")
    print("-"*80)
    
    for threshold in [1, 2, 3, 5, 7, 10, 15, 20]:
        count = sum(1 for node in nodes if node.get('frequency', 1) >= threshold)
        reduction = ((total_concepts - count) / total_concepts) * 100
        print(f"{'>= ' + str(threshold):<20} {count:<20} {reduction:>12.1f}%")
    
    print("\n" + "="*80)
    print("🏆 TOP 30 MOST FREQUENT CONCEPTS")
    print("="*80)
    
    sorted_nodes = sorted(nodes, key=lambda n: n.get('frequency', 1), reverse=True)
    
    for i, node in enumerate(sorted_nodes[:30], 1):
        freq = node.get('frequency', 1)
        label = node.get('label', 'Unknown')
        category = node.get('category', 'N/A')
        print(f"{i:2d}. [{freq:3d}] {label[:60]:<60} ({category})")
    
    print("\n" + "="*80)
    print("📉 BOTTOM 20 LEAST FREQUENT CONCEPTS (The noise)")
    print("="*80)
    
    for i, node in enumerate(sorted_nodes[-20:], 1):
        freq = node.get('frequency', 1)
        label = node.get('label', 'Unknown')
        print(f"{i:2d}. [{freq:3d}] {label}")
    
    print("\n" + "="*80)
    print("🎨 CATEGORY BREAKDOWN")
    print("="*80)
    
    categories = {}
    for node in nodes:
        cat = node.get('category', 'uncategorized')
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_concepts) * 100
        print(f"{cat:<20} {count:>6} ({pct:>5.1f}%)")
    
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    # Calculate ideal threshold
    for threshold in [3, 5, 7, 10]:
        count = sum(1 for node in nodes if node.get('frequency', 1) >= threshold)
        if 150 <= count <= 400:
            print(f"✅ PERFECT: Use frequency >= {threshold} (gives {count} concepts)")
            break
    else:
        # Find closest
        for threshold in range(1, 30):
            count = sum(1 for node in nodes if node.get('frequency', 1) >= threshold)
            if count <= 400:
                print(f"📊 CLOSEST: Use frequency >= {threshold} (gives {count} concepts)")
                break
    
    print("\n" + "="*80)
    
    return {
        'total_concepts': total_concepts,
        'frequency_distribution': freq_dist,
        'top_concepts': [(n['label'], n.get('frequency', 1)) for n in sorted_nodes[:30]]
    }


if __name__ == "__main__":
    analyze_frequency_distribution()
