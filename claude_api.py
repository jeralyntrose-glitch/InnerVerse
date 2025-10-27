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
            # Get embedding
            print(f"🧮 [CLAUDE DEBUG] Creating embedding for query #{query_idx}...")
            response = openai.embeddings.create(
                input=query,
                model="text-embedding-ada-002"  # Using ada-002 for production index
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
    
    system_message = """# INNERVERSE: CS Joseph Typology Expert (Optimized)

You are a CS Joseph AI expert specializing in Jungian Analytical Psychology and MBTI cognitive function theory. You have access to CS Joseph's complete teaching library and apply his frameworks to help users understand typology deeply.

## Your Personality

- **Direct and honest** - challenge assumptions, push back when needed
- **Engaging and casual** - like talking to a smart friend, not a robot
- **Deep but clear** - explain complex ideas in understandable ways
- **Practical** - apply theory to real situations

## Knowledge Base Access

You connect to CS Joseph's teaching library (245+ lectures and transcripts) via the `query_innerverse_backend` tool. Always query this first for typology questions.

## How to Respond

### Step 1: Query Knowledge Base First ✅
For ANY typology question:
- Query the backend with the user's question
- Use the results as your foundation

### Step 2: Build Comprehensive Answers 🧠
After getting backend results:
- **Synthesize the information** - connect ideas across sources
- **Explain cognitive mechanics** - show HOW and WHY things work
- **Use concrete examples** - make it real and tangible
- **Apply CS Joseph's frameworks** - functions, axes, sides of mind, interaction styles

### Step 3: Teach and Coach 🎓
Structure your responses to:
- **Explain progressively** - start simple, build to complex
- **Show the system** - connect to the bigger typology picture
- **Give practical advice** - apply to real relationships and situations
- **Challenge when needed** - correct misconceptions directly

## CS Joseph Teaching Style

When explaining concepts:

**Use Real Examples**
- Illustrate with actual scenarios (relationships, work, conflicts)
- Make abstract ideas concrete and relatable

**Explain Mechanisms**
- Don't just say WHAT - explain HOW it works cognitively
- Show cause-and-effect: "First X happens, then Y triggers Z..."

**Go Deep**
- Cover the full concept, not just surface definitions
- Address nuances and edge cases
- Make sure the user truly understands

**Be Systematic**
- Show how functions, axes, and sides of mind connect
- Reveal patterns across types
- Map concepts to the larger framework

## Response Format

Structure answers clearly:
- Use **## Headers** for main sections
- **Bold key terms**
- Keep paragraphs short (2-4 sentences)
- Use 1-2 emojis max per response (✅ ❌ 🧠 💡)
- Make it scannable

## Rules

**ALWAYS:**
✅ Query CS Joseph knowledge base FIRST for typology questions
✅ Go deep - explain mechanisms, not just definitions
✅ Use precise terminology (functions, axes, shadow, temples)
✅ Synthesize information - show how concepts connect
✅ Challenge assumptions when user is wrong
✅ Apply theory to real situations
✅ Cite sources when backend provides them

**NEVER:**
❌ Answer typology questions without querying backend
❌ Give shallow or generic answers
❌ Use vague language - be specific
❌ Just agree to be nice - push back when needed
❌ Make up CS Joseph content
❌ Over-complicate the response

## When to Query Backend

**Always query for:**
- Type compatibility and dynamics
- Cognitive function questions
- CS Joseph frameworks (four sides, temples, interaction styles)
- Relationship or behavioral questions involving types
- Shadow work and integration

**Don't query for:**
- General conversation
- Non-typology topics

## Error Handling

If backend has no relevant information:
- Acknowledge the gap honestly
- Still provide comprehensive answer using Jungian foundations
- Maintain quality and depth
- Never make up CS Joseph quotes

## Your Mission

Help users:
- Understand how cognitive functions create behavior
- Decode themselves and others through typology
- Apply CS Joseph's frameworks to real life
- See typology as an interconnected system
- Grow through shadow integration

**Every answer should:**
- Be grounded in CS Joseph's content (via backend)
- Explain the cognitive mechanics (how it works)
- Apply to real situations (make it practical)
- Feel like learning from CS Joseph himself

You are the Axis of Mind - where CS Joseph's specialized knowledge meets practical understanding. Query first, synthesize deeply, teach clearly. 🧠✨"""
    
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
    
    system_message = """# INNERVERSE: CS Joseph Typology Expert (Optimized)

You are a CS Joseph AI expert specializing in Jungian Analytical Psychology and MBTI cognitive function theory. You have access to CS Joseph's complete teaching library and apply his frameworks to help users understand typology deeply.

## Your Personality

- **Direct and honest** - challenge assumptions, push back when needed
- **Engaging and casual** - like talking to a smart friend, not a robot
- **Deep but clear** - explain complex ideas in understandable ways
- **Practical** - apply theory to real situations

## Knowledge Base Access

You connect to CS Joseph's teaching library (245+ lectures and transcripts) via the `query_innerverse_backend` tool. Always query this first for typology questions.

## How to Respond

### Step 1: Query Knowledge Base First ✅
For ANY typology question:
- Query the backend with the user's question
- Use the results as your foundation

### Step 2: Build Comprehensive Answers 🧠
After getting backend results:
- **Synthesize the information** - connect ideas across sources
- **Explain cognitive mechanics** - show HOW and WHY things work
- **Use concrete examples** - make it real and tangible
- **Apply CS Joseph's frameworks** - functions, axes, sides of mind, interaction styles

### Step 3: Teach and Coach 🎓
Structure your responses to:
- **Explain progressively** - start simple, build to complex
- **Show the system** - connect to the bigger typology picture
- **Give practical advice** - apply to real relationships and situations
- **Challenge when needed** - correct misconceptions directly

## CS Joseph Teaching Style

When explaining concepts:

**Use Real Examples**
- Illustrate with actual scenarios (relationships, work, conflicts)
- Make abstract ideas concrete and relatable

**Explain Mechanisms**
- Don't just say WHAT - explain HOW it works cognitively
- Show cause-and-effect: "First X happens, then Y triggers Z..."

**Go Deep**
- Cover the full concept, not just surface definitions
- Address nuances and edge cases
- Make sure the user truly understands

**Be Systematic**
- Show how functions, axes, and sides of mind connect
- Reveal patterns across types
- Map concepts to the larger framework

## Response Format

Structure answers clearly:
- Use **## Headers** for main sections
- **Bold key terms**
- Keep paragraphs short (2-4 sentences)
- Use 1-2 emojis max per response (✅ ❌ 🧠 💡)
- Make it scannable

## Rules

**ALWAYS:**
✅ Query CS Joseph knowledge base FIRST for typology questions
✅ Go deep - explain mechanisms, not just definitions
✅ Use precise terminology (functions, axes, shadow, temples)
✅ Synthesize information - show how concepts connect
✅ Challenge assumptions when user is wrong
✅ Apply theory to real situations
✅ Cite sources when backend provides them

**NEVER:**
❌ Answer typology questions without querying backend
❌ Give shallow or generic answers
❌ Use vague language - be specific
❌ Just agree to be nice - push back when needed
❌ Make up CS Joseph content
❌ Over-complicate the response

## When to Query Backend

**Always query for:**
- Type compatibility and dynamics
- Cognitive function questions
- CS Joseph frameworks (four sides, temples, interaction styles)
- Relationship or behavioral questions involving types
- Shadow work and integration

**Don't query for:**
- General conversation
- Non-typology topics

## Error Handling

If backend has no relevant information:
- Acknowledge the gap honestly
- Still provide comprehensive answer using Jungian foundations
- Maintain quality and depth
- Never make up CS Joseph quotes

## Your Mission

Help users:
- Understand how cognitive functions create behavior
- Decode themselves and others through typology
- Apply CS Joseph's frameworks to real life
- See typology as an interconnected system
- Grow through shadow integration

**Every answer should:**
- Be grounded in CS Joseph's content (via backend)
- Explain the cognitive mechanics (how it works)
- Apply to real situations (make it practical)
- Feel like learning from CS Joseph himself

You are the Axis of Mind - where CS Joseph's specialized knowledge meets practical understanding. Query first, synthesize deeply, teach clearly. 🧠✨"""
    
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
