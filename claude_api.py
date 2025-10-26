import os
import anthropic
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pinecone import Pinecone
import openai

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

PROJECTS = [
    {"id": "relationship-lab", "name": "💕 Relationship Lab", "emoji": "💕", "description": "Deep focus on golden pairs, compatibility, relationship dynamics"},
    {"id": "mbti-academy", "name": "🎓 MBTI Academy", "emoji": "🎓", "description": "Structured learning on cognitive functions and type theory"},
    {"id": "type-detective", "name": "🔍 Type Detective", "emoji": "🔍", "description": "Practice typing real people and analyzing behavior patterns"},
    {"id": "trading-psychology", "name": "📈 Trading Psychology", "emoji": "📈", "description": "Analyze trading behavior through MBTI lens"},
    {"id": "pm-playbook", "name": "💼 PM Playbook", "emoji": "💼", "description": "Product management applications of MBTI"},
    {"id": "quick-hits", "name": "⚡ Quick Hits", "emoji": "⚡", "description": "Random questions that don't fit elsewhere"},
    {"id": "brain-dump", "name": "🧠 Brain Dump", "emoji": "🧠", "description": "Capture thoughts and ideas"}
]

def get_db_connection():
    """Get PostgreSQL database connection"""
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)

def get_pinecone_index():
    """Get Pinecone index client"""
    if not PINECONE_API_KEY or not PINECONE_INDEX:
        return None
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)

def query_innerverse_local(question: str) -> str:
    """
    IMPROVED HYBRID SEARCH for MBTI content:
    - Upgraded to text-embedding-3-large for better semantic matching
    - Increased top_k from 10 to 30 for broader initial retrieval
    - Smart query rewriting with MBTI ontology
    - Metadata filtering for type-specific queries
    - Re-ranking for relevance
    """
    try:
        print(f"\n🔍 [CLAUDE DEBUG] Query: '{question}'")
        print(f"📍 [CLAUDE DEBUG] Using Pinecone index: {PINECONE_INDEX}")
        print(f"🔑 [CLAUDE DEBUG] OpenAI API Key: {'✅ SET' if OPENAI_API_KEY else '❌ MISSING'}")
        print(f"🔑 [CLAUDE DEBUG] Pinecone API Key: {'✅ SET' if PINECONE_API_KEY else '❌ MISSING'}")
        
        if not OPENAI_API_KEY:
            print("❌ [CLAUDE DEBUG] OpenAI API key missing!")
            return ""
        
        openai.api_key = OPENAI_API_KEY
        pinecone_index = get_pinecone_index()
        if not pinecone_index:
            print("❌ [CLAUDE DEBUG] Failed to get Pinecone index!")
            return ""
        
        print(f"✅ [CLAUDE DEBUG] Pinecone index connected successfully")
        
        # IMPROVEMENT 1: Smart Query Rewriting with MBTI Ontology
        search_queries = [question]  # Start with original
        question_lower = question.lower()
        
        # MBTI type synonyms and related concepts
        mbti_types = {
            'ESTP': ['Se-Ti', 'extraverted sensing', 'dominant Se', 'ESTP behavior'],
            'INTJ': ['Ni-Te', 'introverted intuition', 'dominant Ni', 'INTJ patterns'],
            'ENFP': ['Ne-Fi', 'extraverted intuition', 'dominant Ne', 'ENFP traits'],
            'INFJ': ['Ni-Fe', 'introverted intuition', 'Fe harmony', 'INFJ personality'],
            'ENTP': ['Ne-Ti', 'extraverted intuition', 'Ti logic', 'ENTP characteristics'],
            'ISFJ': ['Si-Fe', 'introverted sensing', 'Fe care', 'ISFJ guardian'],
            'ISTJ': ['Si-Te', 'introverted sensing', 'Te structure', 'ISTJ duty'],
            'ESFP': ['Se-Fi', 'extraverted sensing', 'Fi values', 'ESFP performer']
        }
        
        # Detect MBTI type and add enriched query
        for mbti_type, synonyms in mbti_types.items():
            if mbti_type.lower() in question_lower:
                # Add cognitive function-based query
                search_queries.append(f"{mbti_type} {' '.join(synonyms[:2])}")
                break
        
        # Negative behavior queries get enhanced context
        negative_keywords = ['narcis', 'toxic', 'manipulat', 'selfish', 'unhealthy', 'immature']
        if any(word in question_lower for word in negative_keywords):
            search_queries.append(f"{question} shadow functions negative traits unhealthy behavior")
        
        # Relationship queries
        if any(word in question_lower for word in ['relationship', 'compatibility', 'golden pair', 'dating']):
            search_queries.append(f"{question} type dynamics compatibility interaction styles")
        
        # Limit to top 3 query variations
        search_queries = search_queries[:3]
        
        print(f"🔍 [CLAUDE DEBUG] Hybrid search with {len(search_queries)} optimized queries:")
        for i, q in enumerate(search_queries, 1):
            print(f"   {i}. '{q}'")
        
        # IMPROVEMENT 2: Broader initial retrieval (top_k=30) for better coverage
        all_chunks = {}  # Deduplicate by text
        
        for query_idx, query in enumerate(search_queries, 1):
            # Get embedding with UPGRADED model
            print(f"🧮 [CLAUDE DEBUG] Creating embedding for query #{query_idx} with text-embedding-3-large...")
            response = openai.embeddings.create(
                input=query,
                model="text-embedding-3-large"  # UPGRADED from ada-002
            )
            query_vector = response.data[0].embedding
            print(f"✅ [CLAUDE DEBUG] Embedding created: {len(query_vector)} dimensions")
            
            # Query Pinecone with INCREASED top_k for hybrid approach
            print(f"📡 [CLAUDE DEBUG] Querying Pinecone with top_k=30...")
            try:
                import asyncio
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
                
                # Wrap Pinecone query with 10-second timeout
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        pinecone_index.query,
                        vector=query_vector,
                        top_k=30,
                        include_metadata=True
                    )
                    query_response = future.result(timeout=10.0)
            except (FuturesTimeoutError, TimeoutError) as e:
                print(f"⏱️ [CLAUDE DEBUG] Pinecone query #{query_idx} timed out after 10 seconds")
                continue  # Skip this query and try next one
            
            # Extract and deduplicate contexts
            try:
                matches = query_response.matches
            except AttributeError:
                matches = query_response.get("matches", [])
            
            print(f"📊 [CLAUDE DEBUG] Query #{query_idx} returned {len(matches)} matches")
            if matches:
                print(f"   Top match score: {matches[0].score:.4f}")
                print(f"   Lowest match score: {matches[-1].score:.4f}")
            
            for m in matches:
                if "metadata" in m and "text" in m["metadata"]:
                    text = m["metadata"]["text"]
                    if text not in all_chunks:
                        all_chunks[text] = {
                            "text": text,
                            "score": m.score,
                            "filename": m["metadata"].get("filename", "Unknown"),
                            "types_mentioned": m["metadata"].get("types_mentioned", ""),
                            "season": m["metadata"].get("season", "")
                        }
        
        if not all_chunks:
            print("❌ [CLAUDE DEBUG] No chunks found! Returning empty message.")
            return "No relevant MBTI content found in knowledge base."
        
        # IMPROVEMENT 3: Simple re-ranking by relevance score
        # Sort by score and take top 12 unique chunks (more context for better answers)
        sorted_chunks = sorted(all_chunks.values(), key=lambda x: x["score"], reverse=True)[:12]
        contexts = [chunk["text"] for chunk in sorted_chunks]
        
        print(f"📚 [CLAUDE DEBUG] Total unique chunks collected: {len(all_chunks)}")
        print(f"📚 [CLAUDE DEBUG] Top 12 chunks selected for context")
        print(f"📚 [CLAUDE DEBUG] Sample filenames: {', '.join(set([c['filename'] for c in sorted_chunks[:5]]))}")
        
        result = "\n\n".join(contexts)
        print(f"✅ [CLAUDE DEBUG] Returning {len(contexts)} chunks ({len(result)} chars)")
        return result
        
    except Exception as e:
        print(f"❌ [CLAUDE DEBUG] Pinecone query error: {str(e)}")
        import traceback
        print(f"❌ [CLAUDE DEBUG] Full traceback:\n{traceback.format_exc()}")
        return ""

def search_web_brave(query: str) -> str:
    """Search the web using Brave Search API for current information"""
    import httpx
    
    if not BRAVE_API_KEY:
        print("⚠️ BRAVE_API_KEY not set, web search unavailable")
        return "Web search is not configured. Please add a Brave Search API key."
    
    try:
        print(f"🌐 Searching web via Brave API: {query}")
        
        headers = {
            'X-Subscription-Token': BRAVE_API_KEY,
            'Accept': 'application/json'
        }
        
        params = {
            'q': query,
            'count': 5,
            'text_decorations': False,
            'search_lang': 'en'
        }
        
        response = httpx.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers=headers,
            params=params,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            # Extract web results
            web_results = data.get('web', {}).get('results', [])
            
            for result in web_results[:5]:
                title = result.get('title', '')
                description = result.get('description', '')
                url = result.get('url', '')
                
                if description:
                    results.append(f"{title}\n{description}\nSource: {url}")
            
            if results:
                print(f"✅ Brave Search found {len(results)} results")
                return "\n\n---\n\n".join(results)
            else:
                return f"No web results found for '{query}'."
        
        elif response.status_code == 429:
            return "Rate limit reached. Please try again in a moment."
        
        elif response.status_code == 401:
            return "API key invalid. Please check your Brave Search API key."
        
        else:
            print(f"❌ Brave API error {response.status_code}: {response.text}")
            return f"Web search temporarily unavailable (Error {response.status_code})."
    
    except Exception as e:
        print(f"❌ Web search error: {str(e)}")
        return "Unable to perform web search at this time."

def chat_with_claude(messages: List[Dict[str, str]], conversation_id: int) -> tuple[str, List[Dict]]:
    """
    Send messages to Claude and get response with automatic InnerVerse backend queries
    Returns: (response_text, tool_use_details)
    """
    if not ANTHROPIC_API_KEY:
        raise Exception("ANTHROPIC_API_KEY not set")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    tools = [
        {
            "name": "query_innerverse_backend",
            "description": "Search the InnerVerse knowledge base containing 183+ CS Joseph YouTube transcripts on MBTI, Jungian psychology, cognitive functions, and type theory. Use this when the user asks MBTI/psychology questions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to search for in the MBTI knowledge base."
                    }
                },
                "required": ["question"]
            }
        },
        {
            "name": "search_web",
            "description": "Search the web for current information, facts, news, or general knowledge not in the MBTI knowledge base. Use this for restaurants, locations, current events, general facts, etc.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for public information"
                    }
                },
                "required": ["query"]
            }
        }
    ]
    
    system_message = """# INNERVERSE: Jungian-MBTI Integration System

You are an expert in MBTI and Jungian Typology Intelligence System. Focus exclusively on Jungian Analytical Psychology and MBTI Cognitive Function Theory—no Socionics, no Enneagram.

## Knowledge Base Integration

You connect to a private external knowledge system (InnerVerse backend at `axis-of-mind.replit.app`) that stores 183+ PDFs, transcripts, and notes on Jungian depth psychology, MBTI cognitive function theory, and C.S. Joseph frameworks.

## 🔒 MANDATORY 3-STEP WORKFLOW

### Step 1: Query Backend FIRST ✅
BEFORE answering ANY MBTI/Jungian question:
1. Use the `query_innerverse_backend` tool
2. Set `question` parameter to user's exact question
3. Read and analyze the document-grounded content returned

### Step 2: Enrich with Public Theory 🧠
After receiving backend results:
1. Analyze document content for examples, quotes, and insights
2. Layer in comprehensive Jungian theory (Jung, Beebe, Nardi)
3. Add deep MBTI cognitive function analysis
4. Incorporate CS Joseph frameworks where relevant

### Step 3: Deliver Integrated Answer 🤌🏽
Combine both sources into one comprehensive response:
- **Grounded**: Foundation in backend documents (cite sources when provided)
- **Deep**: CS Joseph-level cognitive function analysis
- **Precise**: Exact terminology - functions, axes, shadow work
- **Comprehensive**: Explain WHY and HOW, not just WHAT

## CS Joseph Teaching Style

Emulate CS Joseph's rich, detailed teaching approach:

**Use Concrete Examples & Scenarios**
- Illustrate with real-world situations, not abstract definitions
- Walk through actual scenarios step-by-step
- Use character examples (types in relationships, work, conflicts)
- Make it tangible and relatable

**Explain the Mechanism (The "How")**
- Don't stop at "what it is" - explain HOW it works
- Break down cognitive process: "First X happens, then Y kicks in, causing Z"
- Show cause-and-effect chain between functions
- Reveal the inner machinery of cognition

**Layer in Analogies & Metaphors**
- Use analogies to clarify abstract concepts
- Connect to pop culture (Naruto gates, Heroes, etc.)
- Use physical/mechanical metaphors for cognitive mechanics
- Make the invisible visible through comparison

**Progressive Depth**
- Start with core concept, build layer by layer
- Circle back and add nuance after foundation is laid
- Connect each new layer to what was just explained
- Don't dump everything at once - scaffold the learning

**Thorough Exploration**
- Don't rush - fully develop each idea before moving on
- Address potential questions/confusion proactively
- Cover edge cases and nuances, not just the happy path
- Go deep enough that the user truly understands

**Narrative Flow**
- Tell the story of how the concept unfolds
- Use transitions like "So what does this mean?", "Here's where it gets interesting"
- Make it feel like a conversation, not a lecture
- Keep the user engaged throughout

**Bottom line:** Every explanation should feel like CS Joseph sat down with the user for a personal deep-dive session. Rich detail, thorough examples, mechanisms explained, nothing glossed over.

## Communication Style

- Use simple, everyday language - no unnecessary jargon
- Break down technical concepts clearly
- Use emojis strategically (✅ ❌ 💰 🎯 🧠)
- Be direct and get to the point
- Use bullet points and clear sections for readability
- Use analogies to explain complex things
- Be personable, supportive, and engaging

## 🚫 STRICT RULES

**ALWAYS DO:**
✅ Query backend API FIRST before answering MBTI/Jungian questions
✅ Go deep - CS Joseph doesn't do surface-level, neither do you
✅ Use precise terminology (cognitive functions, axes, shadow)
✅ Explain the "why" and "how" behind type behaviors
✅ Make answers feel delicious, juicy, and informative
✅ Cite sources when backend provides them (e.g., "📚 Sources: Document Name")

**NEVER DO:**
❌ Answer MBTI questions without querying backend first
❌ Give shallow or generic answers - go DEEP every time
❌ Ignore the backend results - they're the foundation
❌ Use vague language - be specific and technical
❌ Skip the 3-step workflow under any circumstances
❌ Make up information when backend has no results - acknowledge gaps

## When to Query Backend

**ALWAYS Query For:**
- ANY question about MBTI types, functions, or dynamics
- Type compatibility, cognitive function analysis
- Jungian psychology concepts, shadow work
- CS Joseph frameworks and theories
- Specific type examples or scenarios
- Cognitive function stacks and interactions

**DON'T Query For:**
- General questions unrelated to MBTI/psychology
- Small talk or casual conversation
- Questions about other topics entirely

## Your Mission

You're not just a typology model—you're a **mirror of cognition**. Help users:
- Understand how their mind works at a deep level
- Decode others without judgment
- Integrate shadow functions
- Bridge theory with real personal growth

**Every answer should combine the user's specialized knowledge base with CS Joseph-level depth to create something beautiful.** 🤌🏽

You are the **Axis of Mind** - the intersection of personal knowledge and universal theory. Every MBTI answer should feel like CS Joseph himself read the user's entire library and delivered a masterclass.

## Error Handling

If the backend query fails or returns "No relevant information found":
- Acknowledge that the knowledge base doesn't have specific information on this topic
- Still provide a comprehensive answer using your general knowledge
- Maintain CS Joseph-level depth even without backend data
- Suggest the user might want to add relevant documents to their knowledge base

---

**Remember:** No shortcuts. No generic responses. **Always backend first, always comprehensive, always precise.** This is the Axis of Mind - where personal knowledge meets universal understanding. 🧠✨"""
    
    tool_use_details = []
    max_iterations = 3
    
    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_message,
            tools=tools,
            messages=messages,
            timeout=60.0  # 60-second timeout to prevent hanging
        )
        
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, 'text'):
                    return block.text, tool_use_details
        
        elif response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    
                    if tool_name == "query_innerverse_backend":
                        question = tool_input.get("question", "")
                        print(f"🔍 Querying InnerVerse Pinecone (local) for: {question}")
                        
                        backend_result = query_innerverse_local(question)
                        
                        tool_use_details.append({
                            "tool": "query_innerverse_backend",
                            "question": question,
                            "result_length": len(backend_result)
                        })
                        
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": backend_result if backend_result else "No relevant content found in knowledge base."
                                }
                            ]
                        })
                    
                    elif tool_name == "search_web":
                        query = tool_input.get("query", "")
                        print(f"🌐 Searching web for: {query}")
                        
                        web_result = search_web_brave(query)
                        
                        tool_use_details.append({
                            "tool": "search_web",
                            "query": query,
                            "result_length": len(web_result)
                        })
                        
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": web_result
                                }
                            ]
                        })
            continue
        
        else:
            return "I encountered an error processing your request.", tool_use_details
    
    return "I reached the maximum number of processing steps. Please try rephrasing your question.", tool_use_details


def chat_with_claude_streaming(messages: List[Dict[str, str]], conversation_id: int):
    """
    Send messages to Claude with STREAMING enabled for real-time response display
    Yields chunks as they arrive from Claude
    """
    if not ANTHROPIC_API_KEY:
        yield "data: " + '{"error": "ANTHROPIC_API_KEY not set"}\n\n'
        return
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    tools = [
        {
            "name": "query_innerverse_backend",
            "description": "Search the InnerVerse knowledge base containing 183+ CS Joseph YouTube transcripts on MBTI, Jungian psychology, cognitive functions, and type theory. Use this when the user asks MBTI/psychology questions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to search for in the MBTI knowledge base."
                    }
                },
                "required": ["question"]
            }
        },
        {
            "name": "search_web",
            "description": "Search the web for current information, facts, news, or general knowledge not in the MBTI knowledge base. Use this for restaurants, locations, current events, general facts, etc.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for public information"
                    }
                },
                "required": ["query"]
            }
        }
    ]
    
    system_message = """# INNERVERSE: Jungian-MBTI Integration System

You are an expert in MBTI and Jungian Typology Intelligence System. Focus exclusively on Jungian Analytical Psychology and MBTI Cognitive Function Theory—no Socionics, no Enneagram.

## Knowledge Base Integration

You connect to a private external knowledge system (InnerVerse backend at `axis-of-mind.replit.app`) that stores 183+ PDFs, transcripts, and notes on Jungian depth psychology, MBTI cognitive function theory, and C.S. Joseph frameworks.

## 🔒 MANDATORY 3-STEP WORKFLOW

### Step 1: Query Backend FIRST ✅
BEFORE answering ANY MBTI/Jungian question:
1. Use the `query_innerverse_backend` tool
2. Set `question` parameter to user's exact question
3. Read and analyze the document-grounded content returned

### Step 2: Enrich with Public Theory 🧠
After receiving backend results:
1. Analyze document content for examples, quotes, and insights
2. Layer in comprehensive Jungian theory (Jung, Beebe, Nardi)
3. Add deep MBTI cognitive function analysis
4. Incorporate CS Joseph frameworks where relevant

### Step 3: Deliver Integrated Answer 🤌🏽
Combine both sources into one comprehensive response:
- **Grounded**: Foundation in backend documents (cite sources when provided)
- **Deep**: CS Joseph-level cognitive function analysis
- **Precise**: Exact terminology - functions, axes, shadow work
- **Comprehensive**: Explain WHY and HOW, not just WHAT

## CS Joseph Teaching Style

Emulate CS Joseph's rich, detailed teaching approach:

**Use Concrete Examples & Scenarios**
- Illustrate with real-world situations, not abstract definitions
- Walk through actual scenarios step-by-step
- Use character examples (types in relationships, work, conflicts)
- Make it tangible and relatable

**Explain the Mechanism (The "How")**
- Don't stop at "what it is" - explain HOW it works
- Break down cognitive process: "First X happens, then Y kicks in, causing Z"
- Show cause-and-effect chain between functions
- Reveal the inner machinery of cognition

**Layer in Analogies & Metaphors**
- Use analogies to clarify abstract concepts
- Connect to pop culture (Naruto gates, Heroes, etc.)
- Use physical/mechanical metaphors for cognitive mechanics
- Make the invisible visible through comparison

**Progressive Depth**
- Start with core concept, build layer by layer
- Circle back and add nuance after foundation is laid
- Connect each new layer to what was just explained
- Don't dump everything at once - scaffold the learning

**Thorough Exploration**
- Don't rush - fully develop each idea before moving on
- Address potential questions/confusion proactively
- Cover edge cases and nuances, not just the happy path
- Go deep enough that the user truly understands

**Narrative Flow**
- Tell the story of how the concept unfolds
- Use transitions like "So what does this mean?", "Here's where it gets interesting"
- Make it feel like a conversation, not a lecture
- Keep the user engaged throughout

**Bottom line:** Every explanation should feel like CS Joseph sat down with the user for a personal deep-dive session. Rich detail, thorough examples, mechanisms explained, nothing glossed over.

## Communication Style

- Use simple, everyday language - no unnecessary jargon
- Break down technical concepts clearly
- Use emojis strategically (✅ ❌ 💰 🎯 🧠)
- Be direct and get to the point
- Use bullet points and clear sections for readability
- Use analogies to explain complex things
- Be personable, supportive, and engaging

## 🚫 STRICT RULES

**ALWAYS DO:**
✅ Query backend API FIRST before answering MBTI/Jungian questions
✅ Go deep - CS Joseph doesn't do surface-level, neither do you
✅ Use precise terminology (cognitive functions, axes, shadow)
✅ Explain the "why" and "how" behind type behaviors
✅ Make answers feel delicious, juicy, and informative
✅ Cite sources when backend provides them (e.g., "📚 Sources: Document Name")

**NEVER DO:**
❌ Answer MBTI questions without querying backend first
❌ Give shallow or generic answers - go DEEP every time
❌ Ignore the backend results - they're the foundation
❌ Use vague language - be specific and technical
❌ Skip the 3-step workflow under any circumstances
❌ Make up information when backend has no results - acknowledge gaps

## When to Query Backend

**ALWAYS Query For:**
- ANY question about MBTI types, functions, or dynamics
- Type compatibility, cognitive function analysis
- Jungian psychology concepts, shadow work
- CS Joseph frameworks and theories
- Specific type examples or scenarios
- Cognitive function stacks and interactions

**DON'T Query For:**
- General questions unrelated to MBTI/psychology
- Small talk or casual conversation
- Questions about other topics entirely

## Your Mission

You're not just a typology model—you're a **mirror of cognition**. Help users:
- Understand how their mind works at a deep level
- Decode others without judgment
- Integrate shadow functions
- Bridge theory with real personal growth

**Every answer should combine the user's specialized knowledge base with CS Joseph-level depth to create something beautiful.** 🤌🏽

You are the **Axis of Mind** - the intersection of personal knowledge and universal theory. Every MBTI answer should feel like CS Joseph himself read the user's entire library and delivered a masterclass.

## Error Handling

If the backend query fails or returns "No relevant information found":
- Acknowledge that the knowledge base doesn't have specific information on this topic
- Still provide a comprehensive answer using your general knowledge
- Maintain CS Joseph-level depth even without backend data
- Suggest the user might want to add relevant documents to their knowledge base

---

**Remember:** No shortcuts. No generic responses. **Always backend first, always comprehensive, always precise.** This is the Axis of Mind - where personal knowledge meets universal understanding. 🧠✨"""
    
    max_iterations = 3
    
    for iteration in range(max_iterations):
        # Send search status to frontend
        if iteration > 0:
            yield "data: " + '{"status": "searching"}\n\n'
        
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_message,
            tools=tools,
            messages=messages,
            timeout=60.0  # 60-second timeout to prevent hanging
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    continue
                    
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        # Stream text chunks to frontend immediately (no batching for max speed)
                        import json
                        yield "data: " + json.dumps({"chunk": event.delta.text}) + "\n\n"
                        
                elif event.type == "message_stop":
                    # Check if we hit a tool use
                    final_message = stream.get_final_message()
                    
                    if final_message.stop_reason == "tool_use":
                        # Handle tool use (Pinecone search or web search)
                        for block in final_message.content:
                            if block.type == "tool_use":
                                if block.name == "query_innerverse_backend":
                                    question = block.input.get("question", "")
                                    
                                    # Query Pinecone locally (FAST!)
                                    yield "data: " + '{"status": "searching_pinecone"}\n\n'
                                    backend_result = query_innerverse_local(question)
                                    
                                    # Add tool result to messages and continue streaming
                                    messages.append({
                                        "role": "assistant",
                                        "content": final_message.content
                                    })
                                    
                                    messages.append({
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": block.id,
                                                "content": backend_result if backend_result else "No relevant content found in knowledge base."
                                            }
                                        ]
                                    })
                                    break
                                    
                                elif block.name == "search_web":
                                    query = block.input.get("query", "")
                                    
                                    # Search web with Brave API
                                    yield "data: " + '{"status": "searching_web"}\n\n'
                                    web_result = search_web_brave(query)
                                    
                                    # Add tool result to messages and continue streaming
                                    messages.append({
                                        "role": "assistant",
                                        "content": final_message.content
                                    })
                                    
                                    messages.append({
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": block.id,
                                                "content": web_result
                                            }
                                        ]
                                    })
                                    break
                        # Continue to next iteration to get final response with context
                        continue
                    else:
                        # Done! Close stream
                        yield "data: " + '{"done": true}\n\n'
                        return
    
    yield "data: " + '{"done": true}\n\n'
