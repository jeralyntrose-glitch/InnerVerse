# InnerVerse Claude Chat Wrapper

Automatically query your MBTI/Jungian knowledge base using Claude API with function calling!

## Features

✅ **Automatic Backend Queries** - Claude automatically calls your InnerVerse backend  
✅ **CS Joseph Teaching Style** - Deep, detailed explanations with examples and mechanisms  
✅ **No Manual Work** - Just ask questions, Claude handles everything  
✅ **Conversation History** - Multi-turn conversations with context  

## Setup

### 1. Get Your Claude API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to **Settings** → **API Keys**
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

### 2. Set Environment Variable

In your Replit Secrets (🔒 icon in left sidebar):

- **Key:** `ANTHROPIC_API_KEY`  
- **Value:** Your Claude API key (from step 1)

Your `API_KEY` (for the backend) is already set up!

### 3. Run the Chat

```bash
python claude_wrapper/claude_chat.py
```

## Usage

Just ask any MBTI or Jungian psychology question:

```
💬 You: Explain the golden pair dynamic between ENFP and INFJ

🤔 Claude is thinking...
🔍 Querying InnerVerse backend for: Explain the golden pair dynamic between ENFP and INFJ...

🧠 Claude:
[CS Joseph-level deep explanation with backend data + enrichment]
```

## Example Questions

- "What's the difference between Ti and Te?"
- "How do INTJs use their Ni-Te axis?"
- "Explain shadow functions for ENFPs"
- "What causes INFJ door slam behavior?"
- "How do ENTP and INTJ interact in relationships?"

## How It Works

1. You ask a question
2. Claude recognizes it needs backend data
3. Script automatically queries your InnerVerse API
4. Claude receives the CS Joseph transcript data
5. Claude enriches it with comprehensive theory
6. You get a deep, detailed answer!

**No manual curl commands. No copy-pasting. Just chat!** 🚀
