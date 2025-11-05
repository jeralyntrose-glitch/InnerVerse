"""
Test Concept Extraction with Sample MBTI Documents
"""

import asyncio
import json
from src.services.concept_extractor import extract_concepts, get_extraction_cost_summary

# Sample documents for testing

# SHORT DOCUMENT (~5k chars)
SHORT_DOC = """
Shadow Integration in MBTI and Jungian Psychology

Shadow integration is a foundational process in Jungian psychology and MBTI type development. 
It involves recognizing, understanding, and incorporating the unconscious aspects of the psyche,
particularly the inferior function and shadow functions.

The Inferior Function represents the least developed of the four cognitive functions in one's
function stack. For example, an INTJ has Introverted Intuition (Ni) as their dominant function
and Extraverted Sensing (Se) as their inferior function. The inferior function operates unconsciously
and can cause stress when activated.

Shadow Functions are the four functions that exist outside of the primary function stack. These
include the opposing, critical parent, trickster, and demon functions. They represent rejected
or repressed aspects of personality that must be integrated for wholeness.

The Integration Process requires understanding several key concepts:

1. Cognitive Functions - The eight mental processes (Ti, Te, Fi, Fe, Ni, Ne, Si, Se) that form
the basis of personality type theory. Each person uses all eight but in different orders and 
with different levels of development.

2. Function Stack - The hierarchy of four primary functions that define a type's conscious 
processing. For INTJ: Ni-Te-Fi-Se.

3. Unconscious Shadow - The four shadow functions that mirror the ego functions but operate
in unconscious, often problematic ways. Understanding these leads to integration.

Shadow integration enables several outcomes:
- Greater self-awareness and psychological maturity
- Reduced projection onto others
- Access to the full range of cognitive capabilities
- Healing of psychological wounds and trauma

The process builds on understanding the cognitive functions and requires honest self-examination.
It contrasts with type development, which focuses only on strengthening the primary four functions.
Shadow work manifests as increased flexibility, empathy, and wholeness.

In CS Joseph's teaching framework, shadow integration is considered essential for advanced
type development and healthy relationships. It represents the difference between knowing one's
type intellectually versus living it with full awareness.
""".strip()

# MEDIUM DOCUMENT (~25k chars)
MEDIUM_DOC = """
The Four Sides of the Mind: A Comprehensive Framework

CS Joseph's Four Sides of the Mind model represents an advanced framework in Jungian psychology
and MBTI type theory. This model expands traditional type understanding by recognizing that
each person possesses not one, but four distinct cognitive orientations that activate in
different contexts.

The Ego (Primary Type)
The Ego represents the conscious, default mode of operation. It consists of the four primary
cognitive functions arranged in a specific hierarchy. For an INTJ, this would be:
1. Ni (Hero) - Introverted Intuition
2. Te (Parent) - Extraverted Thinking  
3. Fi (Child) - Introverted Feeling
4. Se (Inferior) - Extraverted Sensing

The Ego functions handle day-to-day decision-making and information processing. These are
the functions people identify with most strongly and use most consciously.

The Unconscious (Shadow)
The Unconscious consists of the four shadow functions that mirror the Ego but operate
unconsciously. These functions represent rejected or undeveloped aspects of personality.
For INTJ:
5. Ne (Opposing) - Extraverted Intuition
6. Ti (Critical Parent) - Introverted Thinking
7. Fe (Trickster) - Extraverted Feeling
8. Si (Demon) - Introverted Sensing

Shadow functions activate during stress, insecurity, or when the Ego fails to handle a situation.
They often manifest negatively until integrated through shadow work.

The Subconscious (Aspirational Type)
The Subconscious represents the type we aspire to become - our idealized self. It consists of
the complete inversion of the Ego function stack. For INTJ (Ni-Te-Fi-Se), the Subconscious
would be ESFP (Se-Fi-Te-Ni).

The Subconscious activates when:
- Around people we admire or feel attracted to
- In situations where we want to make a good impression
- When pursuing aspirational goals

Understanding the Subconscious helps explain:
- Who we find attractive (often our Subconscious type)
- What behaviors we aspire to develop
- Sources of insecurity and self-doubt

The Superego (Critical Type)
The Superego represents our critical, judging orientation. It emerges in response to criticism,
threat, or when defending our values. For INTJ, the Superego would be ENTP (Ne-Ti-Fe-Si).

The Superego manifests as:
- Internal criticism and self-judgment
- Critical evaluation of others
- Defensive reactions to perceived attacks
- Moral superiority or righteousness

Each side serves a purpose:
- Ego: Daily functioning and identity
- Unconscious: Growth through integration of shadow
- Subconscious: Aspiration and attraction
- Superego: Protection and judgment

Integration Across the Four Sides requires several prerequisite concepts:

Cognitive Functions Mastery
Before working with the Four Sides, one must understand the eight cognitive functions deeply.
Each function has specific characteristics, strengths, and weaknesses that manifest differently
depending on position in the stack.

Ti (Introverted Thinking) focuses on internal logical consistency and frameworks
Te (Extraverted Thinking) focuses on external efficiency and objective organization
Fi (Introverted Feeling) focuses on internal values and authenticity
Fe (Extraverted Feeling) focuses on external harmony and social appropriateness
Ni (Introverted Intuition) focuses on internal patterns and future implications
Ne (Extraverted Intuition) focuses on external possibilities and connections
Si (Introverted Sensing) focuses on internal sensory memory and tradition
Se (Extraverted Sensing) focuses on external sensory experience and aesthetics

Function Attitudes and Positions
Each function position carries specific attitudes and energies:
- Hero (1st): Confident, natural strength
- Parent (2nd): Responsible, mature application
- Child (3rd): Playful, joyful but immature
- Inferior (4th): Aspirational but stressful
- Opposing (5th): Oppositional, skeptical
- Critical Parent (6th): Critical, attacking
- Trickster (7th): Deceptive, double-binding
- Demon (8th): Destructive, most feared

Type Interaction Dynamics
The Four Sides framework enables understanding of complex relationship dynamics:
- We often pair with our Subconscious type (INTJ with ESFP)
- We clash with our Superego type (INTJ with ENTP)
- We need our Unconscious type for growth (INTJ needs ESFJ perspectives)

Developmental Stages
Development through the Four Sides follows a progression:
1. Ego Development - Strengthening primary functions
2. Shadow Integration - Incorporating unconscious functions
3. Subconscious Activation - Developing aspirational qualities
4. Superego Management - Healthy use of critical functions

The Complete Four Sides Model represents advanced type theory that builds upon:
- Traditional MBTI four-function stack understanding
- Jungian concepts of consciousness and unconsciousness
- Shadow psychology and integration work
- Beebe's eight-function model

This framework enables deeper self-understanding and more effective navigation of
relationships and personal growth. It contrasts with simplified type descriptions
by acknowledging the full complexity of human psychology while remaining grounded
in observable cognitive patterns.

Practical Applications include:
- Predicting relationship compatibility and challenges
- Understanding sources of stress and dysfunction
- Identifying paths for personal development
- Navigating career choices aligned with all four sides
- Improving communication across type differences

The Four Sides of the Mind represents CS Joseph's synthesis of multiple psychological
models into a comprehensive framework for understanding personality, relationships,
and human development.
""".strip()

# LONG DOCUMENT (~60k chars) - Will be truncated by preprocessing
LONG_DOC = """
Comprehensive Guide to Cognitive Functions and Type Development

PART 1: FOUNDATIONS OF COGNITIVE FUNCTIONS

The cognitive functions form the foundational framework of Jungian personality type theory
and MBTI. Unlike trait-based approaches that measure degrees of characteristics, cognitive
functions describe distinct mental processes used to perceive information and make decisions.

Historical Development
Carl Jung first identified the functions in Psychological Types (1921), describing four
fundamental mental processes:
- Thinking: Logical analysis and decision-making
- Feeling: Value-based judgment and decision-making  
- Sensing: Concrete perception of present reality
- Intuition: Abstract perception of patterns and possibilities

Jung recognized that each function could operate in two attitudes:
- Introverted: Oriented toward internal, subjective reality
- Extraverted: Oriented toward external, objective reality

This created eight distinct cognitive functions, though Jung himself didn't systematically
map out all eight in the way modern type theory does.

Isabel Briggs Myers and Katharine Cook Briggs developed the MBTI assessment based on Jung's
work, creating the four-letter type code system. However, they focused primarily on the
four dichotomies (E/I, S/N, T/F, J/P) rather than deeply exploring the eight functions.

John Beebe advanced function theory significantly in the 1990s by assigning archetypal
energies to each function position, creating the eight-function model used widely today.

CS Joseph has further refined and systematized function theory, particularly in areas of
type interactions, the Four Sides of the Mind, and developmental frameworks.

The Eight Cognitive Functions

Ti - Introverted Thinking
Introverted Thinking constructs internal frameworks of logical consistency. Ti users
care about whether ideas make sense within their own mental models, not whether they're
accepted externally. 

Key characteristics:
- Analyzes logical relationships and principles
- Builds precise internal definitions and categories
- Questions assumptions and seeks understanding
- Values intellectual independence and rigor
- Can appear pedantic or overly analytical

When healthy: Clear thinking, intellectual depth, principled consistency
When unhealthy: Paralysis by analysis, pedantry, social obliviousness

Types with Ti in Hero position: INTP, ISTP
Types with Ti in Parent position: ENTP, ESTP

Te - Extraverted Thinking  
Extraverted Thinking organizes external systems for efficiency and effectiveness. Te users
focus on what works objectively, implementing proven methods and structures.

Key characteristics:
- Prioritizes productivity and measurable results
- Uses objective standards and external metrics
- Implements systems and organizational structures
- Values efficiency and effectiveness
- Can appear impersonal or ruthlessly pragmatic

When healthy: Effective execution, practical achievement, organized systems
When unhealthy: Rigidity, insensitivity, blind adherence to systems

Types with Te in Hero position: ENTJ, ESTJ
Types with Te in Parent position: INTJ, ISTJ

Fi - Introverted Feeling
Introverted Feeling evaluates based on internal values and authenticity. Fi users have
deeply held personal values and judge everything against internal moral frameworks.

Key characteristics:
- Maintains strong personal values and principles  
- Seeks authenticity and genuine self-expression
- Evaluates alignment with internal moral compass
- Values individuality and personal integrity
- Can appear rigid or judgmental about values

When healthy: Moral clarity, authentic living, compassionate boundaries
When unhealthy: Self-righteousness, oversensitivity, martyrdom

Types with Fi in Hero position: INFP, ISFP
Types with Fi in Parent position: ENFP, ESFP

Fe - Extraverted Feeling
Extraverted Feeling creates harmony and manages group emotional dynamics. Fe users
prioritize social cohesion and collective emotional well-being.

Key characteristics:
- Manages group harmony and social atmosphere
- Reads and responds to others' emotional states
- Maintains social appropriateness and customs
- Values community and collective well-being
- Can appear manipulative or inauthentic

When healthy: Social grace, empathy, community building
When unhealthy: People-pleasing, manipulation, boundary violations

Types with Fe in Hero position: ENFJ, ESFJ  
Types with Fe in Parent position: INFJ, ISFJ

Ni - Introverted Intuition
Introverted Intuition perceives underlying patterns and future implications. Ni users
synthesize information into singular insights about how things will unfold.

Key characteristics:
- Synthesizes complex information into singular insights
- Perceives underlying patterns and trajectories
- Focuses on long-term implications and meaning
- Values depth and symbolic understanding
- Can appear mystical or overly abstract

When healthy: Visionary insight, strategic foresight, meaningful synthesis
When unhealthy: Tunnel vision, detachment from reality, mysticism

Types with Ni in Hero position: INTJ, INFJ
Types with Ni in Parent position: ENTJ, ENFJ

Ne - Extraverted Intuition
Extraverted Intuition perceives external possibilities and connections between ideas.
Ne users see potential everywhere and make novel associations.

Key characteristics:
- Perceives multiple possibilities and options
- Makes creative connections between ideas
- Explores potential and new perspectives
- Values innovation and brainstorming
- Can appear scattered or commitment-phobic

When healthy: Creative problem-solving, innovation, enthusiasm  
When unhealthy: Scattered focus, inability to commit, irresponsibility

Types with Ne in Hero position: ENTP, ENFP
Types with Ne in Parent position: INTP, INFP

Si - Introverted Sensing
Introverted Sensing recalls past sensory experiences and maintains continuity with
tradition. Si users value proven methods and detailed memory.

Key characteristics:
- Recalls detailed sensory memories and experiences
- Values tradition, routine, and proven methods
- Maintains continuity and stability
- Compares present to past experiences
- Can appear resistant to change or overly nostalgic

When healthy: Reliable memory, respect for tradition, attention to detail
When unhealthy: Rigidity, living in the past, resistance to growth

Types with Si in Hero position: ISTJ, ISFJ
Types with Si in Parent position: ESTJ, ESFJ

Se - Extraverted Sensing
Extraverted Sensing perceives immediate sensory reality and takes action in the present
moment. Se users excel at responding to current circumstances.

Key characteristics:
- Fully present in immediate sensory experience
- Responds quickly and effectively to current reality  
- Seeks stimulation and aesthetic experience
- Values physical mastery and performance
- Can appear impulsive or reckless

When healthy: Present-moment awareness, effective action, aesthetic appreciation
When unhealthy: Recklessness, addiction to stimulation, lack of foresight

Types with Se in Hero position: ESTP, ESFP
Types with Se in Parent position: ISTP, ISFP

PART 2: FUNCTION STACK DYNAMICS

The Function Stack Hierarchy
Each type's cognitive functions arrange in a specific order called the function stack.
This hierarchy determines how naturally and consciously each function operates.

The Eight Positions:
1. Hero (Dominant) - Most developed, used most consciously and confidently
2. Parent (Auxiliary) - Mature, responsible use to support the Hero
3. Child (Tertiary) - Joyful but immature, needs development
4. Inferior (Fourth) - Aspirational but stressful, gateway to unconscious
5. Opposing (Fifth) - Oppositional, skeptical version of the Hero
6. Critical Parent (Sixth) - Critical, attacking version of the Parent  
7. Trickster (Seventh) - Deceptive, double-binding version of the Child
8. Demon (Eighth) - Most destructive and feared version of the Inferior

Function Attitudes by Position
Each position carries specific psychological energies and characteristics beyond the
function itself.

Hero (1st Position)
The Hero function represents our core strength and identity. We use it most naturally
and confidently, often without conscious effort. The Hero function:
- Operates automatically and effortlessly
- Provides our strongest contribution to the world
- Forms core of identity and self-confidence
- Rarely questioned or doubted when healthy
- Source of greatest pride and capability

Example: INTJ's Ni Hero sees patterns and future implications effortlessly, forming
their identity as strategic visionaries.

Parent (2nd Position)  
The Parent function operates in a responsible, mature way to support the Hero. It:
- Serves and enables the Hero function
- Used consciously but less naturally than Hero
- Applies with maturity and responsibility  
- Helps take care of others and situations
- Can become overprotective or controlling

Example: INTJ's Te Parent organizes systems to implement Ni visions, used responsibly
to achieve goals.

Child (3rd Position)
The Child function brings joy and playfulness but operates immaturely. It:
- Source of fun, creativity, and lightheartedness
- Used with less skill and maturity than Hero/Parent
- Needs development and refinement
- Easily wounded or triggered
- Can be selfish or immature

Example: INTJ's Fi Child holds personal values joyfully but can react with hurt feelings
when values are challenged.

Inferior (4th Position)
The Inferior function aspires toward growth but causes stress when activated. It:
- Least developed of the four ego functions
- Gateway between conscious and unconscious
- Source of stress when circumstances demand its use
- Aspirational - represents desired growth
- Manifests immaturely when stressed

Example: INTJ's Se Inferior wants to be present and aesthetic but feels awkward and
stressful in sensory-demanding situations.

[Document continues with extensive detail about shadow functions, type development,
relationship dynamics, and practical applications...]
""".strip() * 3  # Triple it to make it very long

async def test_extraction():
    """Test concept extraction with documents of different sizes"""
    
    print("=" * 80)
    print("🧪 TESTING CONCEPT EXTRACTION")
    print("=" * 80)
    print()
    
    # Test 1: Short document
    print("📄 TEST 1: SHORT DOCUMENT (~5k chars)")
    print("-" * 80)
    result1 = await extract_concepts(SHORT_DOC, "test_short_001")
    if result1:
        print(f"✅ Extraction successful!")
        print(f"   Concepts: {len(result1['concepts'])}")
        print(f"   Relationships: {len(result1['relationships'])}")
        print(f"   Tokens: {result1['input_tokens']} in, {result1['output_tokens']} out")
        print()
        print("Sample concepts:")
        for concept in result1['concepts'][:3]:
            print(f"   - {concept['label']} ({concept['type']}, {concept['category']})")
        print()
        print("Sample relationships:")
        for rel in result1['relationships'][:3]:
            print(f"   - {rel['from']} → {rel['to']} ({rel['type']})")
    else:
        print("❌ Extraction failed!")
    print()
    print()
    
    # Test 2: Medium document  
    print("📄 TEST 2: MEDIUM DOCUMENT (~25k chars)")
    print("-" * 80)
    result2 = await extract_concepts(MEDIUM_DOC, "test_medium_001")
    if result2:
        print(f"✅ Extraction successful!")
        print(f"   Concepts: {len(result2['concepts'])}")
        print(f"   Relationships: {len(result2['relationships'])}")
        print(f"   Tokens: {result2['input_tokens']} in, {result2['output_tokens']} out")
        print()
        print("Sample concepts:")
        for concept in result2['concepts'][:3]:
            print(f"   - {concept['label']} ({concept['type']}, {concept['category']})")
        print()
        print("Sample relationships:")
        for rel in result2['relationships'][:3]:
            print(f"   - {rel['from']} → {rel['to']} ({rel['type']})")
    else:
        print("❌ Extraction failed!")
    print()
    print()
    
    # Test 3: Long document (will be truncated)
    print("📄 TEST 3: LONG DOCUMENT (~180k chars - will be truncated)")
    print("-" * 80)
    result3 = await extract_concepts(LONG_DOC, "test_long_001")
    if result3:
        print(f"✅ Extraction successful!")
        print(f"   Truncated: {result3.get('was_truncated', False)}")
        print(f"   Original length: {result3.get('original_length', 0):,} chars")
        print(f"   Processed length: {result3.get('processed_length', 0):,} chars")
        print(f"   Concepts: {len(result3['concepts'])}")
        print(f"   Relationships: {len(result3['relationships'])}")
        print(f"   Tokens: {result3['input_tokens']} in, {result3['output_tokens']} out")
        print()
        print("Sample concepts:")
        for concept in result3['concepts'][:3]:
            print(f"   - {concept['label']} ({concept['type']}, {concept['category']})")
    else:
        print("❌ Extraction failed!")
    print()
    print()
    
    # Get cost summary
    print("💰 COST SUMMARY")
    print("=" * 80)
    summary = await get_extraction_cost_summary()
    print(f"Total extractions: {summary['total_extractions']}")
    print(f"Successful: {summary['successful_extractions']}")
    print(f"Failed: {summary['failed_extractions']}")
    print(f"Success rate: {summary['success_rate']}%")
    print(f"Total cost: ${summary['total_cost']:.4f}")
    print(f"Average per extraction: ${summary['average_cost_per_extraction']:.6f}")
    print(f"Total tokens: {summary['total_input_tokens']:,} in, {summary['total_output_tokens']:,} out")
    print()
    
    print("🎉 All tests complete!")

if __name__ == "__main__":
    asyncio.run(test_extraction())
