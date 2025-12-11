"""
Bulletproof Q&A Training Pipeline
Enterprise-Grade System for CS Joseph Content

3-Step Pipeline:
1. Extract facts with quotes (Haiku, temp=0)
2. Validate facts against reference (Haiku, temp=0)
3. Generate Q&A from facts only (Sonnet, temp=0)

This prevents Claude from inventing content by separating extraction, validation, and generation.
"""

import anthropic
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from fuzzywuzzy import fuzz

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

EXTRACTION_MODEL = "claude-3-haiku-20240307"  # Dumber = more literal
VALIDATION_MODEL = "claude-3-haiku-20240307"  # Dumber = more literal
GENERATION_MODEL = "claude-sonnet-4-5-20250929"  # Smarter for generation
TEMPERATURE = 0  # No creativity - be literal
CHUNK_SIZE = 500  # words per chunk

# ═══════════════════════════════════════════════════════════════════════════════
# CSJ CONTEXT - INCLUDED IN EVERY PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

CSJ_CONTEXT = """
═══════════════════════════════════════════════════════════════════
MISSION CONTEXT - READ BEFORE DOING ANYTHING
═══════════════════════════════════════════════════════════════════

You are working with CS Joseph's cognitive typology framework.

⚠️  CRITICAL: CSJ'S SYSTEM IS DIFFERENT FROM MAINSTREAM MBTI  ⚠️

Your training data contains mainstream MBTI information that is 
INCORRECT for this task. You must IGNORE what you "know" about 
personality types and ONLY use what is explicitly stated.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TERMINOLOGY DIFFERENCES (CSJ vs Mainstream)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| CSJ Term | WRONG Mainstream Term | Notes |
|----------|----------------------|-------|
| Hero | Dominant | NOT the same concept |
| Parent | Auxiliary | NOT the same concept |
| Child | Tertiary | NOT the same concept |
| Inferior | Inferior | Similar but different nuance |
| Nemesis | - | Shadow function, no mainstream equivalent |
| Critic | - | Shadow function, no mainstream equivalent |
| Trickster | - | Shadow function, no mainstream equivalent |
| Demon | - | Shadow function, no mainstream equivalent |
| Optimistic | - | Technical term about function attitude |
| Pessimistic | - | Technical term about function attitude |
| Four Sides of Mind | - | Ego, Subconscious, Unconscious, Superego |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMON MISTAKES YOU MUST NOT MAKE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ "Se users are athletic and love extreme sports" 
   → Generic MBTI stereotype, not CSJ teaching

❌ "Ni predicts the future"
   → Oversimplified, not how CSJ describes Ni

❌ "Feeling types are emotional, Thinking types are logical"
   → Mainstream nonsense, not CSJ

❌ "INFJs are rare and special"
   → Mainstream myth, not CSJ

❌ "The dominant function is the strongest"
   → Wrong framework entirely

❌ Adding behavioral examples not explicitly stated in content
   → If the content doesn't say it, you don't say it

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR MINDSET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are a TRANSCRIBER, not an interpreter.
You are LITERAL, not helpful.
You are CONSERVATIVE, not creative.

If something is not EXPLICITLY stated → It does not exist
If you're unsure → Leave it out
If you want to add context → DON'T

═══════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

FACT_EXTRACTION_PROMPT = CSJ_CONTEXT + """
═══════════════════════════════════════════════════════════════════
YOUR TASK: EXTRACT FACTS WITH EVIDENCE
═══════════════════════════════════════════════════════════════════

Extract every factual claim from the content below.

For EACH fact, you MUST include the exact quote from the content.

NO QUOTE = FACT DOESN'T EXIST

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ONLY extract claims EXPLICITLY stated in the content
2. Every fact MUST have a direct quote as evidence
3. Do NOT interpret, infer, or add anything
4. Do NOT use your training knowledge
5. If you can't find a quote to support it, don't include it
6. Preserve exact terminology (Hero, Parent, Child, etc.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FACT: [The factual claim]
QUOTE: "[Exact words from the content that prove this]"

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OF GOOD EXTRACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Content: "The Hero function operates optimistically. It's always on, running 
at full speed. Se Heroes react immediately to their environment."

FACT: The Hero function operates optimistically
QUOTE: "The Hero function operates optimistically"

---

FACT: The Hero function is always on and runs at full speed
QUOTE: "It's always on, running at full speed"

---

FACT: Se Heroes react immediately to their environment
QUOTE: "Se Heroes react immediately to their environment"

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OF BAD EXTRACTION (DO NOT DO THIS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Content: "The Hero function operates optimistically."

❌ BAD:
FACT: The Hero function is the strongest and most developed function
QUOTE: "The Hero function operates optimistically"
→ WRONG: "strongest and most developed" is NOT in the quote

❌ BAD:
FACT: Se Heroes are athletic and love physical activities  
QUOTE: [none provided]
→ WRONG: This is generic MBTI, not stated in content

❌ BAD:
FACT: The Hero, also known as the dominant function, is optimistic
QUOTE: "The Hero function operates optimistically"
→ WRONG: "dominant function" is NOT in the content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTENT TO EXTRACT FROM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extract all facts with quotes now. Output ONLY in the format shown above:
"""

FACT_VALIDATION_PROMPT = CSJ_CONTEXT + """
═══════════════════════════════════════════════════════════════════
YOUR TASK: VALIDATE FACTS AGAINST REFERENCE
═══════════════════════════════════════════════════════════════════

Check each extracted fact against the authoritative reference.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSITION DEFINITIONS (Use these to verify facts):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Hero (1st): Optimistic, always on, highest strength, "saves the world"
- Parent (2nd): Pessimistic, responsible, protective, "cleans up Hero's mess"
- Child (3rd): Optimistic, innocent, playful, "divine child"
- Inferior (4th): Pessimistic, fears, insecurities, gateway to subconscious
- Nemesis (5th): Worry about others, shadow of Hero
- Critic (6th): Self-criticism AND wisdom, pessimistic
- Trickster (7th): Blind spot, unaware, deceptive
- Demon (8th): Lowest awareness, sinful nature, gateway to superego

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ VALID - Fact matches reference exactly
❌ INVALID - Fact contradicts reference (explain why)
⚠️ UNVERIFIED - Fact is not covered by reference (KEEP IT)

IMPORTANT: UNVERIFIED facts are okay! The reference doesn't cover 
everything CSJ teaches. If the fact has a valid quote and doesn't 
contradict the reference, mark it UNVERIFIED and keep it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL VERIFICATION RULES (CHECK THESE FIRST - ZERO TOLERANCE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMMEDIATELY REJECT (❌ INVALID) ANY FACT THAT SAYS:

❌ "child" + ("fears" OR "insecurities" OR "insecure" OR "pessimistic")
   → WRONG: Child = optimistic/innocent. Fears = inferior position.

❌ "inferior" + ("innocent" OR "innocence" OR "optimistic" OR "divine")
   → WRONG: Inferior = pessimistic/fears. Innocent = child position.

❌ "hero" + ("pessimistic" OR "fears" OR "insecure")
   → WRONG: Hero = optimistic. Pessimistic = parent or inferior.

❌ "child represents fears" OR "child = fears" OR "child is fears"
   → WRONG: This is ALWAYS false. Child NEVER represents fears.

❌ "[FUNCTION] child = fears/insecurities"
   → WRONG: Regardless of function (Ni, Se, etc.), child position = innocent, not fears.

PATTERN MATCHING (Be strict):
- If you see ANY mention of "child" AND ("fear" OR "insecure") in the same sentence → ❌ INVALID
- If you see ANY mention of "inferior" AND ("innocent" OR "optimistic") in the same sentence → ❌ INVALID
- Don't be lenient - if it contradicts position definitions, it's wrong.

POSITION/ATTITUDE MATRIX (Use this to verify):
┌──────────┬─────────────┬─────────────────────────────┐
│ Position │   Attitude  │      Attributes             │
├──────────┼─────────────┼─────────────────────────────┤
│ Hero     │ Optimistic  │ Strength, comfort, always on│
│ Parent   │ Pessimistic │ Responsibility, criticism   │
│ Child    │ Optimistic  │ Innocence, divine, playful  │
│ Inferior │ Pessimistic │ Fears, insecurities, gateway│
└──────────┴─────────────┴─────────────────────────────┘

If a fact violates this matrix → ❌ INVALID (explain which position should have that attribute)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDITIONAL VERIFICATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. If fact says "[TYPE] excels at [FUNCTION]" → Check if that function is Hero or Parent for that type

3. If fact mentions a position → Verify the attribute matches the definitions above

4. Cross-reference ALL type claims against the function stacks in the reference JSON

5. Even if the source transcript says something wrong, REJECT IT if it contradicts the reference

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTHORITATIVE REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{reference_data}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FACTS TO VALIDATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{extracted_facts}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Validate each fact. Output format:

FACT: [original fact]
STATUS: ✅ VALID | ❌ INVALID | ⚠️ UNVERIFIED
REASON: [if invalid, explain what's wrong]

---

"""

QA_GENERATION_PROMPT = CSJ_CONTEXT + """
═══════════════════════════════════════════════════════════════════
YOUR TASK: GENERATE Q&A PAIRS FROM FACTS ONLY
═══════════════════════════════════════════════════════════════════

Generate Q&A training pairs using ONLY the facts provided below.

⚠️  YOU DO NOT HAVE ACCESS TO THE ORIGINAL CONTENT  ⚠️
⚠️  THE FACT LIST IS YOUR ONLY SOURCE OF TRUTH  ⚠️

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. You may ONLY use information from the VALIDATED FACTS below
2. If a claim is not in the fact list, it DOES NOT EXIST
3. Do NOT add context, examples, or elaboration from your training
4. Do NOT combine facts to create new claims not explicitly stated
5. Keep answers focused on what the facts actually say

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICE REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sound like a knowledgeable expert, NOT a textbook:

✅ GOOD: "The Hero function is optimistic - it's always on, running full 
speed. That's why Se Heroes react immediately to their environment."

❌ BAD: "According to the framework, the Hero function might be described 
as operating in an optimistic manner, which could potentially mean..."

- Be direct and confident
- No hedging (might, perhaps, potentially, could)
- No citations (CS Joseph says, according to, the material states)
- No source references (in this video, in season 4)
- Natural conversational tone

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANSWER LENGTH & DEPTH (CRITICAL - NOT OPTIONAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ SINGLE-SENTENCE ANSWERS ARE REJECTED ⚠️

MANDATORY REQUIREMENTS:
- EVERY answer MUST be minimum 2-3 sentences (3+ sentences preferred)
- EVERY answer MUST include the "so what" - why does this matter?
- EVERY answer MUST add practical implications or real-world application
- Connect concepts when facts are related - show relationships between ideas

If a fact doesn't have enough depth to create 2-3 sentences, either:
1. Combine related facts to create richer answers
2. Add the practical "so what" - what does this mean for someone's life?
3. Show the relationship to other concepts mentioned in the facts

❌ REJECTED - TOO SHORT:
"The Hero function is optimistic."

"The Hero function is always on, running at full speed - there's no off switch for your Hero."

"Se Heroes react immediately to their environment."

✅ REQUIRED - GOOD LENGTH:
"The Hero function is optimistic - it's always on, running at full speed with no off switch. Your Hero is out there trying to save the world, but it causes collateral damage in the process. That's why the Parent function exists: to clean up the mess and protect others from the Hero's chaos. This dynamic explains why people can feel unstoppable when their Hero is engaged, but also why they might leave destruction in their wake."

"Se Heroes react immediately to their environment - they're tuned into the physical world like a radio picking up signals. That instant reactivity is the Se Hero in action, responding in real-time to what's happening around them. This means ESTPs and ESFPs are always in the moment, which gives them incredible adaptability but can also make them impulsive. Understanding this helps explain why they seem to 'just know' what to do in chaotic situations - their Hero is processing the environment faster than conscious thought."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OF GOOD Q&A (based on sample facts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Given facts:
- Hero function operates optimistically
- Hero function is always on, running at full speed
- Se Heroes react immediately to their environment

✅ GOOD Q&A:

{{"messages": [{{"role": "user", "content": "How does the Hero function operate?"}}, {{"role": "assistant", "content": "The Hero function operates optimistically. It's always on, running at full speed - there's no off switch for your Hero."}}]}}

{{"messages": [{{"role": "user", "content": "How do Se Heroes respond to their surroundings?"}}, {{"role": "assistant", "content": "Se Heroes react immediately to their environment. That instant reactivity is the Se Hero in action."}}]}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE OF BAD Q&A (DO NOT DO THIS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Given the SAME facts above:

❌ BAD Q&A:

{{"messages": [{{"role": "user", "content": "What are Se Heroes good at?"}}, {{"role": "assistant", "content": "Se Heroes are great at sports, physical activities, and hands-on work. They're often athletic and love being in the moment."}}]}}

→ WRONG: None of this is in the fact list. This is generic MBTI garbage.

❌ BAD Q&A:

{{"messages": [{{"role": "user", "content": "How does the Hero function work?"}}, {{"role": "assistant", "content": "The Hero function, also called the dominant function, is your strongest cognitive function. It operates optimistically and is always on."}}]}}

→ WRONG: "dominant function" and "strongest" are NOT in the facts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JSON FORMAT - EXACT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each pair on its own line, valid JSON:

{{"messages": [{{"role": "user", "content": "question"}}, {{"role": "assistant", "content": "answer"}}]}}

- Double quotes for ALL strings
- No trailing commas
- No markdown
- No explanations before or after

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATED FACTS (YOUR ONLY SOURCE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{validated_facts}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate EXACTLY 8-12 Q&A pairs (no more, no less). Output ONLY valid JSON lines:
"""

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def chunk_content(content: str, max_words: int = CHUNK_SIZE) -> List[str]:
    """Split content into small chunks to reduce blending opportunity"""
    words = content.split()
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunk = ' '.join(words[i:i + max_words])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks


def format_reference_for_prompt(ref_data: dict) -> str:
    """
    Format reference data as JSON string for inclusion in prompts.
    
    This is used by the validation step to check facts against reference.
    """
    return json.dumps(ref_data, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: EXTRACT FACTS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_facts(client: anthropic.Anthropic, content: str, log_api_usage_fn=None) -> List[Dict[str, str]]:
    """
    Extract facts with quotes from content using Haiku (dumber = more literal).
    
    Returns list of dicts with 'fact' and 'quote' keys.
    Includes quote verification to prevent prompt example leakage.
    """
    prompt = FACT_EXTRACTION_PROMPT.format(content=content)
    
    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=4000,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text
        
        # Log API usage if function provided
        if log_api_usage_fn:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            # Haiku pricing: $0.25/1M input, $1.25/1M output
            cost = (input_tokens * 0.25 / 1000000) + (output_tokens * 1.25 / 1000000)
            log_api_usage_fn("training_fact_extraction", EXTRACTION_MODEL, input_tokens, output_tokens, cost)
        
        parsed_facts = parse_extracted_facts(response_text)
        
        # CRITICAL: Verify quotes actually exist in source content
        # This prevents prompt example leakage where Claude extracts 
        # facts from the example section instead of actual content
        verified_facts = verify_quotes_in_source(parsed_facts, content)
        
        return verified_facts
        
    except Exception as e:
        print(f"   ❌ Fact extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def parse_extracted_facts(response: str) -> List[Dict[str, str]]:
    """Parse FACT/QUOTE pairs from extraction response"""
    facts = []
    current_fact = None
    current_quote = None
    
    for line in response.strip().split('\n'):
        line = line.strip()
        
        if line.startswith('FACT:'):
            # Save previous fact if exists
            if current_fact and current_quote:
                facts.append({
                    'fact': current_fact,
                    'quote': current_quote
                })
            current_fact = line[5:].strip()
            current_quote = None
            
        elif line.startswith('QUOTE:'):
            # Remove QUOTE: prefix and strip quotes
            quote_text = line[6:].strip()
            # Remove surrounding quotes if present
            if quote_text.startswith('"') and quote_text.endswith('"'):
                quote_text = quote_text[1:-1]
            elif quote_text.startswith("'") and quote_text.endswith("'"):
                quote_text = quote_text[1:-1]
            current_quote = quote_text
            
        elif line == '---':
            # Delimiter - save current fact if exists
            if current_fact and current_quote:
                facts.append({
                    'fact': current_fact,
                    'quote': current_quote
                })
            current_fact = None
            current_quote = None
    
    # Don't forget last one
    if current_fact and current_quote:
        facts.append({
            'fact': current_fact,
            'quote': current_quote
        })
    
    return facts


def verify_quotes_in_source(facts: List[Dict[str, str]], source_content: str, threshold: int = 70) -> List[Dict[str, str]]:
    """
    Filter facts by verifying their quotes actually exist in source content.
    
    Uses fuzzy matching to handle minor transcription differences.
    This prevents prompt example leakage - if a quote doesn't exist in the 
    actual source content, the fact is rejected.
    
    Args:
        facts: List of dicts with 'fact' and 'quote' keys
        source_content: Original content that was sent for extraction
        threshold: Minimum fuzzy match score (0-100) to accept quote
        
    Returns:
        Filtered list of facts where quotes were verified in source
    """
    if not facts:
        return []
    
    verified_facts = []
    source_lower = source_content.lower()
    
    for fact_item in facts:
        quote = fact_item.get('quote', '')
        if not quote:
            continue
            
        quote_lower = quote.lower()
        
        if quote_lower in source_lower:
            verified_facts.append(fact_item)
        else:
            score = fuzz.partial_ratio(quote_lower, source_lower)
            if score >= threshold:
                verified_facts.append(fact_item)
            else:
                print(f"   ⚠️ Quote not found in source (score={score}): \"{quote[:60]}...\"")
    
    if len(verified_facts) < len(facts):
        print(f"   🔍 Quote verification: {len(verified_facts)}/{len(facts)} facts verified in source")
    
    return verified_facts


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: VALIDATE FACTS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_facts(
    client: anthropic.Anthropic, 
    facts: List[Dict[str, str]], 
    reference_data: dict,
    log_api_usage_fn=None
) -> Dict[str, List[Dict[str, str]]]:
    """Validate facts against reference data using Haiku"""
    
    # Format facts for prompt
    facts_text = "\n".join([
        f"FACT: {f['fact']}\nQUOTE: \"{f['quote']}\"\n---"
        for f in facts
    ])
    
    prompt = FACT_VALIDATION_PROMPT.format(
        reference_data=format_reference_for_prompt(reference_data),
        extracted_facts=facts_text
    )
    
    try:
        response = client.messages.create(
            model=VALIDATION_MODEL,
            max_tokens=4000,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text
        
        # Log API usage if function provided
        if log_api_usage_fn:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            # Haiku pricing: $0.25/1M input, $1.25/1M output
            cost = (input_tokens * 0.25 / 1000000) + (output_tokens * 1.25 / 1000000)
            log_api_usage_fn("training_fact_validation", VALIDATION_MODEL, input_tokens, output_tokens, cost)
        
        return parse_validation_response(response_text, facts)
        
    except Exception as e:
        print(f"   ❌ Fact validation error: {str(e)}")
        import traceback
        traceback.print_exc()
        # On error, mark all as unverified (conservative approach)
        return {
            'valid': [],
            'invalid': [],
            'unverified': facts
        }


def parse_validation_response(response: str, original_facts: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Parse validation results into valid/invalid/unverified lists"""
    valid = []
    invalid = []
    unverified = []
    
    current_fact = None
    
    for line in response.strip().split('\n'):
        line = line.strip()
        
        if line.startswith('FACT:'):
            current_fact = line[5:].strip()
            
        elif line.startswith('STATUS:'):
            status_line = line[7:].strip().upper()
            
            if current_fact:
                # Find matching fact in original list
                fact_obj = next(
                    (f for f in original_facts if f['fact'] == current_fact),
                    None
                )
                
                if not fact_obj:
                    # Fact not found, skip
                    continue
                
                if 'INVALID' in status_line and 'VALID' not in status_line:
                    invalid.append(fact_obj)
                elif 'UNVERIFIED' in status_line:
                    unverified.append(fact_obj)
                elif 'VALID' in status_line:
                    valid.append(fact_obj)
    
    # Any facts not found in validation response are marked unverified (conservative)
    validated_fact_texts = {f['fact'] for f in valid + invalid + unverified}
    for fact_obj in original_facts:
        if fact_obj['fact'] not in validated_fact_texts:
            unverified.append(fact_obj)
    
    return {
        'valid': valid,
        'invalid': invalid,
        'unverified': unverified
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: GENERATE Q&A
# ═══════════════════════════════════════════════════════════════════════════════

def generate_qa_from_facts(
    client: anthropic.Anthropic, 
    facts: List[Dict[str, str]],
    parse_qa_response_fn,
    log_api_usage_fn=None
) -> List[Dict]:
    """
    Generate Q&A pairs from validated facts ONLY - Claude never sees PDF.
    
    Args:
        client: Anthropic client
        facts: List of validated facts (dicts with 'fact' and 'quote' keys)
        parse_qa_response_fn: Function to parse Q&A response (imported from main.py)
        log_api_usage_fn: Optional function to log API usage
    
    Returns:
        List of Q&A pair dicts in OpenAI fine-tuning format
    """
    
    # Format facts for prompt - just the fact statements, not quotes
    facts_text = "\n".join([f"- {f['fact']}" for f in facts])
    
    prompt = QA_GENERATION_PROMPT.format(validated_facts=facts_text)
    
    try:
        response = client.messages.create(
            model=GENERATION_MODEL,
            max_tokens=4000,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text
        
        # Log API usage if function provided
        if log_api_usage_fn:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            # Sonnet 3.5 pricing: $3/1M input, $15/1M output
            cost = (input_tokens * 3.0 / 1000000) + (output_tokens * 15.0 / 1000000)
            log_api_usage_fn("training_qa_generation", GENERATION_MODEL, input_tokens, output_tokens, cost)
        
        # Use the imported parse function
        return parse_qa_response_fn(response_text)
        
    except Exception as e:
        print(f"   ❌ Q&A generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOMATIC CONTRADICTION FILTER
# ═══════════════════════════════════════════════════════════════════════════════

def filter_contradictions(pairs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Automatically filter out Q&A pairs with position/attitude contradictions.
    
    Returns:
        Tuple of (filtered_pairs, rejected_pairs_with_reasons)
    """
    import re
    
    # Contradiction patterns (same as scan_contradictions.py)
    contradiction_patterns = [
        (r'(child|3rd).*(fear|fears|insecurity|insecurities|pessimistic|worr)', 
         'Child position should be optimistic/innocent, not fears/insecurities'),
        (r'(inferior|4th).*(innocent|innocence|optimistic|divine|playful)', 
         'Inferior position should be pessimistic/fears, not innocent/optimistic'),
        (r'(hero|1st|dominant).*(pessimistic|fear|fears|insecurity|worr)', 
         'Hero position should be optimistic, not pessimistic/fears'),
        (r'child.*represents.*(fear|fears|insecurity)', 
         'Child never represents fears - that is the inferior'),
        (r'inferior.*represents.*(innocent|innocence|divine)', 
         'Inferior never represents innocence - that is the child'),
    ]
    
    filtered_pairs = []
    rejected_pairs = []
    
    for pair in pairs:
        if 'messages' not in pair or len(pair['messages']) < 2:
            continue
        
        question = pair['messages'][0].get('content', '')
        answer = pair['messages'][1].get('content', '')
        text_to_scan = f"{question} {answer}".lower()
        
        # Check for contradictions
        has_contradiction = False
        rejection_reason = None
        
        for pattern, explanation in contradiction_patterns:
            if re.search(pattern, text_to_scan, re.IGNORECASE):
                has_contradiction = True
                rejection_reason = explanation
                break
        
        if has_contradiction:
            rejected_pairs.append({
                'pair': pair,
                'reason': rejection_reason
            })
        else:
            filtered_pairs.append(pair)
    
    return filtered_pairs, rejected_pairs

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_bulletproof_pipeline(
    content: str,
    reference_data: dict,
    api_key: str,
    parse_qa_response_fn,
    log_api_usage_fn=None
) -> Dict[str, Any]:
    """
    Run the complete bulletproof pipeline:
    Content → Chunk → Extract Facts → Validate → Generate Q&A
    
    Args:
        content: Full text content to process
        reference_data: Reference data dict for validation
        api_key: Anthropic API key
        parse_qa_response_fn: Function to parse Q&A response (from main.py)
        log_api_usage_fn: Optional function to log API usage
    
    Returns:
        Dict with:
        - 'facts': List of all extracted facts
        - 'validation': Dict with 'valid', 'invalid', 'unverified' lists
        - 'pairs': List of Q&A pairs in fine-tuning format
    """
    
    client = anthropic.Anthropic(api_key=api_key)
    
    all_pairs = []
    all_facts = []
    all_validation = {'valid': [], 'invalid': [], 'unverified': []}
    
    # Chunk the content (500 words max)
    chunks = chunk_content(content)
    print(f"📄 Processing {len(chunks)} chunks (500 words each)...")
    
    for i, chunk in enumerate(chunks):
        print(f"\n━━━ Chunk {i+1}/{len(chunks)} ━━━")
        
        # Step 1: Extract facts with quotes
        print("  🔍 Step 1: Extracting facts...")
        facts = extract_facts(client, chunk, log_api_usage_fn)
        print(f"     → Extracted {len(facts)} facts with quotes")
        all_facts.extend(facts)
        
        if not facts:
            print("     → No facts found, skipping chunk")
            continue
        
        # Step 2: Validate against reference
        print("  ✓ Step 2: Validating facts...")
        validation = validate_facts(client, facts, reference_data, log_api_usage_fn)
        print(f"     → ✅ Valid: {len(validation['valid'])}")
        print(f"     → ❌ Invalid: {len(validation['invalid'])}")
        print(f"     → ⚠️ Unverified: {len(validation['unverified'])}")
        
        all_validation['valid'].extend(validation['valid'])
        all_validation['invalid'].extend(validation['invalid'])
        all_validation['unverified'].extend(validation['unverified'])
        
        # Step 3: Generate Q&A from valid + unverified facts only
        usable_facts = validation['valid'] + validation['unverified']
        
        if not usable_facts:
            print("     → No usable facts, skipping Q&A generation")
            continue
        
        print(f"  📝 Step 3: Generating Q&A from {len(usable_facts)} facts...")
        pairs = generate_qa_from_facts(client, usable_facts, parse_qa_response_fn, log_api_usage_fn)
        print(f"     → Generated {len(pairs)} Q&A pairs")
        all_pairs.extend(pairs)
    
    # Step 4: Automatic contradiction filtering
    print(f"\n  🔍 Step 4: Filtering contradictions...")
    filtered_pairs, rejected_pairs = filter_contradictions(all_pairs)
    contradictions_removed = len(rejected_pairs)
    
    if contradictions_removed > 0:
        print(f"     → ❌ Removed {contradictions_removed} pairs with contradictions")
        for rejected in rejected_pairs[:3]:  # Show first 3
            question_preview = rejected['pair']['messages'][0]['content'][:60]
            print(f"        - Rejected: {question_preview}... ({rejected['reason']})")
        if contradictions_removed > 3:
            print(f"        ... and {contradictions_removed - 3} more")
    else:
        print(f"     → ✅ No contradictions found")
    
    # Deduplicate pairs by question (case-insensitive, normalized)
    seen_questions = set()
    deduplicated_pairs = []
    duplicates_removed = 0
    
    for pair in filtered_pairs:
        if 'messages' in pair and len(pair['messages']) >= 2:
            question = pair['messages'][0].get('content', '').strip().lower()
            # Normalize: remove extra whitespace, punctuation differences
            question_normalized = ' '.join(question.split())
            
            if question_normalized and question_normalized not in seen_questions:
                seen_questions.add(question_normalized)
                deduplicated_pairs.append(pair)
            else:
                duplicates_removed += 1
    
    # Summary
    print(f"\n{'═'*50}")
    print(f"✅ PIPELINE COMPLETE")
    print(f"{'═'*50}")
    print(f"Total facts extracted: {len(all_facts)}")
    print(f"  ├─ Valid: {len(all_validation['valid'])}")
    print(f"  ├─ Invalid: {len(all_validation['invalid'])}")
    print(f"  └─ Unverified: {len(all_validation['unverified'])}")
    print(f"Total Q&A pairs generated: {len(all_pairs)}")
    if contradictions_removed > 0:
        print(f"  ├─ Contradictions removed: {contradictions_removed}")
    if duplicates_removed > 0:
        print(f"  └─ Duplicates removed: {duplicates_removed}")
    
    # Cap total pairs at 50 (keep top 50 most diverse/relevant)
    MAX_PAIRS_PER_FILE = 50
    final_pairs = deduplicated_pairs
    pairs_capped = False
    
    if len(deduplicated_pairs) > MAX_PAIRS_PER_FILE:
        # Keep first 50 pairs (they're generated in order of importance)
        final_pairs = deduplicated_pairs[:MAX_PAIRS_PER_FILE]
        pairs_capped = True
    
    if pairs_capped:
        print(f"  └─ Capped at {MAX_PAIRS_PER_FILE} pairs (was {len(deduplicated_pairs)})")
    print(f"Final Q&A pairs: {len(final_pairs)}")
    
    return {
        'facts': all_facts,
        'validation': all_validation,
        'pairs': final_pairs,
        'rejected_contradictions': rejected_pairs
    }

