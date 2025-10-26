# Overview

InnerVerse is a FastAPI-based PDF Q&A application for intelligent knowledge retrieval. It allows users to upload PDFs, transcribe audio and YouTube videos into searchable documents, and generate reports. It chunks, embeds, and stores document content in Pinecone, leveraging OpenAI's GPT models for query answering. The application also monitors API usage, tracks costs, and applies rate limiting, providing an intuitive experience for document interaction.

# Recent Changes

- **v2 Optimized Prompt Working Perfectly (Oct 26, 2025)**: Confirmed that v2 "CS Joseph Typology Expert (Optimized)" prompt is working perfectly - delivers exactly the quality responses needed. Version history: v1 = original "Jungian-MBTI Integration System", v2 = lighter/optimized (CURRENT), v3 = deeper/comprehensive (too complex, caused hanging). Simplified 3-step workflow (Query → Build → Teach) with CS Joseph teaching style. Backup saved in `SYSTEM_PROMPT_V2_WORKING.md`. Timeouts remain in place (10s Pinecone, 60s Claude) for safety.
- **Fixed Pinecone Query Timeout Issue (Oct 26, 2025)**: Added 10-second timeout protection to all Pinecone queries in both `claude_api.py` and `main.py`. Queries now fail gracefully with user-friendly error messages instead of hanging indefinitely when knowledge base searches stall.
- **Hybrid Search System Upgrade (Oct 26, 2025)**: Upgraded to text-embedding-3-large (3072 dims) with improved chunking (2500 chars, 20% overlap), enriched metadata extraction (season/episode, MBTI types, cognitive functions), smart query rewriting with MBTI ontology, and hybrid retrieval (top_k=30 → re-rank to 12). Migration tool available at `/migration`.
- Enhanced Pinecone search: doubled results from 5 to 10 chunks, added query expansion with 2 variations for better intent matching
- **Fixed Enter key behavior (Oct 26, 2025)**: Plain Enter creates new line on iPhone (disabled Shift+Enter on mobile due to auto-capitalization). Desktop: Shift+Enter sends, mobile: use Send button.
- **Project Cleanup (Oct 26, 2025)**: Deleted unused files (CLAUDE_PROJECT_INSTRUCTIONS.md, old Claude app versions v12-v18, claude_wrapper directory) for better project organization.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Interface**: Single-page application with a glassmorphic UI, animated SVG brain icon, purple gradient theme, and a live visual cost tracker. Features include Light/Dark mode, drag-and-drop PDF uploads, Google Drive integration, YouTube MP3 transcription, and a cloud-based visual tag library.
- **Chat Flow**: iPhone-style chat for document Q&A and management.
- **Claude Master Interface** (`/claude`): Advanced conversational workspace powered by Claude Sonnet 4 with a ChatGPT-style interface. It features 7 project categories, persistent conversations in PostgreSQL, a responsive sidebar with full-height design (desktop fixed, mobile overlay), a welcome screen with suggested prompts, and robust state management. Integrates automatic InnerVerse backend queries and web search via Claude API function calling. Supports PWA for mobile installation.
  - **Sidebar**: Fixed-position, full-height sidebar with search, "InnerVerse" home, collapsible "All Chats" and "Projects" sections. Optimized for performance with parallel preloading and instant response times.
  - **Browser History Routing**: Full browser back/forward support using HTML5 History API.
  - **Conversation List**: Compact, ChatGPT-style design with single-line items, timestamps, inline rename/delete icons, and optimistic UI updates for instant operations.
  - **Auto-Expanding Textarea**: Input grows from 1 to 5 lines.
  - **Streaming Responses**: Typewriter effect displays AI responses in 5-character chunks every 8ms with optimized scrolling. Markdown formatted with headers, bold text, bullets, and 1-2 emojis max for scannability.
  - **iOS Optimization**: Optimized for iPhone 14 Pro with viewport locking and safe area handling.
  - **Thinking Indicator**: Subtle pulsing dot with "thinking" text appears during AI processing.
  - **Offline Resilience**: PWA-optimized message persistence, handles interrupted API calls and app backgrounding.
  - **Performance**: Achieved through HTML template strings (10x faster rendering), event delegation, optimistic UI updates, DOM element caching, parallel API fetches, debounced input handlers, and batch rendering.
- **Migration Dashboard** (`/migration`): Real-time dashboard for upgrading embeddings from ada-002 to 3-large with progress tracking, stats visualization, and live console logs.

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations, Python runtime, and Uvicorn ASGI server.
- **Design Pattern**: Stateless API where `document_id` is managed by the frontend.
- **Deployment**: VM deployment with health checks, robust database initialization, and detailed logging.
- **API Usage and Cost Tracking**: Logs and persists OpenAI API call costs to PostgreSQL, accessible via `/api/usage`, with a rate limit of 100 requests per hour.
- **Migration System**: Background task-based migration API (`/api/start-migration`, `/api/migration-status`) for live embedding upgrades without downtime.

## Document Processing Pipeline
- **PDF Parsing**: PyPDF2 for text extraction, including encrypted PDFs.
- **Text Chunking**: LangChain's `RecursiveCharacterTextSplitter` with improved parameters (2500 chars, 500 overlap, paragraph-aware) for CS Joseph transcripts.
- **InnerVerse Intelligence Layer**: Automatic MBTI/Jungian taxonomy tagging using GPT-3.5, storing tags in Pinecone metadata.
- **Enriched Metadata Extraction**: Automatically extracts season/episode numbers, MBTI types mentioned, and cognitive functions from filenames and content.
- **YouTube MP3 Transcription**: Processes audio (MP3, M4A, WAV, MP4) up to 24MB via OpenAI Whisper API, generates formatted PDFs using ReportLab, auto-tags, and indexes in Pinecone.
- **Text to PDF**: Converts text to formatted PDFs with GPT-3.5 for punctuation and grammar fixes.
- **Reprocess PDF**: Enhances existing Whisper-transcribed PDFs.
- **Large File Support**: Efficient binary uploads and batch processing for Pinecone upserts.

## Vector Storage Strategy
- **Database**: Pinecone vector database.
  - **Production Index**: `mbti-knowledge` (1536 dims, ada-002) - 245 documents
  - **New Index**: `mbti-knowledge-v2` (3072 dims, 3-large) - migration target
- **Query Strategy**: Hybrid search with vector similarity + metadata filters + smart re-ranking.

## Embedding Generation
- **Current**: OpenAI `text-embedding-3-large` (3072 dimensions) for superior semantic matching
- **Legacy**: `text-embedding-ada-002` (1536 dimensions) - being phased out via migration

## Hybrid Search System
- **Query Rewriting**: MBTI ontology-aware with type synonyms (ESTP → "Se-Ti extraverted sensing")
- **Retrieval**: top_k=30 initial fetch → metadata filtering → re-rank to 12 best chunks
- **Semantic Expansion**: Auto-expands negative behavior queries, relationship queries, and function-based queries
- **Context Length**: 12 chunks × ~2500 chars = ~30,000 chars of context for Claude

## API Structure
- **Upload**: `POST /upload`, `POST /upload-base64` (PDFs), `POST /upload-audio` (audio).
- **Query**: `POST /query`.
- **Text/PDF Processing**: `POST /text-to-pdf`, `POST /reprocess-pdf`.
- **Document Management**: `GET /documents/report`, `DELETE /documents/{document_id}`, `DELETE /documents/all`, `PATCH /documents/{document_id}/rename`, chat commands.
- **Claude Chat API**: Endpoints for managing project categories, conversations, messages, and searching.
- **Migration API**: `POST /api/start-migration`, `GET /api/migration-status`.
- **Usage Monitoring**: `/api/usage`.
- **Static Files**: Serves frontend assets and Swagger UI documentation.
- **PWA Support**: Service worker, manifest, and icons.
- **CORS**: Enabled for all origins.

## Configuration Management
- **Environment Variables**: API keys managed via Replit Secrets.
  - `PINECONE_INDEX`: Current production index name
  - `NEW_PINECONE_INDEX`: Migration target index name (mbti-knowledge-v2)
- **Client Initialization**: Lazy initialization for API clients.

# External Dependencies

## Vector Database
- **Pinecone**: Vector database for document embeddings.

## AI/ML Services
- **OpenAI API**: For text embeddings (`text-embedding-3-large`), GPT-3.5-turbo (Q&A, text fixes), and Whisper API (audio transcription).
- **Anthropic API**: Claude Sonnet 4 for the Claude Master Interface.

## Document Processing
- **PyPDF2**: PDF parsing.
- **LangChain**: Text splitting.
- **ReportLab**: PDF generation.
- **ffmpeg**: System dependency for audio processing.
- **poppler**: System dependency for PDF rendering.
- **tesseract**: System dependency for OCR.

## Data Storage
- **PostgreSQL**: For persistent cost tracking and Claude conversation history.

## Web Framework
- **FastAPI**: Python web framework.
- **Uvicorn**: ASGI server.
- **Pydantic**: Data validation.

## Integrations
- **Google Drive Picker API**: Google Drive integration.
- **yt-dlp**: YouTube video downloading.
- **Brave Search API**: Web search integration.

# Migration Guide

To upgrade from ada-002 to 3-large embeddings:

1. **Create New Pinecone Index**:
   - Dimensions: 3072
   - Metric: cosine
   - Name: `mbti-knowledge-v2`

2. **Set Environment Variable**:
   ```
   NEW_PINECONE_INDEX=mbti-knowledge-v2
   ```

3. **Run Migration**:
   - Visit `/migration` dashboard
   - Click "Start Migration"
   - Monitor real-time progress

4. **Switch to New Index**:
   - After successful migration, update `PINECONE_INDEX=mbti-knowledge-v2`
   - Restart application

5. **Verify & Cleanup**:
   - Test search quality
   - Delete old `mbti-knowledge` index once verified
