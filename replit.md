# Overview

InnerVerse is a FastAPI-based PDF Q&A application designed for intelligent knowledge retrieval. It enables users to upload PDFs, transcribe audio and YouTube videos into searchable documents, and generate reports. The system leverages chunking, embedding, and storage in Pinecone, using OpenAI's GPT models for query answering. It also includes features for API usage monitoring, cost tracking, and rate limiting, providing an intuitive document interaction experience. The project aims to deliver a professional chat interface, inspired by platforms like Claude.ai, with robust features for conversation management, persistent history, and PWA capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **UI/UX**: Features a glassmorphic design, animated SVG brain icon, purple gradient theme, and a live visual cost tracker. Includes Light/Dark mode, drag-and-drop PDF uploads, Google Drive integration, YouTube MP3 transcription, and a cloud-based visual tag library.
- **Chat Interface (`/chat` and `/claude`)**: A professional, Claude.ai-inspired chat interface with full feature parity. It uses a clean, minimal aesthetic with neutral colors and the Inter font. Key features include:
    - **Sidebar**: Collapsible project folders (7 categories), search functionality for conversations and messages, and conversation management (load, rename, delete).
    - **Conversation Management**: Persistent conversation history stored in PostgreSQL, smart auto-naming for new chats, and responsive design for mobile.
    - **Real-time Interaction**: SSE streaming for AI responses with a typewriter effect, optimized scrolling, and a "thinking" indicator.
    - **PWA Support**: Full Progressive Web App capabilities including offline support, installability, and manifest configuration.
    - **Performance**: Optimized for speed using HTML template strings, event delegation, optimistic UI updates, and parallel API fetches.
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
- **Claude Chat API**: Endpoints for managing project categories, conversations, and messages.
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