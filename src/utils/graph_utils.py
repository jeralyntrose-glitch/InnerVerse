"""
Utility functions for Knowledge Graph operations
"""

from difflib import SequenceMatcher


def fuzzy_match_label(label1: str, label2: str) -> float:
    """
    Calculate similarity between two concept labels using fuzzy string matching.
    
    Args:
        label1: First concept label
        label2: Second concept label
        
    Returns:
        Similarity score between 0.0 and 1.0 (1.0 = identical)
        
    Examples:
        fuzzy_match_label("Shadow Integration", "Shadow Work") -> 0.58
        fuzzy_match_label("Type Grid", "Type Grid") -> 1.0
        fuzzy_match_label("ENTP", "INTP") -> 0.75
    """
    if not label1 or not label2:
        return 0.0
    
    # Normalize: lowercase and strip whitespace
    label1_norm = label1.lower().strip()
    label2_norm = label2.lower().strip()
    
    # Exact match after normalization
    if label1_norm == label2_norm:
        return 1.0
    
    # Use SequenceMatcher for fuzzy comparison
    return SequenceMatcher(None, label1_norm, label2_norm).ratio()


def normalize_concept_id(label: str) -> str:
    """
    Convert a concept label to a normalized ID.
    
    Args:
        label: Concept label
        
    Returns:
        Normalized ID (lowercase, underscores)
        
    Examples:
        normalize_concept_id("Shadow Integration") -> "shadow_integration"
        normalize_concept_id("Type Grid") -> "type_grid"
    """
    return label.lower().strip().replace(' ', '_').replace('-', '_')


def find_best_match(label: str, candidates: list, threshold: float = 0.85) -> tuple:
    """
    Find the best matching label from a list of candidates.
    
    Args:
        label: Label to match
        candidates: List of candidate labels
        threshold: Minimum similarity score (0.0-1.0)
        
    Returns:
        Tuple of (best_match, score) or (None, 0.0) if no match above threshold
    """
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        score = fuzzy_match_label(label, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate
    
    if best_score >= threshold:
        return (best_match, best_score)
    else:
        return (None, 0.0)
