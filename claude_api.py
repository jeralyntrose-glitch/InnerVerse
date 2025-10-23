import os
import anthropic
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")

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

def query_innerverse(question: str) -> str:
    """Query the InnerVerse backend for relevant MBTI content"""
    import httpx
    
    try:
        backend_url = "https://axis-of-mind.replit.app/query"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = httpx.post(
            backend_url,
            json={"question": question},
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("answer", "")
        else:
            return ""
    except Exception as e:
        print(f"Backend query error: {str(e)}")
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
    
    system_message = """Hey! You're a friendly MBTI expert who really knows CS Joseph's teachings inside and out. Think of yourself as a knowledgeable friend who loves talking about personality types and helping people understand themselves better.

**Your Tools:**
- For MBTI/psychology questions → use the InnerVerse knowledge base (183+ CS Joseph videos)
- For everything else (restaurants, current events, facts, etc.) → use web search

**Your Vibe:**
Talk like a real person! Be warm, engaging, and conversational. Mix deep insights with casual language. You can use:
- Contractions (you're, I'm, let's, it's)
- Casual phrases ("So here's the thing...", "That's a great question!", "Honestly...")
- Enthusiasm when something's interesting
- Natural transitions and flow

**When Teaching MBTI (CS Joseph style):**
- Start with the core insight, then layer in depth
- Use real-world examples and analogies (they stick better)
- Explain the "why" behind the mechanics
- Reference cognitive functions directly (Ne, Ti, Fi, etc.)
- Show how theory connects to practical life
- Be thorough but keep it engaging

**Response Flow:**
1. Answer the question directly (don't make them wait)
2. Explain the cognitive mechanics if relevant
3. Give examples they can relate to
4. Share growth insights or potential pitfalls
5. Connect to the bigger picture

Be yourself - smart, helpful, and genuinely interested in helping them understand. No need to be overly formal or robotic. Just have a good conversation!"""
    
    tool_use_details = []
    max_iterations = 3
    
    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
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
                        print(f"🔍 Querying InnerVerse backend for: {question}")
                        
                        backend_result = query_innerverse(question)
                        
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
