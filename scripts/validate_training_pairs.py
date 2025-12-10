#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TRAINING PAIR VALIDATOR
═══════════════════════════════════════════════════════════════════════════════

Validates Q&A training pairs against the CS Joseph type reference.
Catches function slot errors, four sides mistakes, and temperament mismatches.

USAGE:
    python validate_training_pairs.py input.jsonl reference_data.json

OUTPUT:
    - input_CLEAN.jsonl     (pairs that passed validation)
    - input_FLAGGED.jsonl   (pairs with potential errors)
    - input_REPORT.txt      (summary of findings)

═══════════════════════════════════════════════════════════════════════════════
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════════════════
# REFERENCE DATA LOADER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TypeReference:
    """Holds all reference data for validation."""
    
    # Function -> Position -> List of Types
    function_positions: dict = field(default_factory=dict)
    
    # Type -> Shadow Type
    shadow_types: dict = field(default_factory=dict)
    
    # Type -> Subconscious Type
    subconscious_types: dict = field(default_factory=dict)
    
    # Type -> Superego Type
    superego_types: dict = field(default_factory=dict)
    
    # Type -> Temperament
    type_temperaments: dict = field(default_factory=dict)
    
    # Type -> Full function stack {position: function}
    type_stacks: dict = field(default_factory=dict)
    
    # Temperament -> List of Types
    temperament_types: dict = field(default_factory=dict)
    
    # Type -> Quadra
    type_quadras: dict = field(default_factory=dict)


def load_reference(filepath: str) -> TypeReference:
    """Load and parse reference_data.json into validation structures."""
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    ref = TypeReference()
    
    # Initialize function positions
    functions = ['Se', 'Si', 'Ne', 'Ni', 'Te', 'Ti', 'Fe', 'Fi']
    positions = ['Hero', 'Parent', 'Child', 'Inferior', 'Nemesis', 'Critic', 'Trickster', 'Demon']
    
    for func in functions:
        ref.function_positions[func] = {pos: [] for pos in positions}
    
    # Initialize temperaments
    ref.temperament_types = {
        'Guardian': [],
        'Artisan': [],
        'Intellectual': [],
        'Idealist': []
    }
    
    # Process each type
    for type_data in data.get('types', []):
        type_code = type_data.get('code', '')
        
        if not type_code:
            continue
        
        # Get temperament
        categories = type_data.get('categories', {})
        temperament = categories.get('temperament', '')
        if temperament:
            ref.type_temperaments[type_code] = temperament
            if temperament in ref.temperament_types:
                ref.temperament_types[temperament].append(type_code)
        
        # Get quadra
        quadra = categories.get('quadra', '')
        if quadra:
            ref.type_quadras[type_code] = quadra
        
        # Get four sides
        four_sides = type_data.get('four_sides', {})
        
        # Shadow
        shadow = four_sides.get('shadow', {})
        shadow_type = shadow.get('type', '')
        if shadow_type:
            ref.shadow_types[type_code] = shadow_type
        
        # Subconscious
        subconscious = four_sides.get('subconscious', {})
        sub_type = subconscious.get('type', '')
        if sub_type:
            ref.subconscious_types[type_code] = sub_type
        
        # Superego
        superego = four_sides.get('superego', {})
        super_type = superego.get('type', '')
        if super_type:
            ref.superego_types[type_code] = super_type
        
        # Get function stack from ego
        ego = four_sides.get('ego', {})
        ego_functions = ego.get('functions', [])
        
        ref.type_stacks[type_code] = {}
        
        for func_data in ego_functions:
            position = func_data.get('position', '')
            function = func_data.get('function', '')
            
            if position and function:
                ref.type_stacks[type_code][position] = function
                
                # Add to function_positions
                if function in ref.function_positions:
                    if position in ref.function_positions[function]:
                        if type_code not in ref.function_positions[function][position]:
                            ref.function_positions[function][position].append(type_code)
        
        # Get shadow functions
        shadow_functions = shadow.get('functions', [])
        for func_data in shadow_functions:
            position = func_data.get('position', '')
            function = func_data.get('function', '')
            
            if position and function:
                ref.type_stacks[type_code][position] = function
                
                if function in ref.function_positions:
                    if position in ref.function_positions[function]:
                        if type_code not in ref.function_positions[function][position]:
                            ref.function_positions[function][position].append(type_code)
    
    return ref


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# All 16 types
TYPES = [
    'ESTJ', 'ESTP', 'ESFJ', 'ESFP', 'ENTJ', 'ENTP', 'ENFJ', 'ENFP',
    'ISTJ', 'ISTP', 'ISFJ', 'ISFP', 'INTJ', 'INTP', 'INFJ', 'INFP'
]

# All 8 functions
FUNCTIONS = ['Se', 'Si', 'Ne', 'Ni', 'Te', 'Ti', 'Fe', 'Fi']

# All 8 positions
POSITIONS = ['Hero', 'Parent', 'Child', 'Inferior', 'Nemesis', 'Critic', 'Trickster', 'Demon']

# Temperaments
TEMPERAMENTS = ['Guardian', 'Artisan', 'Intellectual', 'Idealist']


def find_type_function_claims(text: str) -> list[dict]:
    """
    Find claims like "ESTP has Ti Hero" or "Ti Hero types are ISTP and INTP".
    Returns list of {type, function, position} dicts.
    """
    claims = []
    text_upper = text.upper()
    text_lower = text.lower()
    
    # Pattern 1: "TYPE has/have FUNCTION POSITION"
    # e.g., "ESTP has Ti Hero", "ENFPs have Ne Hero"
    pattern1 = re.compile(
        r'\b(' + '|'.join(TYPES) + r')s?\b[^.]*?\b(has|have|with)\b[^.]*?\b(' + 
        '|'.join(FUNCTIONS) + r')\s+(' + '|'.join(POSITIONS) + r')\b',
        re.IGNORECASE
    )
    
    for match in pattern1.finditer(text):
        claims.append({
            'type': match.group(1).upper(),
            'function': match.group(3),
            'position': match.group(4).title(),
            'context': match.group(0),
            'pattern': 'TYPE has FUNCTION POSITION'
        })
    
    # Pattern 2: "FUNCTION POSITION types: TYPE, TYPE"
    # e.g., "Ti Hero types are ISTP and INTP"
    # Use greedy match to capture the entire clause including all types
    pattern2 = re.compile(
        r'\b(' + '|'.join(FUNCTIONS) + r')\s+(' + '|'.join(POSITIONS) + 
        r')\b[^.]*?\b(types?|are|is)\b([^.]*)',
        re.IGNORECASE
    )
    
    for match in pattern2.finditer(text):
        # Find all types mentioned in the rest of this sentence/clause
        rest_of_sentence = match.group(4)  # Everything after "types/are/is"
        types_found = re.findall(r'\b(' + '|'.join(TYPES) + r')\b', rest_of_sentence, re.IGNORECASE)
        
        for t in types_found:
            claims.append({
                'type': t.upper(),
                'function': match.group(1),
                'position': match.group(2).title(),
                'context': match.group(0),
                'pattern': 'FUNCTION POSITION types'
            })
    
    # Pattern 3: "TYPE's FUNCTION POSITION" or "TYPE FUNCTION POSITION"
    # e.g., "ESTP's Se Hero", "the INTJ Ni Hero"
    pattern3 = re.compile(
        r'\b(' + '|'.join(TYPES) + r")(?:'s|s')?\s+(" + 
        '|'.join(FUNCTIONS) + r')\s+(' + '|'.join(POSITIONS) + r')\b',
        re.IGNORECASE
    )
    
    for match in pattern3.finditer(text):
        claims.append({
            'type': match.group(1).upper(),
            'function': match.group(2),
            'position': match.group(3).title(),
            'context': match.group(0),
            'pattern': "TYPE's FUNCTION POSITION"
        })
    
    # Deduplicate
    seen = set()
    unique_claims = []
    for claim in claims:
        key = (claim['type'], claim['function'], claim['position'])
        if key not in seen:
            seen.add(key)
            unique_claims.append(claim)
    
    return unique_claims


def find_shadow_claims(text: str) -> list[dict]:
    """
    Find claims about shadow types.
    e.g., "INTJ's shadow is ENFP"
    """
    claims = []
    
    # Pattern: "TYPE's shadow is TYPE" or "shadow of TYPE is TYPE"
    pattern1 = re.compile(
        r'\b(' + '|'.join(TYPES) + r")(?:'s|s')?\s+shadow\s+(?:is|type is|=)\s+(" + 
        '|'.join(TYPES) + r')\b',
        re.IGNORECASE
    )
    
    for match in pattern1.finditer(text):
        claims.append({
            'ego_type': match.group(1).upper(),
            'shadow_type': match.group(2).upper(),
            'context': match.group(0),
            'side': 'shadow'
        })
    
    # Pattern: "shadow of TYPE is TYPE"
    pattern2 = re.compile(
        r'shadow\s+of\s+(?:the\s+)?(' + '|'.join(TYPES) + r')\s+(?:is|=)\s+(' + 
        '|'.join(TYPES) + r')\b',
        re.IGNORECASE
    )
    
    for match in pattern2.finditer(text):
        claims.append({
            'ego_type': match.group(1).upper(),
            'shadow_type': match.group(2).upper(),
            'context': match.group(0),
            'side': 'shadow'
        })
    
    return claims


def find_subconscious_claims(text: str) -> list[dict]:
    """Find claims about subconscious types."""
    claims = []
    
    pattern = re.compile(
        r'\b(' + '|'.join(TYPES) + r")(?:'s|s')?\s+subconscious\s+(?:is|type is|=)\s+(" + 
        '|'.join(TYPES) + r')\b',
        re.IGNORECASE
    )
    
    for match in pattern.finditer(text):
        claims.append({
            'ego_type': match.group(1).upper(),
            'sub_type': match.group(2).upper(),
            'context': match.group(0),
            'side': 'subconscious'
        })
    
    return claims


def find_superego_claims(text: str) -> list[dict]:
    """Find claims about superego types."""
    claims = []
    
    pattern = re.compile(
        r'\b(' + '|'.join(TYPES) + r")(?:'s|s')?\s+superego\s+(?:is|type is|=)\s+(" + 
        '|'.join(TYPES) + r')\b',
        re.IGNORECASE
    )
    
    for match in pattern.finditer(text):
        claims.append({
            'ego_type': match.group(1).upper(),
            'super_type': match.group(2).upper(),
            'context': match.group(0),
            'side': 'superego'
        })
    
    return claims


def find_temperament_claims(text: str) -> list[dict]:
    """
    Find claims about temperaments.
    e.g., "ESTP is a Guardian" or "Guardians include ESTJ"
    """
    claims = []
    
    # Pattern: "TYPE is a TEMPERAMENT"
    pattern1 = re.compile(
        r'\b(' + '|'.join(TYPES) + r')s?\b[^.]*?\b(?:is|are)\s+(?:a\s+)?(' + 
        '|'.join(TEMPERAMENTS) + r')s?\b',
        re.IGNORECASE
    )
    
    for match in pattern1.finditer(text):
        claims.append({
            'type': match.group(1).upper(),
            'temperament': match.group(2).title(),
            'context': match.group(0)
        })
    
    # Pattern: "TEMPERAMENT types: TYPE, TYPE"
    pattern2 = re.compile(
        r'\b(' + '|'.join(TEMPERAMENTS) + r')s?\b[^.]*?(?:include|are|:)[^.]*?(' + 
        '|'.join(TYPES) + r')\b',
        re.IGNORECASE
    )
    
    for match in pattern2.finditer(text):
        sentence = match.group(0)
        types_found = re.findall(r'\b(' + '|'.join(TYPES) + r')\b', sentence, re.IGNORECASE)
        
        for t in types_found:
            claims.append({
                'type': t.upper(),
                'temperament': match.group(1).title(),
                'context': sentence
            })
    
    return claims


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_function_claim(claim: dict, ref: TypeReference) -> Optional[str]:
    """
    Validate a type+function+position claim.
    Returns error message if invalid, None if valid.
    """
    type_code = claim['type']
    function = claim['function']
    position = claim['position']
    
    # Normalize function case (Se, Ti, etc.)
    function = function[0].upper() + function[1].lower() if len(function) == 2 else function
    
    # Check if this type actually has this function in this position
    if type_code in ref.type_stacks:
        actual_function = ref.type_stacks[type_code].get(position)
        
        if actual_function and actual_function != function:
            return f"ERROR: {type_code} has {actual_function} {position}, NOT {function} {position}"
    
    # Check reverse: does this function+position belong to this type?
    if function in ref.function_positions:
        if position in ref.function_positions[function]:
            valid_types = ref.function_positions[function][position]
            
            if valid_types and type_code not in valid_types:
                return f"ERROR: {function} {position} types are {valid_types}, NOT {type_code}"
    
    return None


def validate_shadow_claim(claim: dict, ref: TypeReference) -> Optional[str]:
    """Validate a shadow type claim."""
    ego = claim['ego_type']
    claimed_shadow = claim['shadow_type']
    
    actual_shadow = ref.shadow_types.get(ego)
    
    if actual_shadow and actual_shadow != claimed_shadow:
        return f"ERROR: {ego}'s shadow is {actual_shadow}, NOT {claimed_shadow}"
    
    return None


def validate_subconscious_claim(claim: dict, ref: TypeReference) -> Optional[str]:
    """Validate a subconscious type claim."""
    ego = claim['ego_type']
    claimed_sub = claim['sub_type']
    
    actual_sub = ref.subconscious_types.get(ego)
    
    if actual_sub and actual_sub != claimed_sub:
        return f"ERROR: {ego}'s subconscious is {actual_sub}, NOT {claimed_sub}"
    
    return None


def validate_superego_claim(claim: dict, ref: TypeReference) -> Optional[str]:
    """Validate a superego type claim."""
    ego = claim['ego_type']
    claimed_super = claim['super_type']
    
    actual_super = ref.superego_types.get(ego)
    
    if actual_super and actual_super != claimed_super:
        return f"ERROR: {ego}'s superego is {actual_super}, NOT {claimed_super}"
    
    return None


def validate_temperament_claim(claim: dict, ref: TypeReference) -> Optional[str]:
    """Validate a temperament claim."""
    type_code = claim['type']
    claimed_temp = claim['temperament']
    
    actual_temp = ref.type_temperaments.get(type_code)
    
    if actual_temp and actual_temp != claimed_temp:
        return f"ERROR: {type_code} is {actual_temp}, NOT {claimed_temp}"
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    """Result of validating a single Q&A pair."""
    pair: dict
    line_number: int
    is_valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def validate_pair(pair: dict, line_number: int, ref: TypeReference) -> ValidationResult:
    """Validate a single Q&A pair against reference data."""
    
    result = ValidationResult(
        pair=pair,
        line_number=line_number,
        is_valid=True,
        errors=[],
        warnings=[]
    )
    
    # Extract the assistant's answer
    messages = pair.get('messages', [])
    answer = ''
    
    for msg in messages:
        if msg.get('role') == 'assistant':
            answer = msg.get('content', '')
            break
    
    if not answer:
        result.warnings.append("No assistant content found")
        return result
    
    # Find and validate function claims
    function_claims = find_type_function_claims(answer)
    for claim in function_claims:
        error = validate_function_claim(claim, ref)
        if error:
            result.is_valid = False
            result.errors.append({
                'type': 'function_slot',
                'claim': claim,
                'error': error
            })
    
    # Find and validate shadow claims
    shadow_claims = find_shadow_claims(answer)
    for claim in shadow_claims:
        error = validate_shadow_claim(claim, ref)
        if error:
            result.is_valid = False
            result.errors.append({
                'type': 'shadow',
                'claim': claim,
                'error': error
            })
    
    # Find and validate subconscious claims
    sub_claims = find_subconscious_claims(answer)
    for claim in sub_claims:
        error = validate_subconscious_claim(claim, ref)
        if error:
            result.is_valid = False
            result.errors.append({
                'type': 'subconscious',
                'claim': claim,
                'error': error
            })
    
    # Find and validate superego claims
    super_claims = find_superego_claims(answer)
    for claim in super_claims:
        error = validate_superego_claim(claim, ref)
        if error:
            result.is_valid = False
            result.errors.append({
                'type': 'superego',
                'claim': claim,
                'error': error
            })
    
    # Find and validate temperament claims
    temp_claims = find_temperament_claims(answer)
    for claim in temp_claims:
        error = validate_temperament_claim(claim, ref)
        if error:
            result.is_valid = False
            result.errors.append({
                'type': 'temperament',
                'claim': claim,
                'error': error
            })
    
    return result


def validate_jsonl_file(input_path: str, ref: TypeReference) -> list[ValidationResult]:
    """Validate all pairs in a JSONL file."""
    
    results = []
    
    with open(input_path, 'r') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                pair = json.loads(line)
                result = validate_pair(pair, i, ref)
                results.append(result)
            except json.JSONDecodeError as e:
                results.append(ValidationResult(
                    pair={'raw': line},
                    line_number=i,
                    is_valid=False,
                    errors=[{'type': 'json_parse', 'error': str(e)}]
                ))
    
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

def write_outputs(input_path: str, results: list[ValidationResult]):
    """Write clean file, flagged file, and report."""
    
    input_file = Path(input_path)
    base_name = input_file.stem
    output_dir = input_file.parent
    
    clean_path = output_dir / f"{base_name}_CLEAN.jsonl"
    flagged_path = output_dir / f"{base_name}_FLAGGED.jsonl"
    report_path = output_dir / f"{base_name}_REPORT.txt"
    
    clean_count = 0
    flagged_count = 0
    
    # Write clean and flagged files
    with open(clean_path, 'w') as clean_f, open(flagged_path, 'w') as flagged_f:
        for result in results:
            if result.is_valid:
                clean_f.write(json.dumps(result.pair) + '\n')
                clean_count += 1
            else:
                flagged_f.write(json.dumps(result.pair) + '\n')
                flagged_count += 1
    
    # Write report
    with open(report_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("TRAINING PAIR VALIDATION REPORT\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Input file: {input_path}\n")
        f.write(f"Total pairs: {len(results)}\n")
        f.write(f"Clean pairs: {clean_count}\n")
        f.write(f"Flagged pairs: {flagged_count}\n")
        f.write(f"Error rate: {flagged_count / len(results) * 100:.1f}%\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("ERRORS FOUND\n")
        f.write("-" * 70 + "\n\n")
        
        error_counts = {}
        
        for result in results:
            if not result.is_valid:
                f.write(f"Line {result.line_number}:\n")
                
                # Show the question
                messages = result.pair.get('messages', [])
                for msg in messages:
                    if msg.get('role') == 'user':
                        f.write(f"  Q: {msg.get('content', '')[:100]}...\n")
                        break
                
                for error in result.errors:
                    error_type = error.get('type', 'unknown')
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                    
                    f.write(f"  ❌ {error.get('error', 'Unknown error')}\n")
                    
                    if 'claim' in error:
                        f.write(f"     Context: \"{error['claim'].get('context', '')}\"\n")
                
                f.write("\n")
        
        f.write("-" * 70 + "\n")
        f.write("ERROR SUMMARY\n")
        f.write("-" * 70 + "\n\n")
        
        for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            f.write(f"  {error_type}: {count}\n")
    
    print(f"\n{'=' * 50}")
    print("VALIDATION COMPLETE")
    print(f"{'=' * 50}")
    print(f"Total pairs:   {len(results)}")
    print(f"Clean pairs:   {clean_count}")
    print(f"Flagged pairs: {flagged_count}")
    print(f"Error rate:    {flagged_count / len(results) * 100:.1f}%")
    print(f"{'=' * 50}")
    print(f"\nOutputs:")
    print(f"  ✅ {clean_path}")
    print(f"  ❌ {flagged_path}")
    print(f"  📋 {report_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_training_pairs.py <input.jsonl> <reference_data.json>")
        print("\nExample:")
        print("  python validate_training_pairs.py batch_001.jsonl reference_data.json")
        sys.exit(1)
    
    input_path = sys.argv[1]
    reference_path = sys.argv[2]
    
    # Check files exist
    if not Path(input_path).exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    if not Path(reference_path).exists():
        print(f"Error: Reference file not found: {reference_path}")
        sys.exit(1)
    
    print(f"Loading reference data from {reference_path}...")
    ref = load_reference(reference_path)
    
    print(f"Validating pairs from {input_path}...")
    results = validate_jsonl_file(input_path, ref)
    
    write_outputs(input_path, results)


if __name__ == "__main__":
    main()
