"""
Pinecone Metadata Inspector
READ-ONLY script to inspect actual metadata values in the Pinecone index.

This script will:
1. Query a sample of documents from Pinecone
2. Extract all unique values for each metadata field
3. Determine field types (string vs array)
4. Generate a comprehensive report

NO MUTATIONS - Read-only inspection.
"""

import os
import json
from collections import defaultdict
from typing import Dict, List, Any, Set
from pinecone import Pinecone

# Initialize Pinecone client
def get_pinecone_client():
    """Initialize Pinecone client"""
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found in environment")
    
    pc = Pinecone(api_key=api_key)
    index_name = "mbti-knowledge-v2"
    return pc.Index(index_name)

def inspect_metadata(sample_size: int = 200) -> Dict[str, Any]:
    """
    Inspect Pinecone metadata by querying sample documents
    
    Args:
        sample_size: Number of documents to sample
    
    Returns:
        Report dictionary with field analysis
    """
    print(f"🔍 Inspecting Pinecone metadata (sample size: {sample_size})...")
    
    index = get_pinecone_client()
    
    # Get index stats
    stats = index.describe_index_stats()
    total_vectors = stats.get('total_vector_count', 0)
    print(f"📊 Total vectors in index: {total_vectors}")
    
    # Collect metadata from sample documents
    # Strategy: Use query with random vector to get diverse samples
    import random
    
    all_metadata = []
    batch_size = 50  # Query in batches
    batches = (sample_size + batch_size - 1) // batch_size
    
    print(f"📥 Fetching {sample_size} documents in {batches} batches...")
    
    for batch_num in range(batches):
        # Create a random query vector (3072 dimensions for text-embedding-3-large)
        random_vector = [random.random() for _ in range(3072)]
        
        # Query Pinecone
        results = index.query(
            vector=random_vector,
            top_k=min(batch_size, sample_size - len(all_metadata)),
            include_metadata=True
        )
        
        # Extract metadata
        for match in results.get('matches', []):
            if 'metadata' in match:
                all_metadata.append(match['metadata'])
        
        print(f"  Batch {batch_num + 1}/{batches}: {len(all_metadata)} documents collected")
    
    print(f"✅ Collected {len(all_metadata)} documents\n")
    
    # Analyze metadata fields
    field_analysis = analyze_fields(all_metadata)
    
    return {
        "total_vectors_in_index": total_vectors,
        "sample_size": len(all_metadata),
        "field_analysis": field_analysis,
        "sample_documents": all_metadata[:5]  # Include 5 sample docs for manual inspection
    }

def analyze_fields(metadata_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze metadata fields to determine types and unique values
    
    Args:
        metadata_list: List of metadata dictionaries
    
    Returns:
        Field analysis report
    """
    field_values = defaultdict(lambda: {"values": set(), "types": set(), "count": 0})
    
    for metadata in metadata_list:
        for field, value in metadata.items():
            field_info = field_values[field]
            field_info["count"] += 1
            
            # Determine type
            if isinstance(value, list):
                field_info["types"].add("array")
                # Add individual array values
                for item in value:
                    if item:  # Skip empty strings/None
                        field_info["values"].add(str(item))
            elif isinstance(value, (str, int, float, bool)):
                field_info["types"].add(type(value).__name__)
                if value:  # Skip empty strings
                    field_info["values"].add(str(value))
            else:
                field_info["types"].add(type(value).__name__)
    
    # Convert sets to lists for JSON serialization
    analysis = {}
    for field, info in field_values.items():
        # Limit unique values display to 50 for readability
        unique_values = sorted(list(info["values"]))
        
        analysis[field] = {
            "appears_in_n_documents": info["count"],
            "field_types": sorted(list(info["types"])),
            "unique_value_count": len(unique_values),
            "unique_values": unique_values[:50],  # Top 50 values
            "sample_values_truncated": len(unique_values) > 50
        }
    
    return analysis

def generate_report(report_data: Dict[str, Any], output_file: str = "pinecone_metadata_report.json"):
    """
    Generate and save metadata report
    
    Args:
        report_data: Report data dictionary
        output_file: Output file path
    """
    # Save JSON report
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Full report saved to: {output_file}")
    
    # Print human-readable summary
    print("\n" + "="*80)
    print("PINECONE METADATA INSPECTION REPORT")
    print("="*80)
    print(f"\nTotal vectors in index: {report_data['total_vectors_in_index']}")
    print(f"Sample size analyzed: {report_data['sample_size']}")
    print(f"\nFields found: {len(report_data['field_analysis'])}\n")
    
    # Print critical fields for query intelligence
    critical_fields = [
        "content_type",
        "difficulty", 
        "primary_category",
        "types_discussed",
        "functions_covered",
        "relationship_type",
        "quadra",
        "temple",
        "season",
        "episode",
        "topics",
        "use_case"
    ]
    
    print("🎯 CRITICAL FIELDS FOR QUERY INTELLIGENCE:")
    print("-" * 80)
    
    for field in critical_fields:
        if field in report_data['field_analysis']:
            info = report_data['field_analysis'][field]
            print(f"\n📌 {field}:")
            print(f"   Type: {', '.join(info['field_types'])}")
            print(f"   Appears in: {info['appears_in_n_documents']} documents")
            print(f"   Unique values: {info['unique_value_count']}")
            
            # Show values
            if info['unique_value_count'] <= 20:
                print(f"   Values: {', '.join(info['unique_values'])}")
            else:
                print(f"   Sample values: {', '.join(info['unique_values'][:10])}...")
                if info['sample_values_truncated']:
                    print(f"   (+ {info['unique_value_count'] - 10} more values)")
        else:
            print(f"\n📌 {field}: ❌ NOT FOUND IN METADATA")
    
    print("\n" + "="*80)
    print("\n💡 NEXT STEPS:")
    print("1. Review the full report: scripts/pinecone_metadata_report.json")
    print("2. Check field types (array vs string) for correct Pinecone operators")
    print("3. Verify relationship_type values (golden vs golden_pair)")
    print("4. Update FilterBuilder in query_intelligence.py with correct values")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        # Run inspection
        report = inspect_metadata(sample_size=200)
        
        # Generate report
        generate_report(report)
        
        print("✅ Inspection complete!")
        
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
        import traceback
        traceback.print_exc()
