"""
Knowledge Graph Concept Merger
Consolidates similar concepts to reduce graph complexity while preserving relationships.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple
from src.services.knowledge_graph_manager import KnowledgeGraphManager
from src.utils.graph_utils import fuzzy_match_label


# Protected terms - never merge if concepts contain different values
COGNITIVE_FUNCTIONS = ['Si', 'Se', 'Ni', 'Ne', 'Ti', 'Te', 'Fi', 'Fe']

FUNCTION_POSITIONS = ['Hero', 'Parent', 'Child', 'Inferior', 
                      'Nemesis', 'Critic', 'Trickster', 'Demon']

MBTI_TYPES = ['ENFP', 'INFP', 'ENTP', 'INTP', 'ENFJ', 'INFJ', 
              'ENTJ', 'INTJ', 'ESFP', 'ISFP', 'ESTP', 'ISTP',
              'ESFJ', 'ISFJ', 'ESTJ', 'ISTJ']

QUADRAS = ['Alpha', 'Beta', 'Gamma', 'Delta']

TEMPLES = ['Heart', 'Mind', 'Body', 'Soul']


def can_merge(label1: str, label2: str) -> bool:
    """
    Check if two concepts are safe to merge.
    Prevents merging concepts with different protected terms.
    
    Args:
        label1: First concept label
        label2: Second concept label
        
    Returns:
        True if safe to merge, False otherwise
        
    Examples:
        can_merge("Si Inferior", "Ne Inferior") -> False (different functions)
        can_merge("Hero Function", "Inferior Function") -> False (different positions)
        can_merge("Shadow Integration", "Shadow Work") -> True (no conflicts)
    """
    # Extract cognitive functions from both labels
    funcs1 = [f for f in COGNITIVE_FUNCTIONS if f in label1]
    funcs2 = [f for f in COGNITIVE_FUNCTIONS if f in label2]
    
    # If both have functions, they must match
    if funcs1 and funcs2 and funcs1 != funcs2:
        return False
    
    # Extract function positions
    pos1 = [p for p in FUNCTION_POSITIONS if p in label1]
    pos2 = [p for p in FUNCTION_POSITIONS if p in label2]
    
    # If both have positions, they must match
    if pos1 and pos2 and pos1 != pos2:
        return False
    
    # Extract MBTI types
    types1 = [t for t in MBTI_TYPES if t in label1]
    types2 = [t for t in MBTI_TYPES if t in label2]
    
    # If both have types, they must match
    if types1 and types2 and types1 != types2:
        return False
    
    # Extract quadras
    quad1 = [q for q in QUADRAS if q in label1]
    quad2 = [q for q in QUADRAS if q in label2]
    
    # If both have quadras, they must match
    if quad1 and quad2 and quad1 != quad2:
        return False
    
    # Extract temples
    temp1 = [t for t in TEMPLES if t in label1]
    temp2 = [t for t in TEMPLES if t in label2]
    
    # If both have temples, they must match
    if temp1 and temp2 and temp1 != temp2:
        return False
    
    return True


def preview_merges(similarity_threshold: float = 0.85) -> Dict:
    """
    Preview what would be merged without actually merging.
    
    Args:
        similarity_threshold: Minimum similarity (0.0-1.0) to consider concepts similar
        
    Returns:
        Preview dictionary with merge groups and statistics
    """
    print("=" * 80)
    print("📋 MERGE PREVIEW")
    print("=" * 80)
    print(f"🎯 Similarity threshold: {similarity_threshold}")
    print()
    
    manager = KnowledgeGraphManager()
    graph = manager.load_graph()
    
    nodes = graph['nodes']
    print(f"📊 Current concepts: {len(nodes)}")
    print()
    
    # Find merge groups
    merged_groups = []
    processed = set()
    
    for i, node in enumerate(nodes):
        if node['id'] in processed:
            continue
        
        # Find all similar nodes
        similar = [node]
        for j, other_node in enumerate(nodes):
            if i != j and other_node['id'] not in processed:
                # Check if safe to merge (protected terms)
                if not can_merge(node['label'], other_node['label']):
                    continue
                
                similarity = fuzzy_match_label(node['label'], other_node['label'])
                if similarity >= similarity_threshold:
                    similar.append(other_node)
                    processed.add(other_node['id'])
        
        if len(similar) > 1:
            merged_groups.append(similar)
        
        processed.add(node['id'])
    
    # Display preview
    print(f"🔍 Found {len(merged_groups)} merge groups")
    print()
    
    if merged_groups:
        print("Sample merges (first 10):")
        print("-" * 80)
        for i, group in enumerate(merged_groups[:10]):
            canonical = max(group, key=lambda n: n.get('frequency', 1))
            others = [n['label'] for n in group if n['id'] != canonical['id']]
            print(f"{i+1}. {canonical['label']} (freq: {canonical.get('frequency', 1)})")
            print(f"   ← merging: {', '.join(others)}")
            print()
    
    # Calculate statistics
    concepts_to_remove = sum(len(group) - 1 for group in merged_groups)
    final_concept_count = len(nodes) - concepts_to_remove
    
    print("=" * 80)
    print("📊 MERGE STATISTICS")
    print("=" * 80)
    print(f"Current concepts:   {len(nodes)}")
    print(f"Concepts to remove: {concepts_to_remove}")
    print(f"Final concepts:     {final_concept_count}")
    print(f"Reduction:          {(concepts_to_remove / len(nodes) * 100):.1f}%")
    print("=" * 80)
    
    return {
        "current_concepts": len(nodes),
        "merge_groups": len(merged_groups),
        "concepts_to_remove": concepts_to_remove,
        "final_concepts": final_concept_count,
        "reduction_percentage": (concepts_to_remove / len(nodes) * 100)
    }


def merge_similar_concepts(similarity_threshold: float = 0.85, create_backup: bool = True) -> Dict:
    """
    Merge similar concepts in the knowledge graph.
    
    Args:
        similarity_threshold: Minimum similarity (0.0-1.0) to consider concepts similar
        create_backup: Whether to create backup before merging
        
    Returns:
        Updated graph metadata with merge statistics
    """
    print("=" * 80)
    print("🔧 CONCEPT MERGER")
    print("=" * 80)
    print()
    
    manager = KnowledgeGraphManager()
    graph = manager.load_graph()
    
    # Backup before merge
    if create_backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path("data") / f"knowledge-graph-backup-{timestamp}.json"
        backup_path.parent.mkdir(exist_ok=True)
        
        with open(backup_path, 'w') as f:
            json.dump(graph, f, indent=2)
        
        print(f"💾 Backup created: {backup_path}")
        print()
    
    initial_node_count = len(graph['nodes'])
    initial_edge_count = len(graph['edges'])
    
    print(f"📊 Starting with {initial_node_count} concepts, {initial_edge_count} relationships")
    print()
    
    # 1. Group similar concepts
    print("🔍 Finding similar concepts...")
    merged_groups = []
    processed = set()
    
    for i, node in enumerate(graph['nodes']):
        if node['id'] in processed:
            continue
        
        # Find all similar nodes
        similar = [node]
        for j, other_node in enumerate(graph['nodes']):
            if i != j and other_node['id'] not in processed:
                # Check if safe to merge (protected terms)
                if not can_merge(node['label'], other_node['label']):
                    continue
                
                similarity = fuzzy_match_label(node['label'], other_node['label'])
                if similarity >= similarity_threshold:
                    similar.append(other_node)
                    processed.add(other_node['id'])
        
        if len(similar) > 1:
            merged_groups.append(similar)
            labels = [n['label'] for n in similar]
            print(f"🔗 Merging {len(similar)} concepts: {labels}")
        
        processed.add(node['id'])
    
    print(f"\n✅ Found {len(merged_groups)} merge groups")
    print()
    
    # Track merges for report
    merge_report_groups = []
    
    # 2. Merge each group
    print("🔀 Merging concepts...")
    for group in merged_groups:
        # Use most frequent label as canonical
        canonical = max(group, key=lambda n: n.get('frequency', 1))
        
        # Combine source documents
        all_docs = set()
        for node in group:
            all_docs.update(node.get('source_documents', []))
        
        # Sum frequencies
        total_frequency = sum(n.get('frequency', 1) for n in group)
        
        # Keep longest/best definition
        best_definition = max(
            (n.get('definition', '') for n in group),
            key=len,
            default=''
        )
        
        # Update canonical node
        canonical['source_documents'] = list(all_docs)
        canonical['frequency'] = total_frequency
        canonical['definition'] = best_definition
        canonical['merged_from'] = [n['label'] for n in group if n['id'] != canonical['id']]
        
        # Track for report
        merge_report_groups.append({
            "canonical": canonical['label'],
            "merged": [n['label'] for n in group if n['id'] != canonical['id']],
            "combined_frequency": total_frequency
        })
        
        # Remove other nodes from graph
        ids_to_remove = {node['id'] for node in group if node['id'] != canonical['id']}
        graph['nodes'] = [n for n in graph['nodes'] if n['id'] not in ids_to_remove]
        
        # Update all edges that reference merged nodes
        for edge in graph['edges']:
            for node in group:
                if node['id'] != canonical['id']:
                    if edge['source'] == node['id']:
                        edge['source'] = canonical['id']
                    if edge['target'] == node['id']:
                        edge['target'] = canonical['id']
    
    print(f"✅ Merged {len(merged_groups)} concept groups")
    print()
    
    # 3. Remove duplicate edges (same source+target+type)
    print("🔀 Removing duplicate edges...")
    unique_edges = []
    seen = set()
    
    for edge in graph['edges']:
        key = (edge['source'], edge['target'], edge['relationship_type'])
        if key not in seen:
            unique_edges.append(edge)
            seen.add(key)
        else:
            # Merge evidence into existing edge
            existing = next(e for e in unique_edges if 
                          e['source'] == edge['source'] and 
                          e['target'] == edge['target'] and
                          e['relationship_type'] == edge['relationship_type'])
            existing['strength'] = existing.get('strength', 1) + edge.get('strength', 1)
            if 'evidence_samples' in existing and 'evidence_samples' in edge:
                existing['evidence_samples'].extend(edge['evidence_samples'])
    
    edges_before_dedup = len(graph['edges'])
    graph['edges'] = unique_edges
    print(f"✅ Removed {edges_before_dedup - len(unique_edges)} duplicate edges")
    print()
    
    # 4. Remove self-referencing edges
    print("🔀 Removing self-referencing edges...")
    edges_before_self_ref = len(graph['edges'])
    graph['edges'] = [e for e in graph['edges'] if e['source'] != e['target']]
    print(f"✅ Removed {edges_before_self_ref - len(graph['edges'])} self-referencing edges")
    print()
    
    # 5. Quality checks
    print("✅ Running quality checks...")
    
    # Check for orphaned edges
    node_ids = {n['id'] for n in graph['nodes']}
    orphaned_edges = [e for e in graph['edges'] 
                      if e['source'] not in node_ids or e['target'] not in node_ids]
    
    if orphaned_edges:
        print(f"⚠️  Found {len(orphaned_edges)} orphaned edges - removing")
        graph['edges'] = [e for e in graph['edges'] 
                         if e['source'] in node_ids and e['target'] in node_ids]
    else:
        print("✅ No orphaned edges found")
    
    print()
    
    # 6. Update metadata
    graph['metadata']['total_concepts'] = len(graph['nodes'])
    graph['metadata']['total_relationships'] = len(graph['edges'])
    graph['metadata']['last_merge'] = datetime.now().isoformat()
    graph['metadata']['merge_threshold'] = similarity_threshold
    
    # 7. Save cleaned graph
    manager.save_graph(graph)
    
    # 8. Generate merge report
    merge_report = {
        "timestamp": datetime.now().isoformat(),
        "threshold": similarity_threshold,
        "before": {
            "concepts": initial_node_count,
            "relationships": initial_edge_count
        },
        "after": {
            "concepts": len(graph['nodes']),
            "relationships": len(graph['edges'])
        },
        "merged_groups": merge_report_groups,
        "reduction_percentage": ((initial_node_count - len(graph['nodes'])) / initial_node_count * 100)
    }
    
    report_path = Path("data") / "merge-report.json"
    with open(report_path, 'w') as f:
        json.dump(merge_report, f, indent=2)
    
    print("=" * 80)
    print("✅ MERGE COMPLETE!")
    print("=" * 80)
    print(f"📉 Concepts: {initial_node_count} → {len(graph['nodes'])}")
    print(f"🔗 Relationships: {initial_edge_count} → {len(graph['edges'])}")
    print(f"📊 Reduction: {initial_node_count - len(graph['nodes'])} concepts merged")
    print(f"📄 Report saved to: {report_path}")
    print("=" * 80)
    
    return graph['metadata']


def test_threshold(threshold: float) -> Dict:
    """
    Test a similarity threshold without saving.
    Shows how many merges would occur at this threshold.
    
    Args:
        threshold: Similarity threshold to test
        
    Returns:
        Statistics dictionary
    """
    return preview_merges(threshold)
