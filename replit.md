# Overview

InnerVerse is a FastAPI-based PDF Q&A application designed for intelligent knowledge retrieval. It enables users to upload PDFs, transcribe audio and YouTube videos into searchable documents, and generate reports. The system leverages chunking, embedding, and storage in Pinecone, using OpenAI's GPT models for query answering. It also includes features for API usage monitoring, cost tracking, and rate limiting, providing an intuitive document interaction experience. The project delivers a professional Claude.ai-inspired chat interface with Phase 4 UX polish, featuring markdown rendering, professional color scheme, animated typing indicators, and full mobile optimization.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **UI/UX (Phase 4 - Professional Design)**: Claude.ai-inspired professional interface with clean, spacious aesthetic. Features Inter font, exact professional color scheme (#10A37F teal user bubbles, #F7F7F8 grey AI backgrounds), full markdown rendering (headers, code blocks, lists, links), animated typing indicator, and responsive mobile design. Glassmorphic header with purple gradient remains for branding.
- **Chat Interface (`/chat` and `/claude`)**: A professional, Claude.ai-inspired chat interface with full feature parity. It uses a clean, minimal aesthetic with neutral colors and the Inter font. Key features include:
    - **Sidebar**: Collapsible project folders (7 categories) with compact 4px spacing, no descriptions shown, search functionality for conversations and messages, and conversation management (load, rename, delete). Mobile-optimized with burger menu that stays closed during background refreshes (renderSidebar preserves closed state), auto-closes on conversation selection, and batch-fetches all data before rendering to prevent flickering.
    - **Conversation Management**: Persistent conversation history stored in PostgreSQL, smart auto-naming for new chats, and responsive design for mobile. "All Chats" section displays all conversations across all projects (up to 100, sorted by most recent).
    - **Background Message Processing**: Uses `/message/background` endpoint for iOS PWA compatibility. Messages are saved immediately with "processing" status, processed server-side in background (even when app is closed), and completed responses are delivered via 3-second polling. This ensures messages complete even when user switches away from the app.
    - **Real-time Updates**: 3-second polling for conversation status checks unread responses and processing messages. Background refreshes skip renderSidebar() to prevent sidebar from reopening on mobile.
    - **PWA Support**: Full Progressive Web App capabilities including offline support, installability, and manifest configuration with professional teal brain icon.
    - **Performance**: Optimized for speed using HTML template strings, event delegation, optimistic UI updates, and parallel API fetches.
    - **Chat Styling (Phase 4)**: 
        - **User messages**: Teal bubbles (#10A37F) with white text, right-aligned, 70% max-width (85% on mobile), 18px border-radius, subtle shadow
        - **AI messages**: Full-width grey background (#F7F7F8), 24px padding (16px mobile), markdown rendered with syntax highlighting for code blocks
        - **Typography**: Inter font, 16px base, 1.6 line-height, professional color scheme (#2D2D2D primary text)
        - **Typing Indicator**: Animated dots during AI response generation
        - **Markdown Support**: Full rendering via marked.js - headers, bold, italic, code blocks, lists, blockquotes, links (open in new tab)
    - **Vision/Image Analysis**: Full Claude vision mode support for image upload and analysis via background processing. Users can upload images (JPEG, PNG, GIF, WebP up to 5MB) via the paperclip button, see image previews before sending, and receive AI analysis. Images display inline within chat messages with proper styling.
- **Migration Dashboard (`/migration`)**: Provides a real-time dashboard for upgrading embeddings with progress tracking and live logs.

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations, Python runtime, and Uvicorn ASGI server.
- **Design Pattern**: Stateless API where `document_id` is managed by the frontend.
- **Deployment**: VM deployment with health checks, robust database initialization, and detailed logging.
- **API Management**: Logs and persists OpenAI API call costs to PostgreSQL, accessible via `/api/usage`, with a rate limit of 100 requests per hour.
- **Migration System**: Background task-based API (`/api/start-migration`, `/api/migration-status`) for live embedding upgrades.

## Document Processing Pipeline
- **PDF Parsing**: Uses PyPDF2 for text extraction, including encrypted PDFs.
- **Text Chunking**: LangChain's `RecursiveCharacterTextSplitter` with optimized parameters (2500 chars, 500 overlap) for CS Joseph transcripts.
- **Intelligence Layer**: Automatic MBTI/Jungian taxonomy tagging using GPT-3.5, with tags stored in Pinecone metadata.
- **Metadata Extraction**: Extracts season/episode numbers, MBTI types, and cognitive functions from filenames and content.
- **Audio/Video Processing**: OpenAI Whisper API for transcribing audio (MP3, M4A, WAV, MP4) up to 24MB, generating formatted PDFs via ReportLab, and indexing in Pinecone. `yt-dlp` for YouTube video downloading.
- **Text to PDF**: Converts text to formatted PDFs with GPT-3.5 for punctuation and grammar fixes.
- **Large File Support**: Efficient binary uploads and batch processing for Pinecone upserts.

## Vector Storage and Search
- **Vector Database**: Pinecone.
    - **Production Index**: `mbti-knowledge` (1536 dims, ada-002).
    - **Migration Target**: `mbti-knowledge-v2` (3072 dims, 3-large).
- **Embedding Generation**: Primarily `text-embedding-3-large` (3072 dimensions) with `text-embedding-ada-002` as legacy.
- **Hybrid Search System**: Combines vector similarity with metadata filters and smart re-ranking (top_k=30 initial fetch, re-ranked to 12). Includes MBTI ontology-aware query rewriting and semantic expansion for various query types. Context length for Claude is 12 chunks (~30,000 characters).

## API Structure
- **Core APIs**: `POST /upload`, `POST /upload-base64`, `POST /upload-audio`, `POST /query`, `POST /text-to-pdf`, `POST /reprocess-pdf`.
- **Document Management**: `GET /documents/report`, `DELETE /documents/{document_id}`, `DELETE /documents/all`, `PATCH /documents/{document_id}/rename`, and chat commands.
- **Claude Chat API**: Endpoints for managing project categories, conversations, and messages. Includes `GET /claude/conversations/all/list` for fetching all conversations across projects.
- **OpenAI-Compatible API**: `GET /v1/models`, `POST /v1/chat/completions` for LibreChat integration, wrapping Claude and Pinecone functionality.
- **System APIs**: Migration (`/api/start-migration`, `/api/migration-status`) and usage monitoring (`/api/usage`).
- **Static Files**: Serves frontend assets and Swagger UI.
- **CORS**: Enabled for all origins.

## Configuration Management
- **Environment Variables**: API keys managed via Replit Secrets (`PINECONE_INDEX`, `NEW_PINECONE_INDEX`).
- **Client Initialization**: Lazy initialization for API clients.

# External Dependencies

## Vector Database
- **Pinecone**: For storing and querying document embeddings.

## AI/ML Services
- **OpenAI API**: For text embeddings (`text-embedding-3-large`), GPT-3.5-turbo (Q&A, text fixes), and Whisper API (audio transcription).
- **Anthropic API**: Claude Sonnet 4 for advanced conversational capabilities.

## Document Processing
- **PyPDF2**: PDF parsing.
- **LangChain**: Text splitting.
- **ReportLab**: PDF generation.
- **ffmpeg**: System dependency for audio processing.
- **poppler**: System dependency for PDF rendering.
- **tesseract**: System dependency for OCR.

## Data Storage
- **PostgreSQL**: For persistent cost tracking and conversation history.

## Web Framework
- **FastAPI**: Python web framework.
- **Uvicorn**: ASGI server.
- **Pydantic**: Data validation.

## Integrations
- **Google Drive Picker API**: For Google Drive integration.
- **yt-dlp**: For YouTube video downloading.
- **Brave Search API**: For web search integration.