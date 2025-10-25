# Overview

InnerVerse is a FastAPI-based PDF Q&A application for intelligent knowledge retrieval. It allows users to upload PDFs, transcribe audio and YouTube videos into searchable documents, and generate reports. It chunks, embeds, and stores document content in Pinecone, leveraging OpenAI's GPT models for query answering. The application also monitors API usage, tracks costs, and applies rate limiting, providing an intuitive experience for document interaction.

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

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations, Python runtime, and Uvicorn ASGI server.
- **Design Pattern**: Stateless API where `document_id` is managed by the frontend.
- **Deployment**: VM deployment with health checks, robust database initialization, and detailed logging.
- **API Usage and Cost Tracking**: Logs and persists OpenAI API call costs to PostgreSQL, accessible via `/api/usage`, with a rate limit of 100 requests per hour.

## Document Processing Pipeline
- **PDF Parsing**: PyPDF2 for text extraction, including encrypted PDFs.
- **Text Chunking**: LangChain's `RecursiveCharacterTextSplitter` for overlapping text chunks.
- **InnerVerse Intelligence Layer**: Automatic MBTI/Jungian taxonomy tagging using GPT-3.5, storing tags in Pinecone metadata.
- **YouTube MP3 Transcription**: Processes audio (MP3, M4A, WAV, MP4) up to 24MB via OpenAI Whisper API, generates formatted PDFs using ReportLab, auto-tags, and indexes in Pinecone.
- **Text to PDF**: Converts text to formatted PDFs with GPT-3.5 for punctuation and grammar fixes.
- **Reprocess PDF**: Enhances existing Whisper-transcribed PDFs.
- **Large File Support**: Efficient binary uploads and batch processing for Pinecone upserts.

## Vector Storage Strategy
- **Database**: Pinecone vector database ("mbti-knowledge" index).
- **Query Strategy**: Filters by `document_id` or performs global searches.

## Embedding Generation
- **Provider**: OpenAI API (`text-embedding-ada-002`) for batch-processed embeddings.

## API Structure
- **Upload**: `POST /upload`, `POST /upload-base64` (PDFs), `POST /upload-audio` (audio).
- **Query**: `POST /query`.
- **Text/PDF Processing**: `POST /text-to-pdf`, `POST /reprocess-pdf`.
- **Document Management**: `GET /documents/report`, `DELETE /documents/{document_id}`, `DELETE /documents/all`, `PATCH /documents/{document_id}/rename`, chat commands.
- **Claude Chat API**: Endpoints for managing project categories, conversations, messages, and searching.
- **Usage Monitoring**: `/api/usage`.
- **Static Files**: Serves frontend assets and Swagger UI documentation.
- **PWA Support**: Service worker, manifest, and icons.
- **CORS**: Enabled for all origins.

## Configuration Management
- **Environment Variables**: API keys managed via Replit Secrets.
- **Client Initialization**: Lazy initialization for API clients.

# External Dependencies

## Vector Database
- **Pinecone**: Vector database.

## AI/ML Services
- **OpenAI API**: For text embeddings (`text-embedding-ada-002`), GPT-3.5-turbo (Q&A, text fixes), and Whisper API (audio transcription).
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