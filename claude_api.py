import os
import anthropic
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pinecone import Pinecone
import openai
import time
import json
from src.services.pinecone_organizer import extract_all_metadata, organize_results_by_metadata, format_organized_context
from src.services.conversation_context import get_or_create_context
from src.services.prompt_builder import build_system_prompt, PromptAssemblyError
from src.services.type_injection import get_type_stack

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

# Load MBTI reference data at module level (loaded once on startup)
try:
    with open('src/data/reference_data.json', 'r') as f:
        REFERENCE_DATA = json.load(f)
    print("✅ [REFERENCE DATA] Loaded MBTI reference data successfully")
except FileNotFoundError:
    print("⚠️ [REFERENCE DATA] reference_data.json not found - using Pinecone only")
    REFERENCE_DATA = {}
except Exception as e:
    print(f"⚠️ [REFERENCE DATA] Error loading reference_data.json: {e}")
    REFERENCE_DATA = {}

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

def extract_follow_up_question(text: str) -> str:
    """
    Extract follow-up question from Claude's response.
    Pattern: [FOLLOW-UP: question?]
    Returns: The extracted question string, or None if not found
    """
    import re
    follow_up_match = re.search(r'\[FOLLOW-UP:\s*(.+?)\]', text, re.IGNORECASE)
    if follow_up_match:
        return follow_up_match.group(1).strip()
    return None

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
            
            # Extract ALL metadata (including 10 enriched fields)
            enriched_results = extract_all_metadata(matches)
            
            for result in enriched_results:
                text = result['text']
                if text and text not in all_chunks:
                    all_chunks[text] = result
        
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

def make_claude_api_call_with_retry(client, **kwargs):
    """
    Make Claude API call with exponential backoff retry logic for overloaded errors.
    Retries: 2s wait, then 4s wait. Max 3 attempts total.
    """
    max_retries = 2
    retry_delays = [2, 4]  # Exponential backoff: 2s, then 4s
    
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(**kwargs)
            return response
        
        except anthropic.InternalServerError as e:
            # Check if it's an overloaded error
            error_message = str(e).lower()
            is_overloaded = 'overloaded' in error_message
            
            if is_overloaded and attempt < max_retries:
                wait_time = retry_delays[attempt]
                print(f"⚠️ Claude API overloaded (attempt {attempt + 1}/{max_retries + 1}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # If not overloaded or max retries reached, re-raise
            if is_overloaded:
                raise Exception("Claude API is temporarily busy. Please try again in a moment.")
            else:
                raise
        
        except Exception as e:
            # For other errors, don't retry - just raise immediately
            raise
    
    # This shouldn't be reached, but just in case
    raise Exception("Claude API is temporarily busy. Please try again in a moment.")

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
            "name": "query_reference_data",
            "description": "Get exact MBTI type structures like four sides mappings, cognitive function stacks, temperaments, and quadra assignments. Use this FIRST for factual lookup questions about type structures (e.g., 'What are INFJ's four sides?', 'ENFP function stack', 'INTJ temperament'). Returns verified reference data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "type_code": {
                        "type": "string",
                        "description": "The MBTI type code in uppercase (e.g., INFJ, ENFP, ISTJ, ENTP)"
                    }
                },
                "required": ["type_code"]
            }
        },
        {
            "name": "query_innerverse_backend",
            "description": "Search the InnerVerse knowledge base containing 183+ CS Joseph YouTube transcripts on MBTI, Jungian psychology, cognitive functions, and type theory. Use this when the user asks MBTI/psychology questions that need examples, context, or detailed explanations beyond basic type structures.",
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
    
    # Build system prompt with all 3 layers using centralized prompt builder
    # This ensures reference data injection is structurally enforced
    last_user_message_content = None
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            last_user_message_content = msg.get('content')
            break
    
    try:
        system_message, prompt_metadata = build_system_prompt(
            conversation_id=conversation_id,
            user_message=last_user_message_content or ""
        )
    except PromptAssemblyError as e:
        error_msg = f"Prompt assembly failed: {e}"
        print(f"❌ [PROMPT BUILDER] {error_msg}")
        return (error_msg, [])
    
    tool_use_details = []
    max_iterations = 3
    
    for iteration in range(max_iterations):
        try:
            response = make_claude_api_call_with_retry(
                client,
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_message,
                tools=tools,
                messages=messages,
                timeout=60.0  # 60-second timeout to prevent hanging
            )
        except Exception as e:
            # Catch user-friendly error messages from retry logic
            error_msg = str(e)
            if "temporarily busy" in error_msg.lower():
                # Return the user-friendly message to the frontend
                return (error_msg, tool_use_details, None)
            else:
                # Re-raise other unexpected errors
                raise
        
        # Log Claude API usage
        if hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'input_tokens', 0)
            output_tokens = getattr(response.usage, 'output_tokens', 0)
            cost = (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)
            
            # Import log function from main.py
            try:
                from main import log_api_usage
                log_api_usage("claude_chat", "claude-sonnet-4", input_tokens, output_tokens, cost)
            except Exception as e:
                print(f"⚠️ Could not log Claude usage: {e}")
        
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, 'text'):
                    # Extract follow-up question if present
                    full_text = block.text
                    follow_up_question = extract_follow_up_question(full_text)
                    
                    # Remove the [FOLLOW-UP: ...] from the main text
                    main_text = full_text
                    if follow_up_question:
                        import re
                        follow_up_match = re.search(r'\[FOLLOW-UP:\s*(.+?)\]', full_text, re.IGNORECASE)
                        if follow_up_match:
                            main_text = full_text[:follow_up_match.start()].strip()
                    
                    return (main_text, tool_use_details, follow_up_question)
        
        elif response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    
                    if tool_name == "query_reference_data":
                        type_code = tool_input.get("type_code", "").upper()
                        print(f"📖 [REFERENCE DATA] Looking up type: {type_code}")
                        
                        # Lookup in reference data using same loader as type_injection
                        type_data = get_type_stack(type_code)
                        
                        if type_data:
                            # Extract four sides data properly
                            four_sides = type_data.get("four_sides", {})
                            
                            # Extract type codes from each side
                            ego_type = four_sides.get('ego', {}).get('type', 'Unknown')
                            shadow_type = four_sides.get('shadow', {}).get('type', 'Unknown')
                            subconscious_type = four_sides.get('subconscious', {}).get('type', 'Unknown')
                            superego_type = four_sides.get('superego', {}).get('type', 'Unknown')
                            
                            # Format functions for each side
                            def format_functions(funcs):
                                return '\n'.join([f"  • {f.get('position', 'Unknown')}: {f.get('function', 'Unknown')}" for f in funcs])
                            
                            # Build formatted response
                            result_text = f"""**{type_code} Complete Type Information:**

🎭 **Ego ({ego_type}):**
{format_functions(four_sides.get('ego', {}).get('functions', []))}

👥 **Shadow ({shadow_type}):**
{format_functions(four_sides.get('shadow', {}).get('functions', []))}

🔄 **Subconscious ({subconscious_type}):**
{format_functions(four_sides.get('subconscious', {}).get('functions', []))}

⚡ **Superego ({superego_type}):**
{format_functions(four_sides.get('superego', {}).get('functions', []))}

**Categories:**
• Temperament: {type_data.get('categories', {}).get('temperament', 'Unknown')}
• Quadra: {type_data.get('categories', {}).get('quadra', 'Unknown')}
• Interaction Style: {type_data.get('categories', {}).get('interaction_style', 'Unknown')}
• Temple: {type_data.get('categories', {}).get('temple', 'Unknown')}"""
                            
                            print(f"✅ [REFERENCE DATA] Found and formatted data for {type_code}")
                        else:
                            result_text = f"No reference data found for type: {type_code}"
                            print(f"❌ [REFERENCE DATA] No data for {type_code}")
                        
                        tool_use_details.append({
                            "tool": "query_reference_data",
                            "type_code": type_code,
                            "found": bool(type_data)
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
                                    "content": result_text
                                }
                            ]
                        })
                    
                    elif tool_name == "query_innerverse_backend":
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
            return "I encountered an error processing your request.", tool_use_details, None
    
    return "I reached the maximum number of processing steps. Please try rephrasing your question.", tool_use_details, None


def chat_with_claude_streaming(messages: List[Dict[str, str]], conversation_id: int):
    """
    Send messages to Claude with STREAMING enabled for real-time response display
    Yields chunks as they arrive from Claude
    RETURNS: Yields SSE events, final event includes follow-up question if present
    """
    if not ANTHROPIC_API_KEY:
        yield "data: " + '{"error": "ANTHROPIC_API_KEY not set"}\n\n'
        return
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    full_response_text = []  # Accumulate response for follow-up extraction
    
    tools = [
        {
            "name": "query_reference_data",
            "description": "Get exact MBTI type structures like four sides mappings, cognitive function stacks, temperaments, and quadra assignments. Use this FIRST for factual lookup questions about type structures (e.g., 'What are INFJ's four sides?', 'ENFP function stack', 'INTJ temperament'). Returns verified reference data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "type_code": {
                        "type": "string",
                        "description": "The MBTI type code in uppercase (e.g., INFJ, ENFP, ISTJ, ENTP)"
                    }
                },
                "required": ["type_code"]
            }
        },
        {
            "name": "query_innerverse_backend",
            "description": "Search the InnerVerse knowledge base containing 183+ CS Joseph YouTube transcripts on MBTI, Jungian psychology, cognitive functions, and type theory. Use this when the user asks MBTI/psychology questions that need examples, context, or detailed explanations beyond basic type structures.",
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
    
    # Build system prompt with all 3 layers using centralized prompt builder
    # This ensures reference data injection is structurally enforced
    last_user_message_content = None
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            last_user_message_content = msg.get('content')
            break
    
    try:
        system_message, prompt_metadata = build_system_prompt(
            conversation_id=conversation_id,
            user_message=last_user_message_content or ""
        )
    except PromptAssemblyError as e:
        error_msg = f"Prompt assembly failed: {e}"
        print(f"❌ [PROMPT BUILDER] {error_msg}")
        yield "data: " + json.dumps({"error": error_msg}) + "\n\n"
        return
    
    max_iterations = 3
    
    try:
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
                            text_chunk = event.delta.text
                            full_response_text.append(text_chunk)  # Accumulate for follow-up extraction
                            yield "data: " + json.dumps({"chunk": text_chunk}) + "\n\n"
                            
                    elif event.type == "message_stop":
                        # Check if we hit a tool use
                        final_message = stream.get_final_message()
                        
                        if final_message.stop_reason == "tool_use":
                            # Handle tool use (Reference data, Pinecone search, or web search)
                            for block in final_message.content:
                                if block.type == "tool_use":
                                    if block.name == "query_reference_data":
                                        type_code = block.input.get("type_code", "").upper()
                                        
                                        # Lookup reference data using same loader as type_injection
                                        yield "data: " + '{"status": "looking_up_reference"}\n\n'
                                        type_data = get_type_stack(type_code)
                                        
                                        if type_data:
                                            result_text = json.dumps(type_data, indent=2)
                                            print(f"✅ [REFERENCE DATA STREAMING] Found data for {type_code} via type_injection.get_type_stack()")
                                        else:
                                            result_text = f"No reference data found for type: {type_code}"
                                            print(f"❌ [REFERENCE DATA STREAMING] No data for {type_code} in reference_data.json")
                                        
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
                                                    "content": result_text
                                                }
                                            ]
                                        })
                                        break
                                    
                                    elif block.name == "query_innerverse_backend":
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
                            # Done! Log usage and extract follow-up question
                            import json
                            
                            # Log Claude API usage
                            if hasattr(final_message, 'usage'):
                                input_tokens = getattr(final_message.usage, 'input_tokens', 0)
                                output_tokens = getattr(final_message.usage, 'output_tokens', 0)
                                cost = (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)
                                
                                try:
                                    from main import log_api_usage
                                    log_api_usage("claude_chat_stream", "claude-sonnet-4", input_tokens, output_tokens, cost)
                                    print(f"💰 Logged streaming Claude usage: ${cost:.6f}")
                                except Exception as e:
                                    print(f"⚠️ Could not log streaming Claude usage: {e}")
                            
                            follow_up = extract_follow_up_question("".join(full_response_text))
                            yield "data: " + json.dumps({"done": True, "follow_up": follow_up}) + "\n\n"
                            return
    
        # Max iterations reached - send done with follow-up
        import json
        follow_up = extract_follow_up_question("".join(full_response_text))
        yield "data: " + json.dumps({"done": True, "follow_up": follow_up}) + "\n\n"
    
    except Exception as e:
        import json
        error_msg = str(e)
        print(f"❌ Claude streaming error: {error_msg}")
        yield "data: " + json.dumps({"error": f"Sorry, I encountered an error: {error_msg}. Please try again."}) + "\n\n"
