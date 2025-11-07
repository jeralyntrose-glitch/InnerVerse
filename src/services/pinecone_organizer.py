"""
Pinecone Result Organizer
Organizes Pinecone search results by metadata for structured AI responses
"""

from typing import List, Dict, Any


def organize_results_by_metadata(matches: List[Any], organize_by: str = 'primary_category') -> Dict[str, List[Dict[str, Any]]]:
    """
    Organize Pinecone search results by metadata field.
    
    Args:
        matches: Pinecone query matches (either list of Match objects or dicts)
        organize_by: Metadata field to group by ('primary_category', 'temple', 'difficulty', etc.)
        
    Returns:
        Dict organized by metadata values
        
    Example:
        {
            'cognitive_functions': [
                {'text': '...', 'metadata': {...}, 'score': 0.85},
                {'text': '...', 'metadata': {...}, 'score': 0.82}
            ],
            'octagram': [...]
        }
    """
    organized = {}
    
    for match in matches:
        # Handle both Match objects and dict responses
        if hasattr(match, 'metadata'):
            metadata = match.metadata
            score = match.score
        else:
            metadata = match.get('metadata', {})
            score = match.get('score', 0.0)
        
        # Get grouping key
        group_key = metadata.get(organize_by, 'other')
        
        # Handle list values (e.g., topics, types_discussed)
        if isinstance(group_key, list):
            if group_key:
                group_key = group_key[0]  # Use first item
            else:
                group_key = 'none'
        
        # Initialize group if needed
        if group_key not in organized:
            organized[group_key] = []
        
        # Add result to group
        organized[group_key].append({
            'text': metadata.get('text', ''),
            'metadata': metadata,
            'score': score
        })
    
    # Sort each group by score
    for group_key in organized:
        organized[group_key].sort(key=lambda x: x['score'], reverse=True)
    
    return organized


def extract_all_metadata(matches: List[Any]) -> List[Dict[str, Any]]:
    """
    Extract complete metadata from Pinecone matches.
    
    Includes all 10 enriched fields:
    - content_type
    - difficulty
    - primary_category
    - types_discussed
    - functions_covered
    - relationship_type
    - quadra
    - temple
    - topics
    - use_case
    
    Args:
        matches: Pinecone query matches
        
    Returns:
        List of dicts with full metadata
    """
    results = []
    
    for match in matches:
        # Handle both Match objects and dict responses
        if hasattr(match, 'metadata'):
            metadata = match.metadata
            score = match.score
            match_id = match.id
        else:
            metadata = match.get('metadata', {})
            score = match.get('score', 0.0)
            match_id = match.get('id', '')
        
        results.append({
            'id': match_id,
            'score': score,
            'text': metadata.get('text', ''),
            
            # Core metadata
            'filename': metadata.get('filename', 'Unknown'),
            'doc_id': metadata.get('doc_id', ''),
            'chunk_index': metadata.get('chunk_index', 0),
            
            # Enriched metadata (10 fields)
            'content_type': metadata.get('content_type', 'unknown'),
            'difficulty': metadata.get('difficulty', 'unknown'),
            'primary_category': metadata.get('primary_category', 'unknown'),
            'types_discussed': metadata.get('types_discussed', []),
            'functions_covered': metadata.get('functions_covered', []),
            'relationship_type': metadata.get('relationship_type', 'none'),
            'quadra': metadata.get('quadra', 'none'),
            'temple': metadata.get('temple', 'none'),
            'topics': metadata.get('topics', []),
            'use_case': metadata.get('use_case', 'unknown'),
            
            # Additional metadata
            'tags': metadata.get('tags', []),
            'season': metadata.get('season', ''),
            'types_mentioned': metadata.get('types_mentioned', ''),
        })
    
    return results


def format_organized_context(organized: Dict[str, List[Dict[str, Any]]], max_chunks_per_group: int = 3) -> str:
    """
    Format organized results into a structured context string for AI.
    
    Args:
        organized: Organized results from organize_results_by_metadata()
        max_chunks_per_group: Max chunks to include per category
        
    Returns:
        Formatted string with clear section headers
    """
    sections = []
    
    # Define friendly category names
    category_names = {
        'cognitive_functions': '🧠 Cognitive Functions',
        'typing_methodology': '🔍 Typing Methodology',
        'octagram': '⭐ Octagram & Variants',
        'type_development': '📈 Type Development',
        'relationships': '💕 Relationships & Compatibility',
        'four_sides': '🎭 Four Sides of the Mind',
        'temple_theory': '🏛️ Temple Theory',
        'interaction_styles': '🗣️ Interaction Styles',
        'other': '📚 General MBTI Content'
    }
    
    for category, chunks in organized.items():
        # Get friendly name
        section_name = category_names.get(category, f"📖 {category.replace('_', ' ').title()}")
        
        # Limit chunks per category
        top_chunks = chunks[:max_chunks_per_group]
        
        # Format section
        section_text = f"\n{'='*60}\n{section_name}\n{'='*60}\n"
        
        for i, chunk in enumerate(top_chunks, 1):
            metadata = chunk['metadata']
            
            # Build metadata header
            meta_info = []
            if metadata.get('filename'):
                meta_info.append(f"Source: {metadata['filename'][:60]}")
            if metadata.get('difficulty') and metadata['difficulty'] != 'unknown':
                meta_info.append(f"Level: {metadata['difficulty'].title()}")
            if metadata.get('types_discussed'):
                types = metadata['types_discussed']
                if types:
                    meta_info.append(f"Types: {', '.join(types[:3])}")
            
            section_text += f"\n[Chunk {i}] {' | '.join(meta_info)}\n"
            section_text += f"{chunk['text']}\n"
        
        sections.append(section_text)
    
    return "\n".join(sections)


def get_metadata_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics about metadata in results.
    
    Args:
        results: Results from extract_all_metadata()
        
    Returns:
        Dict with statistics about content types, difficulties, categories, etc.
    """
    summary = {
        'total_chunks': len(results),
        'content_types': {},
        'difficulties': {},
        'categories': {},
        'temples': {},
        'types_discussed': set(),
        'functions_covered': set(),
    }
    
    for result in results:
        # Count content types
        content_type = result.get('content_type', 'unknown')
        summary['content_types'][content_type] = summary['content_types'].get(content_type, 0) + 1
        
        # Count difficulties
        difficulty = result.get('difficulty', 'unknown')
        summary['difficulties'][difficulty] = summary['difficulties'].get(difficulty, 0) + 1
        
        # Count categories
        category = result.get('primary_category', 'unknown')
        summary['categories'][category] = summary['categories'].get(category, 0) + 1
        
        # Count temples
        temple = result.get('temple', 'none')
        if temple != 'none':
            summary['temples'][temple] = summary['temples'].get(temple, 0) + 1
        
        # Collect types and functions
        if result.get('types_discussed'):
            summary['types_discussed'].update(result['types_discussed'])
        if result.get('functions_covered'):
            summary['functions_covered'].update(result['functions_covered'])
    
    # Convert sets to lists for JSON serialization
    summary['types_discussed'] = sorted(list(summary['types_discussed']))
    summary['functions_covered'] = sorted(list(summary['functions_covered']))
    
    return summary
