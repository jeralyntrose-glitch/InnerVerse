"""
Knowledge Graph Manager
Handles CRUD operations for the knowledge graph stored in JSON format.
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
import re


class KnowledgeGraphManager:
    """
    Manages a knowledge graph stored as JSON file.
    Provides methods for adding nodes, edges, deduplication, and querying.
    """
    
    def __init__(self, file_path: str = "data/knowledge-graph.json"):
        self.file_path = file_path
        self.lock = threading.Lock()  # Thread-safe file operations
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create the file with initial structure if it doesn't exist."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            initial_graph = {
                "version": "1.0",
                "last_updated": None,
                "nodes": [],
                "edges": [],
                "metadata": {
                    "total_documents_processed": 0,
                    "total_concepts": 0,
                    "total_relationships": 0
                }
            }
            with open(self.file_path, 'w') as f:
                json.dump(initial_graph, f, indent=2)
    
    def load_graph(self) -> Dict[str, Any]:
        """
        Load the knowledge graph from JSON file.
        Thread-safe with file locking.
        
        Returns:
            Dict containing nodes, edges, and metadata
        """
        with self.lock:
            try:
                with open(self.file_path, 'r') as f:
                    graph = json.load(f)
                return graph
            except FileNotFoundError:
                self._ensure_file_exists()
                return self.load_graph()
            except json.JSONDecodeError as e:
                print(f"❌ Error reading knowledge graph: {e}")
                # Attempt to recover with empty graph
                return {
                    "version": "1.0",
                    "last_updated": None,
                    "nodes": [],
                    "edges": [],
                    "metadata": {
                        "total_documents_processed": 0,
                        "total_concepts": 0,
                        "total_relationships": 0
                    }
                }
    
    def save_graph(self, graph: Dict[str, Any]) -> bool:
        """
        Save the knowledge graph to JSON file.
        Thread-safe with file locking.
        
        Args:
            graph: Graph object to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            try:
                # Update timestamp
                graph["last_updated"] = datetime.utcnow().isoformat()
                
                # Update metadata counts
                graph["metadata"]["total_concepts"] = len(graph["nodes"])
                graph["metadata"]["total_relationships"] = len(graph["edges"])
                
                # Write to file with pretty formatting
                with open(self.file_path, 'w') as f:
                    json.dump(graph, f, indent=2, ensure_ascii=False)
                
                return True
            except Exception as e:
                print(f"❌ Error saving knowledge graph: {e}")
                return False
    
    def generate_node_id(self, label: str) -> str:
        """
        Generate a consistent ID from a label.
        
        Args:
            label: Node label (e.g., "Shadow Integration")
            
        Returns:
            str: Snake-case ID (e.g., "shadow_integration")
        """
        # Convert to lowercase, replace spaces/special chars with underscores
        node_id = re.sub(r'[^a-z0-9]+', '_', label.lower())
        # Remove leading/trailing underscores
        node_id = node_id.strip('_')
        return node_id
    
    def fuzzy_match_label(self, label1: str, label2: str) -> float:
        """
        Calculate similarity between two labels using SequenceMatcher.
        
        Args:
            label1: First label
            label2: Second label
            
        Returns:
            float: Similarity score between 0 and 1
        """
        return SequenceMatcher(None, label1.lower(), label2.lower()).ratio()
    
    def find_similar_nodes(self, label: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Find nodes with labels similar to the given label.
        Used for deduplication.
        
        Args:
            label: Label to match
            threshold: Minimum similarity score (default: 0.8)
            
        Returns:
            List of similar nodes with similarity scores
        """
        graph = self.load_graph()
        similar_nodes = []
        
        for node in graph["nodes"]:
            similarity = self.fuzzy_match_label(label, node["label"])
            if similarity >= threshold:
                similar_nodes.append({
                    **node,
                    "similarity": similarity
                })
        
        # Sort by similarity (highest first)
        similar_nodes.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_nodes
    
    async def add_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a node to the knowledge graph.
        If a similar node exists, increment frequency and add source.
        
        Args:
            node_data: Dict with keys:
                - label (str): Node label/name
                - type (str): Node type (e.g., "concept", "process", "person")
                - category (str): Node category (e.g., "foundational", "advanced")
                - definition (str): Definition or description
                - properties (dict): Additional properties
                - source_documents (list): List of document IDs this came from
                - source_doc (str): Single document ID (backwards compatibility)
                
        Returns:
            Dict: The node (new or updated)
        """
        graph = self.load_graph()
        label = node_data.get("label", "")
        
        # Handle both source_documents (plural) and source_doc (singular) for backwards compatibility
        source_docs = node_data.get("source_documents") or []
        if node_data.get("source_doc"):
            source_docs = [node_data.get("source_doc")]
        
        # Check for similar existing nodes
        similar_nodes = self.find_similar_nodes(label, threshold=0.85)
        
        if similar_nodes:
            # Update existing node
            existing_node = similar_nodes[0]
            node_id = existing_node["id"]
            
            # Find and update the node in the graph
            for node in graph["nodes"]:
                if node["id"] == node_id:
                    # Increment frequency
                    node["frequency"] = node.get("frequency", 1) + 1
                    
                    # Add source documents if not already present
                    for doc in source_docs:
                        if doc and doc not in node.get("sources", []):
                            node.setdefault("sources", []).append(doc)
                    
                    # Update definition if provided
                    if node_data.get("definition"):
                        node["definition"] = node_data.get("definition")
                    
                    # Update category if provided
                    if node_data.get("category"):
                        node["category"] = node_data.get("category")
                    
                    # Update timestamp
                    node["last_updated"] = datetime.utcnow().isoformat()
                    
                    self.save_graph(graph)
                    print(f"✅ Updated existing node: {label} (frequency: {node['frequency']})")
                    return node
        
        # Create new node
        node_id = self.generate_node_id(label)
        
        # Handle ID conflicts
        existing_ids = {n["id"] for n in graph["nodes"]}
        if node_id in existing_ids:
            counter = 1
            while f"{node_id}_{counter}" in existing_ids:
                counter += 1
            node_id = f"{node_id}_{counter}"
        
        new_node = {
            "id": node_id,
            "label": label,
            "type": node_data.get("type", "concept"),
            "category": node_data.get("category", ""),
            "definition": node_data.get("definition", ""),
            "properties": node_data.get("properties", {}),
            "frequency": 1,
            "sources": source_docs,
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        graph["nodes"].append(new_node)
        self.save_graph(graph)
        print(f"✅ Created new node: {label} (ID: {node_id})")
        return new_node
    
    async def add_edge(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an edge (relationship) to the knowledge graph.
        If the same edge exists, increment strength and add evidence.
        
        Args:
            edge_data: Dict with keys:
                - source (str): Source node ID
                - target (str): Target node ID
                - relationship_type (str): Relationship type (e.g., "relates_to", "requires_understanding")
                - type (str): Alternative to relationship_type (backwards compatibility)
                - properties (dict): Additional properties
                - evidence_samples (list): List of evidence strings
                - evidence (str): Single evidence string (backwards compatibility)
                
        Returns:
            Dict: The edge (new or updated)
        """
        graph = self.load_graph()
        source = edge_data.get("source")
        target = edge_data.get("target")
        
        # Handle both relationship_type and type for backwards compatibility
        edge_type = edge_data.get("relationship_type") or edge_data.get("type", "relates_to")
        
        # Handle both evidence_samples (plural) and evidence (singular) for backwards compatibility
        evidence_samples = edge_data.get("evidence_samples") or []
        if edge_data.get("evidence"):
            evidence_samples = [edge_data.get("evidence")]
        
        # Check if edge already exists (same source, target, and type)
        for edge in graph["edges"]:
            if (edge["source"] == source and 
                edge["target"] == target and 
                edge["type"] == edge_type):
                
                # Update existing edge
                edge["strength"] = edge.get("strength", 1) + 1
                
                # Add evidence samples
                for evidence in evidence_samples:
                    if evidence:
                        edge.setdefault("evidence", []).append({
                            "text": evidence,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                edge["last_updated"] = datetime.utcnow().isoformat()
                
                self.save_graph(graph)
                print(f"✅ Updated existing edge: {source} -> {target} (strength: {edge['strength']})")
                return edge
        
        # Create new edge
        edge_id = f"{source}__{edge_type}__{target}"
        
        # Build evidence array
        evidence_array = []
        for evidence in evidence_samples:
            if evidence:
                evidence_array.append({
                    "text": evidence,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        new_edge = {
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
            "properties": edge_data.get("properties", {}),
            "strength": 1,
            "evidence": evidence_array,
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        graph["edges"].append(new_edge)
        self.save_graph(graph)
        print(f"✅ Created new edge: {source} -> {target} (type: {edge_type})")
        return new_edge
    
    async def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single node by its ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Dict: Node data or None if not found
        """
        graph = self.load_graph()
        for node in graph["nodes"]:
            if node["id"] == node_id:
                return node
        return None
    
    async def find_node_by_label(self, label: str, threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """
        Find a node by its label using fuzzy matching.
        
        Args:
            label: Label to search for
            threshold: Similarity threshold (0.85 = 85% match)
            
        Returns:
            Dict: Best matching node or None if no good match found
        """
        similar_nodes = self.find_similar_nodes(label, threshold)
        
        if similar_nodes:
            return similar_nodes[0]
        return None
    
    async def get_connected_nodes(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Get all nodes connected to the given node.
        
        Args:
            node_id: Node ID
            
        Returns:
            List of connected nodes with relationship info
        """
        graph = self.load_graph()
        connected = []
        
        # Find all edges involving this node
        for edge in graph["edges"]:
            if edge["source"] == node_id:
                # Outgoing edge
                target_node = await self.get_node_by_id(edge["target"])
                if target_node:
                    connected.append({
                        "node": target_node,
                        "relationship": edge["type"],
                        "direction": "outgoing",
                        "strength": edge.get("strength", 1)
                    })
            elif edge["target"] == node_id:
                # Incoming edge
                source_node = await self.get_node_by_id(edge["source"])
                if source_node:
                    connected.append({
                        "node": source_node,
                        "relationship": edge["type"],
                        "direction": "incoming",
                        "strength": edge.get("strength", 1)
                    })
        
        return connected
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.
        
        Returns:
            Dict: Statistics including node count, edge count, etc.
        """
        graph = self.load_graph()
        
        # Count node types
        node_types = {}
        for node in graph["nodes"]:
            node_type = node.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # Count edge types
        edge_types = {}
        for edge in graph["edges"]:
            edge_type = edge.get("type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        return {
            "total_nodes": len(graph["nodes"]),
            "total_edges": len(graph["edges"]),
            "node_types": node_types,
            "edge_types": edge_types,
            "last_updated": graph.get("last_updated"),
            "documents_processed": graph["metadata"].get("total_documents_processed", 0)
        }
    
    def validate_graph_structure(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate graph integrity and detect issues.
        
        Args:
            graph: Graph object to validate
            
        Returns:
            Dict with validation results and issues found
        """
        issues = []
        
        # Check for unique IDs
        node_ids = [n["id"] for n in graph["nodes"]]
        if len(node_ids) != len(set(node_ids)):
            issues.append("Duplicate node IDs found")
        
        edge_ids = [e["id"] for e in graph["edges"]]
        if len(edge_ids) != len(set(edge_ids)):
            issues.append("Duplicate edge IDs found")
        
        # Check for orphaned edges (edges referencing non-existent nodes)
        valid_node_ids = set(node_ids)
        orphaned_edges = []
        
        for edge in graph["edges"]:
            if edge["source"] not in valid_node_ids:
                orphaned_edges.append(f"Edge {edge['id']} has invalid source: {edge['source']}")
            if edge["target"] not in valid_node_ids:
                orphaned_edges.append(f"Edge {edge['id']} has invalid target: {edge['target']}")
        
        if orphaned_edges:
            issues.extend(orphaned_edges)
        
        # Check required fields
        for node in graph["nodes"]:
            if "id" not in node or "label" not in node:
                issues.append(f"Node missing required fields: {node}")
        
        for edge in graph["edges"]:
            if "id" not in edge or "source" not in edge or "target" not in edge:
                issues.append(f"Edge missing required fields: {edge}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_nodes": len(graph["nodes"]),
            "total_edges": len(graph["edges"])
        }
    
    def get_concept(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single concept (node) by ID.
        Required for AI generation.
        
        Args:
            concept_id: Concept/node ID
            
        Returns:
            Dict with concept data including:
            - id: Concept ID
            - name: Concept label/name
            - definition: Concept definition (if available)
            - category: Concept category/type
            - related_concepts: List of related concept edges
            
            Returns None if not found
        """
        graph = self.load_graph()
        
        # Find the node
        node = None
        for n in graph["nodes"]:
            if n["id"] == concept_id:
                node = n
                break
        
        if not node:
            return None
        
        # Find related edges
        related_edges = []
        for edge in graph["edges"]:
            if edge["source"] == concept_id:
                related_edges.append({
                    'target_id': edge["target"],
                    'relationship_type': edge.get("type", "related"),
                    'label': edge.get("label", "")
                })
            elif edge["target"] == concept_id:
                related_edges.append({
                    'target_id': edge["source"],
                    'relationship_type': edge.get("type", "related"),
                    'label': edge.get("label", ""),
                    'reverse': True
                })
        
        return {
            'id': node["id"],
            'name': node.get("label", ""),
            'definition': node.get("definition", ""),
            'category': node.get("type", ""),
            'metadata': node.get("metadata", {}),
            'related_concepts': related_edges
        }
    
    def search_concepts(self, query: str, top_k: int = 30) -> List[Dict[str, Any]]:
        """
        Search concepts by semantic similarity.
        Required for AI generation.
        
        Uses simple text-based matching on labels and definitions.
        For production, this could be enhanced with Pinecone vector search.
        
        Args:
            query: Search query
            top_k: Maximum number of results to return
            
        Returns:
            List of concept dicts sorted by relevance
        """
        graph = self.load_graph()
        query_lower = query.lower()
        
        # Score each node based on text similarity
        scored_nodes = []
        for node in graph["nodes"]:
            score = 0.0
            label = node.get("label", "").lower()
            definition = node.get("definition", "").lower()
            
            # Exact label match gets highest score
            if query_lower == label:
                score = 10.0
            # Label contains query
            elif query_lower in label:
                score = 5.0
            # Query contains label
            elif label in query_lower:
                score = 4.0
            # Definition contains query
            elif query_lower in definition:
                score = 3.0
            # Partial match using SequenceMatcher
            else:
                label_similarity = SequenceMatcher(None, query_lower, label).ratio()
                def_similarity = SequenceMatcher(None, query_lower, definition).ratio()
                score = max(label_similarity, def_similarity) * 2.0
            
            if score > 0.1:
                # Find related edges for this node
                related_edges = []
                for edge in graph["edges"]:
                    if edge["source"] == node["id"]:
                        related_edges.append({
                            'target_id': edge["target"],
                            'relationship_type': edge.get("type", "related"),
                            'label': edge.get("label", "")
                        })
                
                scored_nodes.append({
                    'id': node["id"],
                    'name': node.get("label", ""),
                    'definition': node.get("definition", ""),
                    'category': node.get("type", ""),
                    'metadata': node.get("metadata", {}),
                    'related_concepts': related_edges,
                    'relevance_score': score
                })
        
        # Sort by score descending
        scored_nodes.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Return top_k results
        return scored_nodes[:top_k]
