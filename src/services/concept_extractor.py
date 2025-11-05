"""
Concept Extractor Service
Analyzes document content via Claude API and extracts knowledge graph data.
"""

import os
import json
import anthropic
from datetime import datetime
from typing import Optional, Dict, List
import asyncio


# Allowed relationship types for validation
ALLOWED_RELATIONSHIP_TYPES = [
    "requires_understanding",
    "leads_to",
    "contrasts_with",
    "builds_on",
    "enables",
    "manifests_as",
    "part_of",
    "related_to"
]

# Allowed concept types
ALLOWED_CONCEPT_TYPES = [
    "theory",
    "process",
    "function",
    "framework",
    "principle",
    "concept"
]

# Allowed categories
ALLOWED_CATEGORIES = [
    "foundational",
    "intermediate",
    "advanced"
]


def preprocess_document_text(text: str, max_chars: int = 100000) -> str:
    """
    Preprocess document text before sending to Claude.
    
    - Truncates if > max_chars (Claude context limit)
    - Smart sampling: first 30%, last 20%, middle 50%
    - Removes excessive whitespace
    - Preserves original terminology
    
    Args:
        text: Raw document text
        max_chars: Maximum character limit (default: 100,000)
        
    Returns:
        Preprocessed text ready for Claude API
    """
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # If under limit, return as-is
    if len(text) <= max_chars:
        return text
    
    # Smart truncation: prioritize intro, conclusion, sample middle
    first_30_chars = int(max_chars * 0.30)
    last_20_chars = int(max_chars * 0.20)
    middle_50_chars = max_chars - first_30_chars - last_20_chars
    
    # Calculate positions
    first_section = text[:first_30_chars]
    
    # Last section
    last_section = text[-last_20_chars:] if len(text) > last_20_chars else ""
    
    # Middle section - sample from center
    middle_start = len(text) // 3
    middle_end = middle_start + middle_50_chars
    middle_section = text[middle_start:middle_end] if middle_start < len(text) else ""
    
    # Combine sections with markers
    truncated = f"""{first_section}

... [MIDDLE SECTION SAMPLED] ...

{middle_section}

... [CONCLUSION] ...

{last_section}"""
    
    return truncated


def validate_extraction(data: Dict) -> bool:
    """
    Validate extraction response from Claude.
    
    Checks:
    - Required fields present
    - Relationship types valid
    - Concept types valid
    - Categories valid
    - No empty labels
    
    Args:
        data: Extraction result dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Check required top-level fields
        if "concepts" not in data or "relationships" not in data:
            print("❌ Validation failed: Missing 'concepts' or 'relationships'")
            return False
        
        if not isinstance(data["concepts"], list) or not isinstance(data["relationships"], list):
            print("❌ Validation failed: 'concepts' and 'relationships' must be arrays")
            return False
        
        # Validate each concept
        for concept in data["concepts"]:
            # Required fields
            if not all(key in concept for key in ["label", "type", "category", "definition"]):
                print(f"❌ Validation failed: Concept missing required fields: {concept}")
                return False
            
            # Non-empty label
            if not concept["label"] or not concept["label"].strip():
                print(f"❌ Validation failed: Empty concept label")
                return False
            
            # Valid type
            if concept["type"] not in ALLOWED_CONCEPT_TYPES:
                print(f"⚠️ Warning: Unknown concept type '{concept['type']}', using 'concept'")
                concept["type"] = "concept"
            
            # Valid category
            if concept["category"] not in ALLOWED_CATEGORIES:
                print(f"⚠️ Warning: Unknown category '{concept['category']}', using 'foundational'")
                concept["category"] = "foundational"
        
        # Validate each relationship
        for rel in data["relationships"]:
            # Required fields
            if not all(key in rel for key in ["from", "to", "type", "evidence"]):
                print(f"❌ Validation failed: Relationship missing required fields: {rel}")
                return False
            
            # Non-empty labels
            if not rel["from"] or not rel["to"]:
                print(f"❌ Validation failed: Empty relationship labels")
                return False
            
            # Valid relationship type
            if rel["type"] not in ALLOWED_RELATIONSHIP_TYPES:
                print(f"⚠️ Warning: Unknown relationship type '{rel['type']}', using 'related_to'")
                rel["type"] = "related_to"
        
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


async def track_extraction_cost(document_id: str, input_tokens: int, output_tokens: int, success: bool, error: Optional[str] = None):
    """
    Track extraction costs to /data/extraction-costs.json
    
    Args:
        document_id: Document identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        success: Whether extraction succeeded
        error: Error message if failed
    """
    # Claude Sonnet 4.5 pricing (as of Nov 2025)
    # Input: $3 per million tokens
    # Output: $15 per million tokens
    input_cost = (input_tokens / 1_000_000) * 3.0
    output_cost = (output_tokens / 1_000_000) * 15.0
    total_cost = input_cost + output_cost
    
    cost_entry = {
        "document_id": document_id,
        "timestamp": datetime.utcnow().isoformat(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": round(total_cost, 6),
        "success": success,
        "error": error
    }
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Append to cost tracking file
    cost_file = "data/extraction-costs.json"
    
    try:
        # Read existing costs
        if os.path.exists(cost_file):
            with open(cost_file, 'r') as f:
                costs = json.load(f)
        else:
            costs = []
        
        # Append new entry
        costs.append(cost_entry)
        
        # Write back
        with open(cost_file, 'w') as f:
            json.dump(costs, f, indent=2)
        
        print(f"💰 Cost tracked: {document_id} - ${total_cost:.6f} ({input_tokens} in, {output_tokens} out)")
        
    except Exception as e:
        print(f"❌ Failed to track cost: {e}")


async def extract_concepts(document_text: str, document_id: str) -> Optional[Dict]:
    """
    Extract concepts and relationships from document using Claude API.
    
    Args:
        document_text: Full document text
        document_id: Document identifier
        
    Returns:
        Dict with concepts, relationships, and metadata, or None if failed
    """
    try:
        print(f"🔍 Extracting concepts from document: {document_id}")
        
        # 1. Preprocess text
        processed_text = preprocess_document_text(document_text)
        char_count = len(processed_text)
        was_truncated = len(document_text) > len(processed_text)
        
        if was_truncated:
            print(f"✂️ Text truncated: {len(document_text):,} → {char_count:,} chars")
        else:
            print(f"📄 Processing {char_count:,} characters")
        
        # 2. Build Claude API prompt
        prompt = f"""You are analyzing a transcript of a CS Joseph lecture on MBTI/Jungian psychology.

Extract:
1. KEY CONCEPTS - Important ideas, theories, processes discussed
2. RELATIONSHIPS - How concepts connect (prerequisite, leads to, contrasts with, etc.)

Return ONLY valid JSON in this format:
{{
  "concepts": [
    {{
      "label": "Concept Name",
      "type": "theory|process|function|framework|principle|concept",
      "category": "foundational|intermediate|advanced",
      "definition": "Brief definition (1-2 sentences)"
    }}
  ],
  "relationships": [
    {{
      "from": "Concept A",
      "to": "Concept B",
      "type": "requires_understanding|leads_to|contrasts_with|builds_on|enables|manifests_as|part_of|related_to",
      "evidence": "Brief quote or paraphrase showing this connection"
    }}
  ]
}}

Guidelines:
- Extract 5-15 key concepts per document (most important ones)
- Extract 3-10 relationships (only clear, explicit connections)
- Use consistent terminology (e.g. always "Shadow Integration" not sometimes "Shadow Work")
- Focus on conceptual relationships, not just co-occurrence
- Mark foundational concepts (core pillars of teaching)

Document text:
{processed_text}"""
        
        # 3. Call Anthropic Claude API
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        print(f"🤖 Calling Claude API...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Latest Claude Sonnet 4
            max_tokens=4096,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # 4. Parse JSON response
        response_text = response.content[0].text
        
        # Try to extract JSON if wrapped in markdown
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        extracted = json.loads(response_text)
        
        # 5. Validate structure
        if not validate_extraction(extracted):
            raise ValueError("Extraction validation failed")
        
        # 6. Add metadata
        extracted["document_id"] = document_id
        extracted["extracted_at"] = datetime.utcnow().isoformat()
        extracted["input_tokens"] = response.usage.input_tokens
        extracted["output_tokens"] = response.usage.output_tokens
        extracted["was_truncated"] = was_truncated
        extracted["original_length"] = len(document_text)
        extracted["processed_length"] = char_count
        
        # 7. Track cost
        await track_extraction_cost(
            document_id,
            response.usage.input_tokens,
            response.usage.output_tokens,
            success=True
        )
        
        print(f"✅ Extracted {len(extracted['concepts'])} concepts, {len(extracted['relationships'])} relationships")
        
        return extracted
        
    except json.JSONDecodeError as e:
        error_msg = f"JSON parsing failed: {str(e)}"
        print(f"❌ {error_msg}")
        await track_extraction_cost(document_id, 0, 0, success=False, error=error_msg)
        return None
        
    except Exception as e:
        error_msg = f"Extraction failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Track cost even on failure if we got a response
        if 'response' in locals() and hasattr(response, 'usage'):
            await track_extraction_cost(
                document_id,
                response.usage.input_tokens,
                response.usage.output_tokens,
                success=False,
                error=error_msg
            )
        else:
            await track_extraction_cost(document_id, 0, 0, success=False, error=error_msg)
        
        return None


async def get_extraction_cost_summary() -> Dict:
    """
    Get summary of extraction costs from tracking file.
    
    Returns:
        Dict with total costs, success rate, token usage
    """
    cost_file = "data/extraction-costs.json"
    
    if not os.path.exists(cost_file):
        return {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "success_rate": 0,
            "total_cost": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "average_cost_per_extraction": 0
        }
    
    try:
        with open(cost_file, 'r') as f:
            costs = json.load(f)
        
        total = len(costs)
        successful = sum(1 for c in costs if c.get("success", False))
        failed = total - successful
        
        total_cost = sum(c.get("cost", 0) for c in costs)
        total_input = sum(c.get("input_tokens", 0) for c in costs)
        total_output = sum(c.get("output_tokens", 0) for c in costs)
        
        return {
            "total_extractions": total,
            "successful_extractions": successful,
            "failed_extractions": failed,
            "success_rate": round((successful / total * 100) if total > 0 else 0, 2),
            "total_cost": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "average_cost_per_extraction": round(total_cost / total, 6) if total > 0 else 0,
            "recent_extractions": costs[-10:]  # Last 10 extractions
        }
        
    except Exception as e:
        print(f"❌ Error reading cost summary: {e}")
        return {"error": str(e)}
