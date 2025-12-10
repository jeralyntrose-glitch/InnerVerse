#!/usr/bin/env python3
"""
Test script for validate_training_pairs.py
Tests regex patterns and validation logic against known correct/incorrect data.
"""

import json
import sys
sys.path.insert(0, '.')

from scripts.validate_training_pairs import (
    find_type_function_claims,
    find_shadow_claims,
    find_temperament_claims,
    load_reference,
    validate_function_claim,
    validate_shadow_claim,
    validate_temperament_claim
)

print("=" * 70)
print("VALIDATION SCRIPT TEST SUITE")
print("=" * 70)

# Load reference data
print("\n1. Loading reference_data.json...")
try:
    ref = load_reference('src/data/reference_data.json')
    print("   ✅ Reference data loaded successfully")
    print(f"   - Types loaded: {len(ref.type_stacks)}")
    print(f"   - Temperaments: {list(ref.temperament_types.keys())}")
except Exception as e:
    print(f"   ❌ Failed to load reference data: {e}")
    sys.exit(1)

# Verify reference data structure
print("\n2. Verifying reference data structure...")

# Check ESTP
print("\n   ESTP verification:")
estp_stack = ref.type_stacks.get('ESTP', {})
print(f"   - Hero: {estp_stack.get('Hero')} (expected: Se)")
print(f"   - Parent: {estp_stack.get('Parent')} (expected: Ti)")
print(f"   - Child: {estp_stack.get('Child')} (expected: Fe)")
print(f"   - Inferior: {estp_stack.get('Inferior')} (expected: Ni)")
assert estp_stack.get('Hero') == 'Se', "ESTP Hero should be Se"
assert estp_stack.get('Parent') == 'Ti', "ESTP Parent should be Ti"
assert estp_stack.get('Child') == 'Fe', "ESTP Child should be Fe"
assert estp_stack.get('Inferior') == 'Ni', "ESTP Inferior should be Ni"
print("   ✅ ESTP stack verified")

# Check ISTP
print("\n   ISTP verification:")
istp_stack = ref.type_stacks.get('ISTP', {})
print(f"   - Hero: {istp_stack.get('Hero')} (expected: Ti)")
print(f"   - Parent: {istp_stack.get('Parent')} (expected: Se)")
print(f"   - Child: {istp_stack.get('Child')} (expected: Ni)")
print(f"   - Inferior: {istp_stack.get('Inferior')} (expected: Fe)")
assert istp_stack.get('Hero') == 'Ti', "ISTP Hero should be Ti"
assert istp_stack.get('Parent') == 'Se', "ISTP Parent should be Se"
print("   ✅ ISTP stack verified")

# Check INTJ shadow
print("\n   INTJ shadow verification:")
intj_shadow = ref.shadow_types.get('INTJ')
print(f"   - Shadow: {intj_shadow} (expected: ENTP)")
assert intj_shadow == 'ENTP', "INTJ shadow should be ENTP"
print("   ✅ INTJ shadow verified")

# Check ESTP temperament
print("\n   ESTP temperament verification:")
estp_temp = ref.type_temperaments.get('ESTP')
print(f"   - Temperament: {estp_temp} (expected: Artisan)")
assert estp_temp == 'Artisan', "ESTP should be Artisan"
print("   ✅ ESTP temperament verified")

# Test regex patterns
print("\n" + "=" * 70)
print("3. TESTING REGEX PATTERNS")
print("=" * 70)

test_cases = [
    {
        "text": "ESTP has Ti Hero",
        "expected_type": "ESTP",
        "expected_function": "Ti",
        "expected_position": "Hero",
        "pattern_name": "TYPE has FUNCTION POSITION"
    },
    {
        "text": "ESTP's Se Hero",
        "expected_type": "ESTP",
        "expected_function": "Se",
        "expected_position": "Hero",
        "pattern_name": "TYPE's FUNCTION POSITION"
    },
    {
        "text": "Ti Hero types are ISTP and INTP",
        "expected_types": ["ISTP", "INTP"],
        "expected_function": "Ti",
        "expected_position": "Hero",
        "pattern_name": "FUNCTION POSITION types"
    },
    {
        "text": "The INTJ with their Ni Hero function",
        "expected_type": "INTJ",
        "expected_function": "Ni",
        "expected_position": "Hero",
        "pattern_name": "TYPE with FUNCTION POSITION"
    }
]

for i, tc in enumerate(test_cases):
    print(f"\n   Test {i+1}: \"{tc['text']}\"")
    claims = find_type_function_claims(tc['text'])
    
    if 'expected_types' in tc:
        found_types = [c['type'] for c in claims]
        for expected in tc['expected_types']:
            if expected in found_types:
                matching = [c for c in claims if c['type'] == expected][0]
                print(f"   ✅ Found: {matching['type']} {matching['function']} {matching['position']}")
            else:
                print(f"   ❌ Missing type: {expected}")
    else:
        if claims:
            c = claims[0]
            match = (c['type'] == tc['expected_type'] and 
                    c['position'] == tc['expected_position'])
            func_match = c['function'].lower() == tc['expected_function'].lower()
            if match and func_match:
                print(f"   ✅ Found: {c['type']} {c['function']} {c['position']}")
            else:
                print(f"   ❌ Mismatch: Got {c['type']} {c['function']} {c['position']}")
        else:
            print(f"   ❌ No claims found!")

# Test shadow pattern
print("\n   Test: Shadow claim regex")
shadow_text = "INTJ's shadow is ENFP"
shadow_claims = find_shadow_claims(shadow_text)
if shadow_claims:
    sc = shadow_claims[0]
    print(f"   Found: {sc['ego_type']}'s shadow is {sc['shadow_type']}")
    print(f"   ✅ Shadow pattern works")
else:
    print(f"   ❌ Shadow pattern failed to match: \"{shadow_text}\"")

# Test temperament pattern
print("\n   Test: Temperament claim regex")
temp_text = "ESTP is a Guardian"
temp_claims = find_temperament_claims(temp_text)
if temp_claims:
    tc = temp_claims[0]
    print(f"   Found: {tc['type']} is {tc['temperament']}")
    print(f"   ✅ Temperament pattern works")
else:
    print(f"   ❌ Temperament pattern failed to match: \"{temp_text}\"")

# Test validation logic
print("\n" + "=" * 70)
print("4. TESTING VALIDATION LOGIC")
print("=" * 70)

print("\n   CORRECT claims (should pass):")

correct_claims = [
    {"type": "ESTP", "function": "Se", "position": "Hero", "context": "test"},
    {"type": "ESTP", "function": "Ti", "position": "Parent", "context": "test"},
    {"type": "ISTP", "function": "Ti", "position": "Hero", "context": "test"},
    {"type": "INTJ", "function": "Ni", "position": "Hero", "context": "test"},
]

for claim in correct_claims:
    error = validate_function_claim(claim, ref)
    if error:
        print(f"   ❌ {claim['type']} {claim['function']} {claim['position']}: {error}")
    else:
        print(f"   ✅ {claim['type']} {claim['function']} {claim['position']}: PASSED")

print("\n   INCORRECT claims (should fail):")

incorrect_claims = [
    {"type": "ESTP", "function": "Ti", "position": "Hero", "context": "test", "expected_error": "Se Hero"},
    {"type": "ISTP", "function": "Se", "position": "Hero", "context": "test", "expected_error": "Ti Hero"},
    {"type": "INTJ", "function": "Ne", "position": "Hero", "context": "test", "expected_error": "Ni Hero"},
]

for claim in incorrect_claims:
    error = validate_function_claim(claim, ref)
    if error:
        print(f"   ✅ CAUGHT: {claim['type']} {claim['function']} {claim['position']}")
        print(f"      Error: {error}")
    else:
        print(f"   ❌ MISSED: {claim['type']} {claim['function']} {claim['position']} should have failed!")

# Test shadow validation
print("\n   Shadow validation:")
correct_shadow = {"ego_type": "INTJ", "shadow_type": "ENTP", "context": "test"}
wrong_shadow = {"ego_type": "INTJ", "shadow_type": "ENFP", "context": "test"}

error = validate_shadow_claim(correct_shadow, ref)
if error:
    print(f"   ❌ INTJ shadow=ENTP should pass: {error}")
else:
    print(f"   ✅ INTJ shadow=ENTP: PASSED")

error = validate_shadow_claim(wrong_shadow, ref)
if error:
    print(f"   ✅ CAUGHT: INTJ shadow=ENFP (wrong)")
    print(f"      Error: {error}")
else:
    print(f"   ❌ MISSED: INTJ shadow=ENFP should have failed!")

# Test temperament validation
print("\n   Temperament validation:")
correct_temp = {"type": "ESTP", "temperament": "Artisan", "context": "test"}
wrong_temp = {"type": "ESTP", "temperament": "Guardian", "context": "test"}

error = validate_temperament_claim(correct_temp, ref)
if error:
    print(f"   ❌ ESTP=Artisan should pass: {error}")
else:
    print(f"   ✅ ESTP=Artisan: PASSED")

error = validate_temperament_claim(wrong_temp, ref)
if error:
    print(f"   ✅ CAUGHT: ESTP=Guardian (wrong)")
    print(f"      Error: {error}")
else:
    print(f"   ❌ MISSED: ESTP=Guardian should have failed!")

print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("\nAll critical tests completed. Review results above.")
print("If all tests show ✅, your validation script is working correctly.")
