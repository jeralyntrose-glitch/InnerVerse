"""
Manual Merge Helpers
For manually merging specific concepts that fuzzy matching might miss.
"""

import asyncio
from typing import List
from src.services.knowledge_graph_manager import KnowledgeGraphManager


def merge_specific_concepts(labels_to_merge: List[str], canonical_label: str) -> bool:
    """
    Manually merge a list of concept labels into one canonical label.
    
    Args:
        labels_to_merge: List of concept labels to merge (including canonical)
        canonical_label: The label to keep (must be in labels_to_merge)
        
    Returns:
        True if successful, False otherwise
        
    Example:
        await merge_specific_concepts(
            ["Shadow Work", "Shadow Integration", "Shadow Development"],
            "Shadow Integration"
        )
    """
    print("=" * 80)
    print("🔧 MANUAL CONCEPT MERGE")
    print("=" * 80)
    print()
    
    if canonical_label not in labels_to_merge:
        print(f"❌ Error: Canonical label '{canonical_label}' must be in labels_to_merge")
        return False
    
    manager = KnowledgeGraphManager()
    graph = manager.load_graph()
    
    # Find all nodes to merge
    nodes_to_merge = []
    for node in graph['nodes']:
        if node['label'] in labels_to_merge:
            nodes_to_merge.append(node)
    
    if len(nodes_to_merge) != len(labels_to_merge):
        found_labels = [n['label'] for n in nodes_to_merge]
        missing = set(labels_to_merge) - set(found_labels)
        print(f"⚠️  Warning: Could not find all labels. Missing: {missing}")
        if not nodes_to_merge:
            print("❌ No nodes found to merge")
            return False
    
    # Find canonical node
    canonical = None
    for node in nodes_to_merge:
        if node['label'] == canonical_label:
            canonical = node
            break
    
    if not canonical:
        print(f"❌ Error: Could not find canonical node '{canonical_label}'")
        return False
    
    print(f"📌 Canonical: {canonical['label']}")
    print(f"🔗 Merging: {[n['label'] for n in nodes_to_merge if n['id'] != canonical['id']]}")
    print()
    
    # Combine source documents
    all_docs = set()
    for node in nodes_to_merge:
        all_docs.update(node.get('source_documents', []))
    
    # Sum frequencies
    total_frequency = sum(n.get('frequency', 1) for n in nodes_to_merge)
    
    # Keep longest/best definition
    best_definition = max(
        (n.get('definition', '') for n in nodes_to_merge),
        key=len,
        default=''
    )
    
    # Update canonical node
    canonical['source_documents'] = list(all_docs)
    canonical['frequency'] = total_frequency
    canonical['definition'] = best_definition
    canonical['merged_from'] = [n['label'] for n in nodes_to_merge if n['id'] != canonical['id']]
    
    # Remove other nodes from graph
    ids_to_remove = {node['id'] for node in nodes_to_merge if node['id'] != canonical['id']}
    graph['nodes'] = [n for n in graph['nodes'] if n['id'] not in ids_to_remove]
    
    # Update all edges that reference merged nodes
    edges_updated = 0
    for edge in graph['edges']:
        for node in nodes_to_merge:
            if node['id'] != canonical['id']:
                if edge['source'] == node['id']:
                    edge['source'] = canonical['id']
                    edges_updated += 1
                if edge['target'] == node['id']:
                    edge['target'] = canonical['id']
                    edges_updated += 1
    
    # Remove duplicate edges
    unique_edges = []
    seen = set()
    duplicates_removed = 0
    
    for edge in graph['edges']:
        key = (edge['source'], edge['target'], edge['relationship_type'])
        if key not in seen:
            unique_edges.append(edge)
            seen.add(key)
        else:
            duplicates_removed += 1
            # Merge evidence into existing edge
            existing = next(e for e in unique_edges if 
                          e['source'] == edge['source'] and 
                          e['target'] == edge['target'] and
                          e['relationship_type'] == edge['relationship_type'])
            existing['strength'] = existing.get('strength', 1) + edge.get('strength', 1)
            if 'evidence_samples' in existing and 'evidence_samples' in edge:
                existing['evidence_samples'].extend(edge['evidence_samples'])
    
    graph['edges'] = unique_edges
    
    # Remove self-referencing edges
    edges_before = len(graph['edges'])
    graph['edges'] = [e for e in graph['edges'] if e['source'] != e['target']]
    self_refs_removed = edges_before - len(graph['edges'])
    
    # Update metadata
    graph['metadata']['total_concepts'] = len(graph['nodes'])
    graph['metadata']['total_relationships'] = len(graph['edges'])
    
    # Save
    manager.save_graph(graph)
    
    print("=" * 80)
    print("✅ MERGE COMPLETE!")
    print("=" * 80)
    print(f"📊 Merged {len(nodes_to_merge)} concepts into '{canonical_label}'")
    print(f"🔗 Updated {edges_updated} edge references")
    print(f"♻️  Removed {duplicates_removed} duplicate edges")
    print(f"♻️  Removed {self_refs_removed} self-referencing edges")
    print(f"📈 Final frequency: {total_frequency}")
    print("=" * 80)
    
    return True


def list_similar_concepts(label: str, threshold: float = 0.7) -> List[str]:
    """
    Find concepts similar to a given label.
    Helpful for identifying manual merge candidates.
    
    Args:
        label: Concept label to find similar concepts for
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        List of similar concept labels
    """
    from src.utils.graph_utils import fuzzy_match_label
    
    manager = KnowledgeGraphManager()
    graph = manager.load_graph()
    
    similar = []
    for node in graph['nodes']:
        if node['label'] != label:
            similarity = fuzzy_match_label(label, node['label'])
            if similarity >= threshold:
                similar.append({
                    'label': node['label'],
                    'similarity': similarity,
                    'frequency': node.get('frequency', 1)
                })
    
    # Sort by similarity descending
    similar.sort(key=lambda x: x['similarity'], reverse=True)
    
    print(f"🔍 Concepts similar to '{label}' (threshold: {threshold}):")
    print("-" * 80)
    for item in similar:
        print(f"  {item['label']} - similarity: {item['similarity']:.2f}, freq: {item['frequency']}")
    
    return [item['label'] for item in similar]
