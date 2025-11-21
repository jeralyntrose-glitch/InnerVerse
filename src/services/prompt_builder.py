"""
Centralized Prompt Assembly System with Runtime Validation
Ensures reference data injection reaches Claude reliably.
"""

import re
import hashlib
from typing import Optional
from pathlib import Path
from .type_injection import load_reference_data, get_type_stack, format_stack_for_prompt, detect_types_in_message, normalize_message_content
from .conversation_context import ConversationContext

# Cache base template at module level to avoid disk IO on every request
_CACHED_BASE_TEMPLATE = None


class PromptAssemblyError(Exception):
    """Raised when prompt assembly fails validation."""
    pass


class PromptAssembly:
    """
    Builds and validates system prompts with all 3 layers:
    - Layer 1: v3.1 Octagram base template
    - Layer 2: Type stack injection (reference data)
    - Layer 3: Conversation context memory
    
    Guarantees reference data reaches Claude or fails fast.
    """
    
    def __init__(self, conversation_id: int, user_message: str):
        self.conversation_id = conversation_id
        self.user_message = user_message
        self.detected_types = []
        self.injected_types = []
        self.context = None
        self.final_prompt = None
        self.metadata = {}
        
    def build(self) -> str:
        """
        Build the complete system prompt with all layers.
        Returns final prompt string.
        Raises PromptAssemblyError if validation fails.
        """
        # Layer 1: Base v3.1 Octagram template
        base_template = self._load_base_template()
        
        # Layer 2: Type stack injection
        type_injection, detected, injected = self._build_type_injection()
        self.detected_types = detected
        self.injected_types = injected
        
        # Layer 3: Conversation context memory
        context_injection, context = self._build_context_injection()
        self.context = context
        
        # Assemble final prompt
        parts = [base_template]
        if type_injection:
            parts.append(type_injection)
        if context_injection:
            parts.append(context_injection)
            
        self.final_prompt = "\n\n".join(parts)
        
        # Validate
        self._validate()
        
        # Build metadata
        self._build_metadata()
        
        return self.final_prompt
    
    def _load_base_template(self) -> str:
        """Load v3.1 Octagram system prompt template (cached at module level)."""
        global _CACHED_BASE_TEMPLATE
        
        if _CACHED_BASE_TEMPLATE is None:
            template_path = Path(__file__).parent.parent.parent / 'SYSTEM_PROMPT_V3_1_OCTAGRAM.md'
            
            if not template_path.exists():
                raise PromptAssemblyError(f"Base template not found: {template_path}")
                
            with open(template_path, 'r') as f:
                content = f.read()
                
            # Strip markdown header if present
            if content.startswith('# '):
                content = '\n'.join(content.split('\n')[1:])
                
            _CACHED_BASE_TEMPLATE = content.strip()
            print(f"✅ [PROMPT BUILDER] Cached base template ({len(_CACHED_BASE_TEMPLATE)} chars)")
            
        return _CACHED_BASE_TEMPLATE
    
    def _detect_types_in_message(self, message: str) -> list[str]:
        """
        Detect MBTI types in message using shared detection logic.
        Delegates to type_injection.detect_types_in_message for consistency.
        """
        return detect_types_in_message(message)
    
    def _build_type_injection(self) -> tuple[str, list[str], list[str]]:
        """
        Build Layer 2 type injection.
        Returns: (injection_string, detected_types, injected_types)
        """
        # Normalize message content to handle Anthropic block arrays
        normalized_message = normalize_message_content(self.user_message)
        detected = self._detect_types_in_message(normalized_message)
        
        if not detected:
            return "", [], []
        
        print(f"🔍 [PROMPT BUILDER] Detected types: {detected}")
        
        # Load reference data
        reference_data = load_reference_data()
        
        # Build forceful injection header
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
        
        injected = []
        for type_code in detected:
            type_data = get_type_stack(type_code)
            if type_data:
                injection_parts.append(format_stack_for_prompt(type_data))
                injected.append(type_code)
            else:
                print(f"⚠️ [PROMPT BUILDER] No reference data for {type_code}")
        
        if not injected:
            return "", detected, []
            
        return "\n".join(injection_parts), detected, injected
    
    def _build_context_injection(self) -> tuple[str, Optional[ConversationContext]]:
        """
        Build Layer 3 conversation context memory.
        Returns: (injection_string, context_object)
        """
        try:
            from .conversation_context import update_context
            
            # Normalize message content to handle Anthropic block arrays
            normalized_message = normalize_message_content(self.user_message)
            
            # Extract and remember relationship context
            context = update_context(self.conversation_id, normalized_message)
            context_string = context.to_prompt_string()
            
            if context_string:
                print(f"🧠 [PROMPT BUILDER] Added conversation context")
                return context_string, context
            else:
                return "", context
                
        except Exception as e:
            print(f"⚠️ [PROMPT BUILDER] Context extraction failed: {e}")
            return "", None
    
    def _validate(self):
        """
        Runtime validation that injection succeeded.
        Fails fast if detected types weren't injected.
        """
        # Critical check: If types detected but not injected, fail
        missing = set(self.detected_types) - set(self.injected_types)
        if missing:
            error_msg = (
                f"VALIDATION FAILED: Detected types {list(missing)} but "
                f"reference data injection failed. Cannot guarantee Claude "
                f"will use correct function stacks."
            )
            print(f"❌ [PROMPT BUILDER] {error_msg}")
            raise PromptAssemblyError(error_msg)
        
        # Success logging
        if self.detected_types:
            print(f"✅ [PROMPT BUILDER] Validated: {len(self.injected_types)} types injected")
        
        # Check final prompt isn't empty
        if not self.final_prompt:
            raise PromptAssemblyError("Final prompt is empty")
        if len(self.final_prompt) < 100:
            raise PromptAssemblyError("Final prompt is too short")
    
    def _build_metadata(self):
        """Build diagnostic metadata for logging and debugging."""
        prompt_text = self.final_prompt or ""
        self.metadata = {
            'conversation_id': self.conversation_id,
            'detected_types': self.detected_types,
            'injected_types': self.injected_types,
            'context_present': self.context is not None,
            'prompt_length': len(prompt_text),
            'prompt_hash': hashlib.sha256(prompt_text.encode()).hexdigest()[:12],
            'has_type_injection': len(self.injected_types) > 0,
        }
    
    def get_metadata(self) -> dict:
        """Return diagnostic metadata."""
        return self.metadata
    
    def log_summary(self):
        """Log a summary of the prompt assembly."""
        meta = self.metadata
        print(f"📊 [PROMPT BUILDER] Summary:")
        print(f"   - Conversation: {meta['conversation_id']}")
        print(f"   - Detected types: {meta['detected_types']}")
        print(f"   - Injected types: {meta['injected_types']}")
        print(f"   - Context memory: {'Yes' if meta['context_present'] else 'No'}")
        print(f"   - Final length: {meta['prompt_length']} chars")
        print(f"   - Prompt hash: {meta['prompt_hash']}")


def build_system_prompt(conversation_id: int, user_message: str) -> tuple[str, dict]:
    """
    Convenience function to build and validate system prompt.
    
    Returns:
        (final_prompt, metadata)
        
    Raises:
        PromptAssemblyError if validation fails
    """
    assembly = PromptAssembly(conversation_id, user_message)
    final_prompt = assembly.build()
    assembly.log_summary()
    return final_prompt, assembly.get_metadata()
