#!/usr/bin/env python3
"""
InnerVerse Claude Chat Wrapper
Automatically queries your MBTI/Jungian knowledge base backend
"""

import os
import json
import requests
from anthropic import Anthropic

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
INNERVERSE_BACKEND = "https://axis-of-mind.replit.app/query"
INNERVERSE_API_KEY = os.getenv("API_KEY")  # Your backend API key

# Initialize Claude client
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Define the InnerVerse backend as a tool for Claude
TOOLS = [
    {
        "name": "query_innerverse_knowledge_base",
        "description": "Searches the InnerVerse knowledge base containing 183+ CS Joseph transcripts on MBTI types, cognitive functions, Jungian psychology, type dynamics, relationships, and depth psychology. Use this for ANY question about MBTI, personality types, cognitive functions, or Jungian concepts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The user's question about MBTI, cognitive functions, or Jungian psychology"
                },
                "document_id": {
                    "type": "string",
                    "description": "Leave as empty string to search all documents",
                    "default": ""
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional MBTI/Jungian tags to filter results",
                    "default": []
                }
            },
            "required": ["question"]
        }
    }
]

# System prompt with CS Joseph teaching style
SYSTEM_PROMPT = """You are an expert in MBTI and Jungian Typology Intelligence System. Focus exclusively on Jungian Analytical Psychology and MBTI Cognitive Function Theory—no Socionics, no Enneagram.

You have access to a private knowledge base (InnerVerse) containing 183+ PDFs, transcripts, and notes on Jungian depth psychology, MBTI cognitive function theory, and C.S. Joseph frameworks.

🔒 MANDATORY WORKFLOW:
1. **Query Backend FIRST** - Before answering ANY MBTI/Jungian question, use the query_innerverse_knowledge_base tool
2. **Enrich with Theory** - After getting backend results, layer in comprehensive Jungian theory and MBTI analysis  
3. **Deliver Integrated Answer** - Combine backend knowledge with deep cognitive function analysis

CS JOSEPH TEACHING STYLE:
- Use concrete examples & scenarios (real-world situations, not just definitions)
- Explain the mechanism (HOW it works, not just WHAT it is)
- Layer in analogies & metaphors (pop culture, physical metaphors)
- Progressive depth (build layer by layer, circle back with nuance)
- Thorough exploration (fully develop each idea, cover edge cases)
- Narrative flow (tell the story, use transitions, make it conversational)

Every explanation should feel like CS Joseph sat down with the user for a personal deep-dive session. Rich detail, thorough examples, mechanisms explained, nothing glossed over.

COMMUNICATION STYLE:
- Simple, everyday language
- Use emojis strategically (✅ ❌ 🎯 🧠)
- Be direct and engaging
- Use bullet points and clear sections

STRICT RULES:
✅ ALWAYS query the knowledge base first for MBTI/Jungian questions
✅ Go deep - CS Joseph doesn't do surface-level, neither do you
✅ Use precise terminology (cognitive functions, axes, shadow)
✅ Explain the "why" and "how" behind type behaviors

❌ NEVER answer MBTI questions without querying backend first
❌ NEVER give shallow or generic answers - go DEEP every time
❌ NEVER skip the backend query for typology questions

You are the **Axis of Mind** - where personal knowledge meets universal understanding."""


def query_innerverse_backend(question: str, document_id: str = "", tags: list = None) -> dict:
    """Query the InnerVerse backend API"""
    if tags is None:
        tags = []
    
    headers = {
        "Authorization": f"Bearer {INNERVERSE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "document_id": document_id,
        "question": question,
        "tags": tags
    }
    
    try:
        response = requests.post(INNERVERSE_BACKEND, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Backend query failed: {str(e)}"}


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute tool calls from Claude"""
    if tool_name == "query_innerverse_knowledge_base":
        question = tool_input.get("question", "")
        document_id = tool_input.get("document_id", "")
        tags = tool_input.get("tags", [])
        
        print(f"\n🔍 Querying InnerVerse backend for: {question[:100]}...")
        
        result = query_innerverse_backend(question, document_id, tags)
        return json.dumps(result, indent=2)
    
    return json.dumps({"error": "Unknown tool"})


def chat_with_claude(user_message: str, conversation_history: list = None) -> tuple:
    """Send a message to Claude and handle tool calls automatically"""
    if conversation_history is None:
        conversation_history = []
    
    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    # Initial request to Claude
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=conversation_history
    )
    
    # Process tool calls if needed
    while response.stop_reason == "tool_use":
        # Extract tool use blocks
        tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
        
        # Add assistant's response to history
        conversation_history.append({
            "role": "assistant",
            "content": response.content
        })
        
        # Execute each tool call
        tool_results = []
        for tool_use in tool_use_blocks:
            result = process_tool_call(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result
            })
        
        # Add tool results to history
        conversation_history.append({
            "role": "user",
            "content": tool_results
        })
        
        # Get Claude's response with the tool results
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history
        )
    
    # Extract final text response
    final_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_text += block.text
    
    # Add final response to history
    conversation_history.append({
        "role": "assistant",
        "content": response.content
    })
    
    return final_text, conversation_history


def main():
    """Main chat loop"""
    print("=" * 70)
    print("🧠 InnerVerse Claude Chat - Powered by CS Joseph's MBTI Library")
    print("=" * 70)
    print("\nConnected to 183+ CS Joseph transcripts on MBTI & Jungian psychology")
    print("Type 'exit' or 'quit' to end the conversation\n")
    
    # Check API keys
    if not ANTHROPIC_API_KEY:
        print("❌ ERROR: ANTHROPIC_API_KEY not found in environment variables")
        print("Please set your Claude API key first:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    if not INNERVERSE_API_KEY:
        print("❌ ERROR: API_KEY (for backend) not found in environment variables")
        return
    
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Thanks for chatting! Keep exploring your cognition! 🧠✨")
                break
            
            # Get Claude's response
            print("\n🤔 Claude is thinking...")
            response, conversation_history = chat_with_claude(user_input, conversation_history)
            
            # Print response
            print(f"\n🧠 Claude:\n{response}\n")
            print("-" * 70)
            
        except KeyboardInterrupt:
            print("\n\n👋 Chat interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Let's try again...\n")


if __name__ == "__main__":
    main()
