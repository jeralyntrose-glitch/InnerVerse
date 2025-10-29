# Overview

InnerVerse is a FastAPI-based PDF Q&A application designed for intelligent knowledge retrieval. It enables users to upload PDFs, transcribe audio and YouTube videos into searchable documents, and generate reports. The system leverages chunking, embedding, and storage in Pinecone, using OpenAI's GPT models for query answering. It also includes features for API usage monitoring, cost tracking, and rate limiting, providing an intuitive document interaction experience. The project delivers a professional Claude.ai-inspired chat interface with Phase 4 UX polish, featuring markdown rendering, professional color scheme, animated typing indicators, and full mobile optimization.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **UI/UX (Sleek Compact Design)**: Apple-inspired minimalist interface with sleek, tight, refined aesthetic. Features Inter font, thin minimal header (50px, light grey), teal accent colors (#10A37F), compact spacing throughout, and responsive mobile design. Professional productivity tool aesthetic with reduced padding and tighter margins while maintaining usability.
- **Chat Interface (`/chat` and `/claude`)**: A professional, Claude.ai-inspired chat interface with full feature parity. It uses a clean, minimal aesthetic with neutral colors and the Inter font. Key features include:
    - **Sidebar**: Collapsible project folders (7 categories) with compact 4px spacing, no descriptions shown, conversation management (load, rename, delete). Mobile-optimized with burger menu that stays closed during background refreshes (renderSidebar preserves closed state), auto-closes on conversation selection, and batch-fetches all data before rendering to prevent flickering.
    - **Search Functionality (Phase 5 Part 1)**: Comprehensive search with backend endpoint `/claude/conversations/search` that searches both conversation titles AND message content using SQL LEFT JOIN. Features 300ms debounce, real-time filtering, auto-expand/collapse folders based on matches, clear via X button or ESC key, XSS protection, and graceful client-side fallback. Search results bypass client-side filtering (isBackendSearch flag prevents double-filtering).
    - **Copy Message Functionality (Phase 5 Part 2)**: One-click copy buttons on all messages (user and AI) with intelligent markdown stripping for AI responses. Features desktop hover-to-reveal UX, mobile always-visible buttons, keyboard accessibility (Tab/Enter/Space), success feedback with checkmark animation, and clipboard API with legacy fallback. Strips markdown formatting (bold, italic, code blocks, headers, lists, links) from AI messages before copying plain text.
    - **Conversation Management**: Persistent conversation history stored in PostgreSQL, smart auto-naming for new chats, and responsive design for mobile. "All Chats" section displays all conversations across all projects (up to 100, sorted by most recent).
    - **Background Message Processing**: Uses `/message/background` endpoint for iOS PWA compatibility. Messages are saved immediately with "processing" status, processed server-side in background (even when app is closed), and completed responses are delivered via 3-second polling. This ensures messages complete even when user switches away from the app.
    - **Real-time Updates**: 3-second polling for conversation status checks unread responses and processing messages. Background refreshes skip renderSidebar() to prevent sidebar from reopening on mobile.
    - **PWA Support**: Full Progressive Web App capabilities including offline support, installability, and manifest configuration with professional teal brain icon.
    - **Performance**: Optimized for speed using HTML template strings, event delegation, optimistic UI updates, and parallel API fetches.
    - **Chat Styling (ChatGPT-Inspired Minimal)**: 
        - **Header**: Thin minimal bar (50px), light grey (#F7F7F8), minimalist teal brain logo (SVG), centered title with refined typography
        - **Burger Menu**: Clean white button with border, positioned inside header bounds, teal hover state
        - **User messages**: ChatGPT-style - light grey background (#F7F7F8), left-aligned, full-width, 16px font, 1.6 line-height
        - **AI messages**: White background (#FFFFFF), left-aligned, full-width, compact padding (16px 20px), markdown rendered
        - **Typography**: Inter font, 16px base, 1.6 line-height, clean black text (#2D2D2D)
        - **Sidebar**: Compact spacing - reduced padding throughout, smaller folder icons (14px), tight conversation items (6px padding)
        - **New Chat Button**: Sleek white button with 1px border, teal hover (#E6F7F4), compact (8px vertical padding)
        - **Send Button**: Teal (#10A37F) with darker hover (#0D8C6C), compact (40px height, 10px padding)
        - **Input Area**: Sleeker design - reduced padding (12px), smaller input (10px 14px), 15px font
        - **Spacing**: Tight margins - 12px between messages, 4px between folders, 1px between conversations
        - **Typing Indicator**: Animated dots, compact padding (16px 20px)
        - **Mobile**: Gray background extends to top notch area (safe-area-inset-top) for polished look
        - **Markdown Support**: Full rendering via marked.js - headers, bold, italic, code blocks, lists, blockquotes, links (open in new tab)
        - **Security**: Comprehensive XSS protection via DOMPurify sanitization (markdown), HTML escaping (sidebar), and DOM API value assignment (modals)
    - **Vision/Image Analysis (Phase 6)**: Full Claude vision mode support for image upload and analysis. Features paperclip button (📎) positioned left of input, mobile camera access, file validation (5MB max, JPEG/PNG/GIF/WebP), image preview with thumbnail/filename/filesize, remove button (×), and inline image display in chat messages. Backend leverages Claude Sonnet 4 Vision API with base64 image encoding. Primary use cases: screenshot-based MBTI typing from text messages, social media captions, forum posts, and handwritten notes.
    - **Auto-Expanding Textarea (Phase 6)**: Message input uses multi-line textarea that auto-expands as user types (max 150px height, then scrolls). Supports Shift+Enter for new lines and Enter to send. Resets to single line after sending.
    - **Dark/Light Mode (Phase 7)**: Full theme switching capability with persistent localStorage preference. Features:
        - **Toggle Button**: Borderless colored icons (indigo moon 🌙 for light mode, amber sun ☀️ for dark mode) positioned in top-right header corner, aligned with hamburger button. Includes hover fade and rotation animation.
        - **Theme System**: Comprehensive CSS custom properties (--color-*) for all UI elements including backgrounds, text, borders, buttons, inputs, messages, sidebar, modals, and code blocks.
        - **Light Mode Colors**: Clean whites (#FFFFFF main, #F7F7F8 header), grey user bubbles (#E5E5EA), teal accents (#10A37F).
        - **Dark Mode Colors**: Rich darks (#1A1A1A main, #252525 header/AI bubbles, #2D2D2D user bubbles), adjusted borders (#3A3A3A), brighter link blue (#4A9EFF).
        - **Prevent Flash**: Inline script in <head> applies theme before page render using localStorage and system preference fallback.
        - **Persistence**: Theme preference saved to localStorage, auto-applied on page load.
        - **Complete Coverage**: All UI components adapted including messages, sidebar folders/conversations, search, input areas, buttons, modals, typing indicator, code blocks, and markdown content.
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