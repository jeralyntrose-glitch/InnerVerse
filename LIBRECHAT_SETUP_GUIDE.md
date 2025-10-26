# LibreChat Integration Guide for InnerVerse

This guide explains how to connect LibreChat (an open-source AI chat UI) to your InnerVerse backend, giving you a professional chat interface while keeping all your CS Joseph typology intelligence!

## ✅ What's Already Done

Your InnerVerse backend now has **OpenAI-compatible API endpoints** that LibreChat can connect to:

- **`/v1/chat/completions`** - Streaming chat endpoint (wraps Claude + Pinecone)
- **`/v1/models`** - Lists available models

These endpoints convert LibreChat's OpenAI-format requests to your Claude backend and stream responses back in OpenAI format.

---

## 📋 Prerequisites

Before setting up LibreChat, install:

1. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)
   - Required for running LibreChat
   - Make sure it's running before proceeding

2. **Git** - [Download here](https://git-scm.com/downloads)
   - For cloning the LibreChat repository

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Clone & Configure LibreChat

```bash
# Clone LibreChat
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat

# Copy environment template
cp .env.example .env
```

### Step 2: Create Custom Endpoint Configuration

Create a file named `librechat.yaml` in the LibreChat directory:

```yaml
version: 1.2.8
cache: true

endpoints:
  custom:
    - name: "InnerVerse"
      apiKey: "user_provided"  # LibreChat will ask users for their key
      baseURL: "http://host.docker.internal:5000/v1"  # Your InnerVerse backend
      models:
        default: ["innerverse-claude-sonnet-4"]
        fetch: true  # Try to fetch models from /v1/models endpoint
      titleConvo: true
      titleModel: "innerverse-claude-sonnet-4"
      summarize: false
      summaryModel: "innerverse-claude-sonnet-4"
      forcePrompt: false
      modelDisplayLabel: "InnerVerse"
```

**Important Notes:**
- `http://host.docker.internal:5000/v1` - This URL lets LibreChat (running in Docker) talk to your InnerVerse backend (running on your host machine on port 5000)
- `apiKey: "user_provided"` - LibreChat will prompt users to enter an API key (you can use any value since InnerVerse doesn't currently require authentication)

### Step 3: Mount Configuration in Docker

Create `docker-compose.override.yml`:

```yaml
services:
  api:
    volumes:
      - ./librechat.yaml:/app/librechat.yaml
```

---

## 🎯 Start LibreChat

```bash
# Make sure Docker Desktop is running, then:
docker compose up -d
```

**Access LibreChat:**
Open your browser to `http://localhost:3080`

---

## 🔧 Configuration Options

### For Replit Deployment

If you're running InnerVerse on Replit (https://axis-of-mind.replit.app):

```yaml
baseURL: "https://axis-of-mind.replit.app/v1"
```

### For Local Development

If both LibreChat and InnerVerse are running locally without Docker:

```yaml
baseURL: "http://localhost:5000/v1"
```

### Custom Headers (Optional)

Add authentication or custom headers:

```yaml
headers:
  X-Custom-Header: "value"
  Authorization: "Bearer your-token-here"
```

---

## 📝 First-Time Use

1. **Start InnerVerse Backend**
   - Make sure your InnerVerse server is running on port 5000
   - Check that `/v1/models` is accessible

2. **Start LibreChat**
   ```bash
   docker compose up -d
   ```

3. **Open LibreChat**
   - Visit `http://localhost:3080`
   - Create an account
   - Select "InnerVerse" from the model dropdown
   - Enter an API key when prompted (any value works for now)
   - Start chatting!

---

## ✨ What You Get

With LibreChat connected to InnerVerse, you'll have:

- **Professional UI** - Clean, modern chat interface
- **Full InnerVerse Intelligence** - All your Claude + Pinecone + CS Joseph knowledge
- **Conversation History** - Built-in chat history management
- **Multi-Model Support** - Easy to add more models later
- **File Uploads** - Drag and drop files (LibreChat feature)
- **Search** - Search through conversations
- **Export** - Export conversations to JSON/CSV

---

## 🔍 Testing the Connection

Before starting LibreChat, test that your InnerVerse endpoints work:

```bash
# Test models endpoint
curl http://localhost:5000/v1/models

# Test chat completions (non-streaming)
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "innerverse-claude-sonnet-4",
    "messages": [{"role": "user", "content": "What is MBTI?"}],
    "stream": false
  }'
```

---

## 🐛 Troubleshooting

### "Connection refused" error
- **Cause**: LibreChat can't reach your InnerVerse backend
- **Fix**: Check that InnerVerse is running on port 5000 and use `http://host.docker.internal:5000/v1` in the config

### Models not showing in LibreChat
- **Fix 1**: Make sure `/v1/models` endpoint returns valid JSON
- **Fix 2**: Set `fetch: false` and manually list models in `default: ["model-name"]`

### Empty or incomplete responses
- **Cause**: Streaming format mismatch
- **Fix**: Check server logs for errors in `/v1/chat/completions` endpoint

### Docker won't start
- **Fix**: Make sure Docker Desktop is running
- **Fix**: Try `docker compose down` then `docker compose up -d` again

---

## 🔄 Updating LibreChat

To update LibreChat to the latest version:

```bash
docker compose down
git pull
docker compose pull
docker compose up -d
```

---

## 📚 Additional Resources

- **LibreChat Documentation**: https://www.librechat.ai/docs
- **Custom Endpoints Guide**: https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/custom_endpoint
- **Docker Troubleshooting**: https://docs.docker.com/desktop/troubleshoot/overview/

---

## 🎉 Next Steps

Once LibreChat is running:

1. **Test basic chat** - Ask a typology question and verify you get CS Joseph-style responses
2. **Check conversation history** - Verify chats are being saved
3. **Explore features** - Try file uploads, search, and export
4. **Customize** - Add more models, change themes, configure settings

---

**You now have a professional chat UI powered by your InnerVerse intelligence backend!** 🧠✨
