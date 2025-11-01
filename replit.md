# Overview

InnerVerse is a FastAPI-based PDF Q&A application that provides intelligent knowledge retrieval from various sources, including uploaded PDFs, transcribed audio, and YouTube videos. It leverages chunking, embedding, and Pinecone storage, utilizing OpenAI's GPT models and Anthropic's Claude for query answering and report generation. The project aims to deliver a professional, intuitive document interaction experience with a Claude.ai-inspired chat interface, featuring advanced UX, mobile optimization, API usage monitoring, and cost tracking.

# User Preferences

Preferred communication style: Simple, everyday language with a decent amount of emojis (not excessive, but engaging).

# System Architecture

## Frontend Architecture
- **UI/UX (Sleek Compact Design)**: Apple-inspired minimalist interface with a professional productivity tool aesthetic, featuring lighter ChatGPT-style typography (Inter font), a thin header, teal accent colors, and compact spacing.
- **Branding**: "InnerVerse" title uses a thin Outfit font with increased letter-spacing, accompanied by a simplified teal brain logo.
- **Chat Interface (`/chat` and `/claude`)**: A professional, Claude.ai/ChatGPT-inspired interface with:
    - **Sidebar**: Collapsible project folders, conversation management (load, rename, delete), and mobile optimization.
    - **Search Functionality**: Comprehensive backend search for conversation titles and message content with debounce, real-time filtering, and XSS protection.
    - **Copy Message Functionality**: One-click copy for all messages, intelligently stripping markdown from AI responses.
    - **Conversation Management**: Persistent history in PostgreSQL, smart auto-naming, and responsive design.
    - **Background Message Processing**: Uses a dedicated endpoint for iOS PWA compatibility, ensuring messages complete server-side.
    - **Real-time Updates**: 3-second polling for conversation status and unread responses.
    - **PWA Support**: Full Progressive Web App implementation with manifest, icons, service worker, custom install UI, and iOS support.
    - **Performance**: Optimized with HTML template strings, event delegation, optimistic UI, and parallel API fetches.
    - **Chat Styling**: ChatGPT-inspired minimal design with distinct user and AI message styling, auto-expanding textarea, full markdown rendering via `marked.js`, and enhanced visual hierarchy (bold teal headings with H1: 28px/700, H2: 24px/600, H3: 20px/600, increased spacing, and emoji-friendly design for engaging, scannable responses).
    - **Security**: Comprehensive XSS protection via DOMPurify, HTML escaping, and DOM API value assignment.
    - **Vision/Image Analysis**: Multi-image upload (2-5 images) and analysis using Claude Sonnet 4 Vision API. Features client-side automatic image compression (3MB target per image accounting for base64 encoding overhead, using canvas API with progressive quality reduction 0.9→0.5), horizontal scrollable thumbnail preview with individual remove buttons, bulk "Clear All" option, grid layout display in chat for multiple images, and inline image display. GIF/WebP animations preserved up to 3.75MB. Backend accepts both single `image` and multi-image `images` array for backward compatibility.
    - **Dark/Light Mode**: Full theme switching with persistent localStorage preference and a comprehensive CSS custom property system.
- **Migration Dashboard (`/migration`)**: Real-time dashboard for upgrading embeddings with progress tracking.
- **AXIS MIND Uploader (`/uploader`)**: Document upload and management interface with drag & drop PDF upload, YouTube transcription, Text-to-PDF conversion with AI grammar fixes, tag library, API cost tracker, and document reporting.

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations, Python runtime, and Uvicorn.
- **Design Pattern**: Stateless API.
- **Deployment**: VM deployment with health checks and robust logging.
- **API Management**: Logs OpenAI API costs to PostgreSQL, accessible via `/api/usage`, with a rate limit.
- **Retry Logic**: Automatic retry with exponential backoff for Claude API overload errors (2s, then 4s, max 3 attempts). User-friendly error messages after exhausting retries.
- **Migration System**: Background task-based API for live embedding upgrades.

## Document Processing Pipeline
- **PDF Parsing**: PyPDF2 for text extraction.
- **Text Chunking**: LangChain's `RecursiveCharacterTextSplitter` with optimized parameters.
- **Intelligence Layer**: Automatic MBTI/Jungian taxonomy tagging using GPT-3.5, stored in Pinecone metadata.
- **Metadata Extraction**: Extracts season/episode, MBTI types, and cognitive functions.
- **Audio/Video Processing**: OpenAI Whisper API for transcription, ReportLab for PDF generation, and `yt-dlp` for YouTube downloads.
- **Text to PDF**: Converts text to formatted PDFs with GPT-3.5 for grammar correction.
- **Large File Support**: Efficient binary uploads and batch processing for Pinecone upserts.

## Vector Storage and Search
- **Vector Database**: Pinecone (`mbti-knowledge` production index, `mbti-knowledge-v2` migration target).
- **Embedding Generation**: Primarily `text-embedding-3-large` (3072 dimensions) with `text-embedding-ada-002` as legacy.
- **Hybrid Search System**: Combines vector similarity with metadata filters, smart re-ranking, and MBTI ontology-aware query rewriting.

## API Structure
- **Core APIs**: For upload (PDF, audio, base64), querying, text-to-PDF conversion, and re-processing.
- **Document Management**: CRUD operations for documents and chat commands.
- **Claude Chat API**: Endpoints for managing project categories, conversations, and messages.
- **OpenAI-Compatible API**: `/v1/models` and `/v1/chat/completions` for LibreChat integration, wrapping Claude and Pinecone.
- **System APIs**: Migration and usage monitoring.
- **Static Files**: Serves frontend assets and Swagger UI.
- **CORS**: Enabled for all origins.

## Configuration Management
- **Environment Variables**: API keys managed via Replit Secrets.
- **Client Initialization**: Lazy initialization for API clients.

# External Dependencies

## Vector Database
- **Pinecone**: For storing and querying document embeddings.

## AI/ML Services
- **OpenAI API**: For text embeddings, GPT-3.5-turbo (Q&A, text fixes), and Whisper API (audio transcription).
- **Anthropic API**: Claude Sonnet 4 for conversational AI.

## Document Processing
- **PyPDF2**: PDF parsing.
- **LangChain**: Text splitting.
- **ReportLab**: PDF generation.
- **ffmpeg**: For audio processing.
- **poppler**: For PDF rendering.
- **tesseract**: For OCR.

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