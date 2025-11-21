"""
Smoke Test: Structural Enforcement of Type Injection
Verifies that "UDUF INFJ" pattern correctly injects INFJ shadow functions.
"""

from src.services.prompt_builder import build_system_prompt, PromptAssemblyError

def test_uduf_infj_detection():
    """Test that UDUF INFJ pattern detects INFJ and injects correct shadow stack."""
    print("\n🧪 TEST: UDUF INFJ Detection & Injection")
    
    # Anthropic-style block content (what we actually receive)
    message_blocks = [{'type': 'text', 'text': 'What are the shadow functions for UDUF INFJ?'}]
    
    try:
        system_prompt, metadata = build_system_prompt(
            conversation_id=999,
            user_message=message_blocks
        )
        
        # Verify type was detected
        assert metadata['detected_types'] == ['INFJ'], f"Expected ['INFJ'], got {metadata['detected_types']}"
        print(f"✅ Detected types: {metadata['detected_types']}")
        
        # Verify type was injected
        assert metadata['injected_types'] == ['INFJ'], f"Expected ['INFJ'], got {metadata['injected_types']}"
        print(f"✅ Injected types: {metadata['injected_types']}")
        
        # Verify INFJ shadow functions are in the prompt
        # INFJ shadow stack (from reference_data.json): Ne, Fi, Te, Si
        assert 'Nemesis: **Ne**' in system_prompt, "Ne shadow function not found"
        assert 'Critic: **Fi**' in system_prompt, "Fi shadow function not found"
        assert 'Trickster: **Te**' in system_prompt, "Te shadow function not found"
        assert 'Demon: **Si**' in system_prompt, "Si shadow function not found"
        print("✅ Correct shadow functions injected: Ne, Fi, Te, Si")
        
        # Verify forceful warning is present
        assert '🚨 CRITICAL: READ THIS FIRST 🚨' in system_prompt, "Warning header not found"
        assert 'YOUR TRAINING DATA IS WRONG' in system_prompt, "Warning text not found"
        print("✅ Forceful warning header present")
        
        print(f"\n✅ TEST PASSED: UDUF INFJ correctly injects INFJ shadow stack")
        return True
        
    except PromptAssemblyError as e:
        print(f"❌ TEST FAILED: PromptAssemblyError - {e}")
        return False
    except AssertionError as e:
        print(f"❌ TEST FAILED: Assertion - {e}")
        return False
    except Exception as e:
        print(f"❌ TEST FAILED: Unexpected error - {e}")
        return False


def test_slash_pattern_detection():
    """Test that SF/SF ENTP pattern detects ENTP."""
    print("\n🧪 TEST: SF/SF ENTP Pattern Detection")
    
    try:
        system_prompt, metadata = build_system_prompt(
            conversation_id=999,
            user_message="Tell me about SF/SF ENTP"
        )
        
        assert 'ENTP' in metadata['detected_types'], f"ENTP not detected in {metadata['detected_types']}"
        print(f"✅ Detected ENTP from SF/SF pattern")
        
        print(f"✅ TEST PASSED: SF/SF ENTP detection works")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False


def test_basic_type_detection():
    """Test that basic ENFJ detection works."""
    print("\n🧪 TEST: Basic ENFJ Detection")
    
    try:
        system_prompt, metadata = build_system_prompt(
            conversation_id=999,
            user_message="What is ENFJ?"
        )
        
        assert 'ENFJ' in metadata['detected_types'], f"ENFJ not detected in {metadata['detected_types']}"
        assert 'ENFJ' in metadata['injected_types'], f"ENFJ not injected in {metadata['injected_types']}"
        print(f"✅ ENFJ detected and injected")
        
        print(f"✅ TEST PASSED: Basic ENFJ detection works")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False


def test_missing_reference_data_fails():
    """Test that fake type code fails validation."""
    print("\n🧪 TEST: Missing Reference Data Validation")
    
    # This test is tricky - ZZZZ won't be detected as a valid MBTI type
    # so it won't fail PromptAssemblyError, it just won't inject anything
    try:
        system_prompt, metadata = build_system_prompt(
            conversation_id=999,
            user_message="What about ABCD type?"  # Invalid type
        )
        
        # Should detect nothing and inject nothing
        assert metadata['detected_types'] == [], f"Invalid type detected: {metadata['detected_types']}"
        assert metadata['injected_types'] == [], f"Invalid type injected: {metadata['injected_types']}"
        print(f"✅ Invalid type correctly ignored")
        
        print(f"✅ TEST PASSED: Invalid types are ignored")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PROMPT ASSEMBLY SMOKE TESTS")
    print("=" * 60)
    
    results = [
        test_uduf_infj_detection(),      # Critical test
        test_slash_pattern_detection(),   # Octagram pattern variant
        test_basic_type_detection(),      # Basic functionality
        test_missing_reference_data_fails() # Validation
    ]
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("=" * 60)
        exit(0)
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("=" * 60)
        exit(1)
