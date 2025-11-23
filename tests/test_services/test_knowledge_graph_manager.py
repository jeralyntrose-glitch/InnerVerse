"""
Tests for Knowledge Graph Manager
"""
import pytest
import json
import tempfile
import os
from pathlib import Path

from src.services.knowledge_graph_manager import KnowledgeGraphManager


@pytest.fixture
def temp_graph_file():
    """Create a temporary graph file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
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
        json.dump(initial_graph, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_kg_manager_initialization(temp_graph_file):
    """Test KnowledgeGraphManager initialization"""
    kg = KnowledgeGraphManager(temp_graph_file)
    assert kg.file_path == temp_graph_file
    assert os.path.exists(temp_graph_file)


def test_kg_manager_creates_file_if_missing():
    """Test that KG manager creates file if it doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_path = os.path.join(tmpdir, "test_graph.json")
        assert not os.path.exists(graph_path)
        
        kg = KnowledgeGraphManager(graph_path)
        assert os.path.exists(graph_path)
        
        # Check file has correct structure
        with open(graph_path) as f:
            data = json.load(f)
        
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data


def test_load_graph(temp_graph_file):
    """Test loading knowledge graph"""
    kg = KnowledgeGraphManager(temp_graph_file)
    graph = kg.load_graph()
    
    assert "nodes" in graph
    assert "edges" in graph
    assert "metadata" in graph
    assert isinstance(graph["nodes"], list)
    assert isinstance(graph["edges"], list)


def test_load_graph_caching(temp_graph_file):
    """Test that load_graph uses caching"""
    kg = KnowledgeGraphManager(temp_graph_file)
    
    # First load
    graph1 = kg.load_graph()
    # Second load should use cache
    graph2 = kg.load_graph()
    
    # Should be the exact same object (cached)
    assert graph1 is graph2


def test_save_graph(temp_graph_file):
    """Test saving knowledge graph"""
    kg = KnowledgeGraphManager(temp_graph_file)
    graph = kg.load_graph()
    
    # Modify graph
    graph["nodes"].append({
        "id": "test_node",
        "label": "Test Node",
        "type": "concept"
    })
    
    # Save
    success = kg.save_graph(graph)
    assert success
    
    # Reload and verify
    kg._cache = None  # Clear cache
    reloaded = kg.load_graph()
    assert len(reloaded["nodes"]) == 1
    assert reloaded["nodes"][0]["id"] == "test_node"


def test_add_node(temp_graph_file):
    """Test adding a node to the graph"""
    kg = KnowledgeGraphManager(temp_graph_file)
    
    node_data = {
        "label": "Test Concept",
        "type": "concept",
        "description": "A test concept"
    }
    
    node_id = kg.add_node(node_data)
    assert node_id is not None
    
    # Verify node was added
    graph = kg.load_graph()
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["label"] == "Test Concept"


def test_get_node(temp_graph_file):
    """Test retrieving a node by ID"""
    kg = KnowledgeGraphManager(temp_graph_file)
    
    # Add a node
    node_data = {"label": "Test", "type": "concept"}
    node_id = kg.add_node(node_data)
    
    # Retrieve it
    node = kg.get_node(node_id)
    assert node is not None
    assert node["id"] == node_id
    assert node["label"] == "Test"


def test_get_nonexistent_node(temp_graph_file):
    """Test retrieving a node that doesn't exist"""
    kg = KnowledgeGraphManager(temp_graph_file)
    
    node = kg.get_node("nonexistent_id")
    assert node is None


def test_add_edge(temp_graph_file):
    """Test adding an edge between nodes"""
    kg = KnowledgeGraphManager(temp_graph_file)
    
    # Add two nodes
    node1_id = kg.add_node({"label": "Node 1", "type": "concept"})
    node2_id = kg.add_node({"label": "Node 2", "type": "concept"})
    
    # Add edge
    edge_data = {
        "relationship": "relates_to",
        "weight": 0.8
    }
    
    edge_id = kg.add_edge(node1_id, node2_id, edge_data)
    assert edge_id is not None
    
    # Verify edge was added
    graph = kg.load_graph()
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["source"] == node1_id
    assert graph["edges"][0]["target"] == node2_id


def test_search_nodes(temp_graph_file):
    """Test searching for nodes"""
    kg = KnowledgeGraphManager(temp_graph_file)
    
    # Add some nodes
    kg.add_node({"label": "Cognitive Functions", "type": "concept"})
    kg.add_node({"label": "Extraverted Thinking", "type": "function"})
    kg.add_node({"label": "INTJ Type", "type": "mbti_type"})
    
    # Search
    results = kg.search_nodes(query="cognitive")
    assert len(results) > 0
    assert any("Cognitive" in r["label"] for r in results)


def test_get_connected_nodes(temp_graph_file):
    """Test getting nodes connected to a specific node"""
    kg = KnowledgeGraphManager(temp_graph_file)
    
    # Create a small graph
    node1_id = kg.add_node({"label": "Center", "type": "concept"})
    node2_id = kg.add_node({"label": "Related 1", "type": "concept"})
    node3_id = kg.add_node({"label": "Related 2", "type": "concept"})
    
    kg.add_edge(node1_id, node2_id, {"relationship": "relates_to"})
    kg.add_edge(node1_id, node3_id, {"relationship": "relates_to"})
    
    # Get connected nodes
    connected = kg.get_connected_nodes(node1_id)
    assert len(connected) == 2
    assert any(n["label"] == "Related 1" for n in connected)
    assert any(n["label"] == "Related 2" for n in connected)

