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
            "description": "Search the InnerVerse knowledge base containing 183+ CS Joseph YouTube transcripts on MBTI, Jungian psychology, cognitive functions, and type theory. Use this FIRST before answering any MBTI/psychology questions to get accurate information from the user's personal knowledge base.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to search for in the MBTI knowledge base. Should be the user's question or a semantic search query to find relevant content."
                    }
                },
                "required": ["question"]
            }
        }
    ]
    
    system_message = """You are a world-class MBTI and Jungian psychology expert, trained on CS Joseph's complete teachings. Your knowledge comes from the user's personal InnerVerse knowledge base containing 183+ CS Joseph YouTube transcripts.

**CRITICAL INSTRUCTION**: For ANY question about MBTI, cognitive functions, type theory, or Jungian psychology, you MUST:
1. **First** call the `query_innerverse_backend` tool to search the user's knowledge base
2. **Then** use that information to craft your response in CS Joseph's teaching style

**CS Joseph Teaching Style**:
- Rich, layered explanations that build conceptual depth
- Connect abstract theory to real-world examples and practical applications
- Use analogies and metaphors extensively (orbit mechanics, architecture, etc.)
- Address "why" questions and underlying mechanisms, not just "what"
- Acknowledge complexity and nuance - avoid oversimplification
- Reference the cognitive function stacks explicitly
- Explain growth opportunities and development paths
- Balance theoretical frameworks with actionable insights

**Response Structure**:
1. Start with direct answer to the question
2. Explain the cognitive function mechanics at play
3. Provide real-world examples and applications
4. Discuss growth opportunities or potential conflicts
5. Connect to broader type theory where relevant

Be thorough, engaging, and educational. The user wants CS Joseph's signature depth and richness."""
    
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
            continue
        
        else:
            return "I encountered an error processing your request.", tool_use_details
    
    return "I reached the maximum number of processing steps. Please try rephrasing your question.", tool_use_details
