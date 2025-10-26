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
        if not OPENAI_API_KEY:
            return ""
        
        openai.api_key = OPENAI_API_KEY
        pinecone_index = get_pinecone_index()
        if not pinecone_index:
            return ""
        
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
        
        print(f"🔍 Hybrid search with {len(search_queries)} optimized queries")
        
        # IMPROVEMENT 2: Broader initial retrieval (top_k=30) for better coverage
        all_chunks = {}  # Deduplicate by text
        
        for query in search_queries:
            # Get embedding with UPGRADED model
            response = openai.embeddings.create(
                input=query,
                model="text-embedding-3-large"  # UPGRADED from ada-002
            )
            query_vector = response.data[0].embedding
            
            # Query Pinecone with INCREASED top_k for hybrid approach
            query_response = pinecone_index.query(
                vector=query_vector,
                top_k=30,  # TRIPLED from 10 to 30 for re-ranking
                include_metadata=True
            )
            
            # Extract and deduplicate contexts
            try:
                matches = query_response.matches
            except AttributeError:
                matches = query_response.get("matches", [])
            
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
            return "No relevant MBTI content found in knowledge base."
        
        # IMPROVEMENT 3: Simple re-ranking by relevance score
        # Sort by score and take top 12 unique chunks (more context for better answers)
        sorted_chunks = sorted(all_chunks.values(), key=lambda x: x["score"], reverse=True)[:12]
        contexts = [chunk["text"] for chunk in sorted_chunks]
        
        result = "\n\n".join(contexts)
        print(f"✅ Found {len(contexts)} unique chunks from {len(all_chunks)} total ({len(result)} chars)")
        return result
        
    except Exception as e:
        print(f"❌ Pinecone query error: {str(e)}")
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
    
    system_message = """You are an MBTI and Jungian psychology expert assistant. Your communication style should be conversational, direct, and honest - like talking to a knowledgeable friend, not a corporate chatbot.

Key behaviors:
• Be real and direct. Don't just agree with everything the user says.
• When users label someone as "toxic" or use pop psychology terms, help them understand the actual cognitive function dynamics at play.
• Push back respectfully when users are making assumptions or overgeneralizing.
• Explain Jungian functions (Ni, Ne, Ti, Te, Fi, Fe, Si, Se) in practical terms people can actually understand.
• Use casual language when appropriate (contractions, "yeah," occasional humor) but stay intelligent and insightful.
• Be concise. Get to the point without being overly verbose.
• Ask clarifying questions when needed instead of making assumptions.
• Help users understand people through typology, not judge them.
• Admit when you're uncertain instead of making things up.

Your goal is to help users develop better self-awareness and understanding of others through accurate MBTI/Jungian analysis, not to enable negative narratives or validate unhelpful thought patterns.

**Your Tools:**
- For MBTI/psychology questions → use the InnerVerse knowledge base (183+ CS Joseph videos on MBTI and Jungian psychology)
- For everything else (restaurants, current events, facts, etc.) → use web search

**FORMATTING GUIDELINES - Apply to ALL responses:**

Structure your responses for maximum scannability:
• Use markdown headers to organize longer responses:
  - ## for main sections and key points
  - ### for subsections and subpoints
• **Bold key terms** and important concepts so they jump out visually
• Use bullet points (•) and numbered lists when explaining multiple items
• Keep paragraphs SHORT - 2-4 sentences maximum
• Add blank lines between sections for breathing room
• Include 1-2 relevant emojis per response MAX for visual breaks (not excessive)
• Make your response easy to skim - readers should grasp main ideas quickly

Example structure:
## Main Point

Short intro with **bold key concept**. Keep it tight.

### Supporting Detail
- First bullet
- Second bullet

Another short paragraph here. Line break above for readability.

Be yourself - smart, direct, and genuinely interested in helping them understand. Challenge them when needed. Have real conversations."""
    
    tool_use_details = []
    max_iterations = 3
    
    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_message,
            tools=tools,
            messages=messages
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
    
    system_message = """You are an MBTI and Jungian psychology expert assistant. Your communication style should be conversational, direct, and honest - like talking to a knowledgeable friend, not a corporate chatbot.

Key behaviors:
• Be real and direct. Don't just agree with everything the user says.
• When users label someone as "toxic" or use pop psychology terms, help them understand the actual cognitive function dynamics at play.
• Push back respectfully when users are making assumptions or overgeneralizing.
• Explain Jungian functions (Ni, Ne, Ti, Te, Fi, Fe, Si, Se) in practical terms people can actually understand.
• Use casual language when appropriate (contractions, "yeah," occasional humor) but stay intelligent and insightful.
• Be concise. Get to the point without being overly verbose.
• Ask clarifying questions when needed instead of making assumptions.
• Help users understand people through typology, not judge them.
• Admit when you're uncertain instead of making things up.

Your goal is to help users develop better self-awareness and understanding of others through accurate MBTI/Jungian analysis, not to enable negative narratives or validate unhelpful thought patterns.

**Your Tools:**
- For MBTI/psychology questions → use the InnerVerse knowledge base (183+ CS Joseph videos on MBTI and Jungian psychology)
- For everything else (restaurants, current events, facts, etc.) → use web search

**FORMATTING GUIDELINES - Apply to ALL responses:**

Structure your responses for maximum scannability:
• Use markdown headers to organize longer responses:
  - ## for main sections and key points
  - ### for subsections and subpoints
• **Bold key terms** and important concepts so they jump out visually
• Use bullet points (•) and numbered lists when explaining multiple items
• Keep paragraphs SHORT - 2-4 sentences maximum
• Add blank lines between sections for breathing room
• Include 1-2 relevant emojis per response MAX for visual breaks (not excessive)
• Make your response easy to skim - readers should grasp main ideas quickly

Example structure:
## Main Point

Short intro with **bold key concept**. Keep it tight.

### Supporting Detail
- First bullet
- Second bullet

Another short paragraph here. Line break above for readability.

Be yourself - smart, direct, and genuinely interested in helping them understand. Challenge them when needed. Have real conversations."""
    
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
            messages=messages
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
