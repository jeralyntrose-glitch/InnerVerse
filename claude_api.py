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
    """Query Pinecone directly for MBTI content (FAST - no external API call)"""
    try:
        if not OPENAI_API_KEY:
            return ""
        
        # Get embedding for the question
        openai.api_key = OPENAI_API_KEY
        response = openai.embeddings.create(
            input=question,
            model="text-embedding-ada-002"
        )
        question_vector = response.data[0].embedding
        
        # Query Pinecone
        pinecone_index = get_pinecone_index()
        if not pinecone_index:
            return ""
        
        print(f"🔍 Searching Pinecone for: {question}")
        query_response = pinecone_index.query(
            vector=question_vector,
            top_k=5,
            include_metadata=True
        )
        
        # Extract contexts
        contexts = []
        try:
            matches = query_response.matches
        except AttributeError:
            matches = query_response.get("matches", [])
        
        for m in matches:
            if "metadata" in m and "text" in m["metadata"]:
                contexts.append(m["metadata"]["text"])
        
        if not contexts:
            return "No relevant MBTI content found in knowledge base."
        
        result = "\n\n".join(contexts)
        print(f"✅ Found {len(contexts)} relevant chunks ({len(result)} chars)")
        return result
        
    except Exception as e:
        print(f"❌ Pinecone query error: {str(e)}")
        return ""

def search_web(query: str) -> str:
    """Search the web for current information using DuckDuckGo HTML scraping"""
    import httpx
    from urllib.parse import quote_plus
    
    try:
        # Use DuckDuckGo HTML search (more reliable than JSON API)
        encoded_query = quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = httpx.get(search_url, headers=headers, timeout=15.0, follow_redirects=True)
        
        if response.status_code == 200:
            html = response.text
            
            # Extract search results using simple string parsing
            results = []
            snippets = html.split('class="result__snippet">')
            
            for snippet in snippets[1:6]:  # Get top 5 results
                end_idx = snippet.find('</a>')
                if end_idx != -1:
                    text = snippet[:end_idx]
                    # Clean HTML tags
                    text = text.replace('<b>', '').replace('</b>', '')
                    text = text.replace('&quot;', '"').replace('&#x27;', "'")
                    text = text.strip()
                    if text and len(text) > 20:
                        results.append(text)
            
            if results:
                print(f"✅ Web search found {len(results)} results for: {query}")
                return "\n\n".join(results)
            
            # Fallback: Try JSON API with better parsing
            print("⚠️ HTML parsing failed, trying JSON API...")
            json_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
            json_response = httpx.get(json_url, timeout=10.0)
            
            if json_response.status_code == 200:
                data = json_response.json()
                results = []
                
                # Get abstract
                if data.get("AbstractText"):
                    results.append(f"Overview: {data['AbstractText']}")
                
                # Get related topics (handle nested structure)
                for topic in data.get("RelatedTopics", [])[:5]:
                    if isinstance(topic, dict):
                        if "Text" in topic:
                            results.append(topic["Text"])
                        elif "Topics" in topic:
                            # Handle nested topics
                            for subtopic in topic["Topics"][:3]:
                                if "Text" in subtopic:
                                    results.append(subtopic["Text"])
                
                if results:
                    return "\n\n".join(results)
            
            return f"No detailed results found for '{query}'. Try rephrasing the question or being more specific."
        
        return "Search service temporarily unavailable"
    except Exception as e:
        print(f"❌ Web search error: {str(e)}")
        return f"Search error: Unable to fetch results at this time."

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
                        
                        web_result = search_web(query)
                        
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
                        # Stream text chunks to frontend in real-time
                        import json
                        yield "data: " + json.dumps({"chunk": event.delta.text}) + "\n\n"
                        
                elif event.type == "message_stop":
                    # Check if we hit a tool use
                    final_message = stream.get_final_message()
                    
                    if final_message.stop_reason == "tool_use":
                        # Handle tool use (Pinecone search)
                        for block in final_message.content:
                            if block.type == "tool_use" and block.name == "query_innerverse_backend":
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
                        # Continue to next iteration to get final response with context
                        continue
                    else:
                        # Done! Close stream
                        yield "data: " + '{"done": true}\n\n'
                        return
    
    yield "data: " + '{"done": true}\n\n'
