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
    """Extract MBTI types mentioned in user message."""
    # Defensive: ensure message is a string
    if not isinstance(message, str):
        print(f"⚠️ [TYPE INJECTION] Expected string, got {type(message)}. Converting...")
        message = str(message)
    
    message_upper = message.upper()
    found_types = []
    for mbti_type in MBTI_TYPES:
        if re.search(rf'\b{mbti_type}\b', message_upper):
            found_types.append(mbti_type)
    return found_types

def get_type_stack(type_code: str) -> dict | None:
    """Get full stack for a type from reference data."""
    data = load_reference_data()
    for type_data in data['types']:
        if type_data['code'] == type_code:
            return type_data
    return None

def format_stack_for_prompt(type_data: dict) -> str:
    """Format type data into concise prompt injection."""
    code = type_data['code']
    four_sides = type_data['four_sides']
    
    ego_funcs = four_sides['ego']['functions']
    ego_str = ", ".join([f"{f['function']} {f['position'].lower()}" for f in ego_funcs])
    
    shadow_funcs = four_sides['shadow']['functions']
    shadow_str = ", ".join([f"{f['function']} {f['position'].lower()}" for f in shadow_funcs])
    
    categories = type_data['categories']
    
    return f"""
**{code} Function Stack (CS Joseph):**
- Ego: {ego_str}
- Shadow: {shadow_str}
- Quadra: {categories['quadra']} | Temple: {categories['temple']} | Archetype: {categories['archetype']}
- Four Sides: Ego={four_sides['ego']['type']}, Shadow={four_sides['shadow']['type']}, Subconscious={four_sides['subconscious']['type']}, Superego={four_sides['superego']['type']}
"""

def build_context_injection(user_message_content) -> str:
    """
    Build context injection for detected types.
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
    
    injection_parts = ["**Reference Data (USE THIS, not general MBTI knowledge):**"]
    
    for type_code in detected_types:
        type_data = get_type_stack(type_code)
        if type_data:
            injection_parts.append(format_stack_for_prompt(type_data))
        else:
            print(f"⚠️ [TYPE INJECTION] No data found for {type_code}")
    
    return "\n".join(injection_parts)
