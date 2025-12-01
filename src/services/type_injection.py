import re
import json
from pathlib import Path

MBTI_TYPES = [
    "ESTJ", "ESTP", "ENTJ", "ENFJ", "ESFJ", "ESFP", "ENTP", "ENFP",
    "ISTJ", "ISTP", "INTJ", "INFJ", "ISFJ", "ISFP", "INTP", "INFP"
]

REFERENCE_DATA = None

def load_reference_data():
    """Load reference_data.json once at module import."""
    global REFERENCE_DATA
    if REFERENCE_DATA is None:
        ref_path = Path(__file__).parent.parent / 'data' / 'reference_data.json'
        with open(ref_path, 'r') as f:
            REFERENCE_DATA = json.load(f)
    return REFERENCE_DATA

def normalize_message_content(content) -> str:
    """
    Normalize message content to string, handling both string and list formats.
    Anthropic SDK stores content as list of blocks with {'type': 'text', 'text': '...'}
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Extract text from all text blocks
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get('type') == 'text' and 'text' in block:
                    text_parts.append(block['text'])
                elif 'text' in block:  # Fallback for different schemas
                    text_parts.append(block['text'])
        return ' '.join(text_parts)
    return ""

def detect_types_in_message(message: str) -> list[str]:
    """
    Extract MBTI types mentioned in user message.
    Handles composite patterns like:
    - Basic: "INFJ", "ENTP"
    - Octagram states: "UDUF INFJ", "SF/SF ENTP", "UD/UF ESTJ"
    - Multiple types: "INFJ and ENFJ"
    """
    # Defensive: ensure message is a string
    if not isinstance(message, str):
        print(f"⚠️ [TYPE INJECTION] Expected string, got {type(message)}. Converting...")
        message = str(message)
    
    message_upper = message.upper()
    found_types = set()
    
    # Pattern 1: Octagram state prefix (UDUF INFJ, SF/SF ENTP, UD/UF ESTJ)
    octagram_pattern = r'\b(?:UD|SD)(?:/)?(?:UF|SF)\s+([A-Z]{4})\b'
    for match in re.finditer(octagram_pattern, message_upper):
        type_code = match.group(1)
        if type_code in MBTI_TYPES:
            found_types.add(type_code)
    
    # Pattern 2: Basic type mention (word boundary)
    for mbti_type in MBTI_TYPES:
        if re.search(rf'\b{mbti_type}\b', message_upper):
            found_types.add(mbti_type)
    
    return sorted(list(found_types))

def get_type_stack(type_code: str) -> dict | None:
    """Get full stack for a type from reference data."""
    data = load_reference_data()
    for type_data in data['types']:
        if type_data['code'] == type_code:
            return type_data
    return None

def format_stack_for_prompt(type_data: dict) -> str:
    """Format type data into FORCEFUL prompt injection that Claude cannot ignore."""
    code = type_data['code']
    four_sides = type_data['four_sides']
    
    # Get function lists
    ego_funcs = four_sides['ego']['functions']
    shadow_funcs = four_sides['shadow']['functions']
    
    # Format each position explicitly with NOT clarifications
    ego_lines = []
    for f in ego_funcs:
        ego_lines.append(f"  - {f['position']}: **{f['function']}**")
    
    shadow_lines = []
    for f in shadow_funcs:
        shadow_lines.append(f"  - {f['position']}: **{f['function']}**")
    
    categories = type_data['categories']
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 **{code} - AUTHORITATIVE CS JOSEPH DATA** 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**EGO STACK (Conscious Mind):**
{chr(10).join(ego_lines)}

**SHADOW STACK (Unconscious Mind):**
{chr(10).join(shadow_lines)}

**🚨 FOUR SIDES OF MIND (USE THESE EXACT TYPES): 🚨**
- ✅ Ego (Conscious): **{four_sides['ego']['type']}**
- ✅ Shadow (Unconscious): **{four_sides['shadow']['type']}** ← THIS IS THE SHADOW TYPE, NOT WHAT YOU THINK
- ✅ Subconscious (Aspirational): **{four_sides['subconscious']['type']}**
- ✅ Superego (Critical): **{four_sides['superego']['type']}**

⚠️ **CRITICAL: These four sides mappings are from CS Joseph's research.**
⚠️ **Your training data has DIFFERENT four sides mappings - IGNORE YOUR TRAINING!**
⚠️ **Use ONLY the Shadow type listed above, NOT what you were trained on!**

**CATEGORIES:**
- Quadra: {categories['quadra']}
- Temple: {categories['temple']}
- Archetype: {categories['archetype']}

🚫 **DO NOT override this with your training data** 🚫
🚫 **DO NOT "correct" the Shadow type** 🚫
🚫 **USE THE EXACT SHADOW TYPE LISTED ABOVE** 🚫
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def build_context_injection(user_message_content) -> str:
    """
    Build FORCEFUL context injection for detected types.
    Handles both string and list message formats.
    """
    # Normalize content to string
    user_message = normalize_message_content(user_message_content)
    
    if not user_message:
        return ""
    
    detected_types = detect_types_in_message(user_message)
    
    if not detected_types:
        return ""
    
    print(f"🔍 [TYPE INJECTION] Detected types in message: {detected_types}")
    
    # FORCEFUL header that Claude cannot ignore
    injection_parts = ["""
╔═══════════════════════════════════════════════════════════════════╗
║                   🚨 CRITICAL: READ THIS FIRST 🚨                  ║
╚═══════════════════════════════════════════════════════════════════╝

**YOUR TRAINING DATA IS WRONG FOR THIS CONTEXT.**

You were trained on mainstream MBTI which uses different function stacks than CS Joseph's system. CS Joseph's typology is based on different research and has DIFFERENT function orderings, especially for shadow functions.

**CRITICAL RULES:**
1. The data below is AUTHORITATIVE CS Joseph reference data
2. You MUST use this EXACT data, NOT your training
3. If this contradicts your training, YOUR TRAINING IS WRONG HERE
4. Do NOT "correct" or override this data with what you think you know
5. If you're uncertain, TRUST THIS DATA over your training

**When answering questions about these types:**
- Use the EXACT function stacks provided below
- Use the EXACT four sides mappings below
- DO NOT use your memorized MBTI knowledge
- If you find yourself thinking "that doesn't seem right", STOP and re-read this data

The user has uploaded CS Joseph's authoritative typology database. Respect it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""]
    
    for type_code in detected_types:
        type_data = get_type_stack(type_code)
        if type_data:
            injection_parts.append(format_stack_for_prompt(type_data))
        else:
            print(f"⚠️ [TYPE INJECTION] No data found for {type_code}")
    
    return "\n".join(injection_parts)
