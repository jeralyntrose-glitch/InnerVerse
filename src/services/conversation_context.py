"""
Layer 3: Conversation Context Memory

Automatically extracts and remembers relationship context across conversations.
Example: "I'm an ENFP and my partner is an INFJ" → remembers partner = INFJ throughout conversation
"""

from dataclasses import dataclass, field
from typing import Optional, Dict
import re

MBTI_TYPES = [
    "ESTJ", "ESTP", "ENTJ", "ENFJ", "ESFJ", "ESFP", "ENTP", "ENFP",
    "ISTJ", "ISTP", "INTJ", "INFJ", "ISFJ", "ISFP", "INTP", "INFP"
]

RELATIONSHIP_PATTERNS = {
    "user": [
        r"i'?m\s+an?\s+({types})",
        r"i\s+am\s+an?\s+({types})",
        r"as\s+an?\s+({types})",
        r"my\s+type\s+is\s+({types})",
        r"i'?m\s+({types})",
    ],
    "partner": [
        r"partner\s+is\s+an?\s+({types})",
        r"boyfriend\s+is\s+an?\s+({types})",
        r"girlfriend\s+is\s+an?\s+({types})",
        r"husband\s+is\s+an?\s+({types})",
        r"wife\s+is\s+an?\s+({types})",
        r"spouse\s+is\s+an?\s+({types})",
        r"dating\s+an?\s+({types})",
        r"married\s+to\s+an?\s+({types})",
        r"my\s+({types})\s+partner",
        r"my\s+({types})\s+boyfriend",
        r"my\s+({types})\s+girlfriend",
        r"my\s+({types})\s+husband",
        r"my\s+({types})\s+wife",
    ],
    "friend": [
        r"friend\s+is\s+an?\s+({types})",
        r"my\s+({types})\s+friend",
        r"best\s+friend\s+is\s+an?\s+({types})",
    ],
    "coworker": [
        r"coworker\s+is\s+an?\s+({types})",
        r"colleague\s+is\s+an?\s+({types})",
        r"boss\s+is\s+an?\s+({types})",
        r"manager\s+is\s+an?\s+({types})",
        r"my\s+({types})\s+boss",
        r"my\s+({types})\s+coworker",
    ],
    "parent": [
        r"mom\s+is\s+an?\s+({types})",
        r"dad\s+is\s+an?\s+({types})",
        r"mother\s+is\s+an?\s+({types})",
        r"father\s+is\s+an?\s+({types})",
        r"parent\s+is\s+an?\s+({types})",
        r"my\s+({types})\s+mom",
        r"my\s+({types})\s+dad",
    ],
    "sibling": [
        r"sister\s+is\s+an?\s+({types})",
        r"brother\s+is\s+an?\s+({types})",
        r"sibling\s+is\s+an?\s+({types})",
        r"my\s+({types})\s+sister",
        r"my\s+({types})\s+brother",
    ],
    "child": [
        r"son\s+is\s+an?\s+({types})",
        r"daughter\s+is\s+an?\s+({types})",
        r"kid\s+is\s+an?\s+({types})",
        r"child\s+is\s+an?\s+({types})",
        r"my\s+({types})\s+son",
        r"my\s+({types})\s+daughter",
    ],
}


@dataclass
class ConversationContext:
    """Stores relationship context for a conversation."""
    user_type: Optional[str] = None
    partner_type: Optional[str] = None
    friend_type: Optional[str] = None
    coworker_type: Optional[str] = None
    parent_type: Optional[str] = None
    sibling_type: Optional[str] = None
    child_type: Optional[str] = None
    other_types: Dict[str, str] = field(default_factory=dict)
    
    def to_prompt_string(self) -> str:
        """Convert context to string for prompt injection."""
        parts = []
        if self.user_type:
            parts.append(f"User is {self.user_type}")
        if self.partner_type:
            parts.append(f"Partner is {self.partner_type}")
        if self.friend_type:
            parts.append(f"Friend is {self.friend_type}")
        if self.coworker_type:
            parts.append(f"Coworker is {self.coworker_type}")
        if self.parent_type:
            parts.append(f"Parent is {self.parent_type}")
        if self.sibling_type:
            parts.append(f"Sibling is {self.sibling_type}")
        if self.child_type:
            parts.append(f"Child is {self.child_type}")
        for role, mbti in self.other_types.items():
            parts.append(f"{role.capitalize()} is {mbti}")
        
        if not parts:
            return ""
        return "**Conversation Context:** " + ". ".join(parts) + "."


def extract_context_from_message(message: str, existing_context: ConversationContext) -> ConversationContext:
    """Extract type mentions and update context."""
    message_lower = message.lower()
    types_pattern = "|".join(MBTI_TYPES)
    
    for relationship, patterns in RELATIONSHIP_PATTERNS.items():
        for pattern in patterns:
            regex = pattern.format(types=types_pattern)
            match = re.search(regex, message_lower, re.IGNORECASE)
            if match:
                found_type = match.group(1).upper()
                if relationship == "user":
                    existing_context.user_type = found_type
                elif relationship == "partner":
                    existing_context.partner_type = found_type
                elif relationship == "friend":
                    existing_context.friend_type = found_type
                elif relationship == "coworker":
                    existing_context.coworker_type = found_type
                elif relationship == "parent":
                    existing_context.parent_type = found_type
                elif relationship == "sibling":
                    existing_context.sibling_type = found_type
                elif relationship == "child":
                    existing_context.child_type = found_type
    
    return existing_context


session_contexts: Dict[int, ConversationContext] = {}


def get_or_create_context(conversation_id: int) -> ConversationContext:
    """Get existing context or create new one for conversation."""
    if conversation_id not in session_contexts:
        session_contexts[conversation_id] = ConversationContext()
    return session_contexts[conversation_id]


def update_context(conversation_id: int, message: str) -> ConversationContext:
    """Update context based on new message."""
    context = get_or_create_context(conversation_id)
    return extract_context_from_message(message, context)


def clear_context(conversation_id: int):
    """Clear context for a conversation."""
    if conversation_id in session_contexts:
        del session_contexts[conversation_id]
