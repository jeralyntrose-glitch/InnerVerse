# Overview

InnerVerse is a FastAPI-based PDF Q&A application offering intelligent knowledge retrieval from diverse sources like PDFs, audio, and YouTube videos. It utilizes chunking, embedding, and Pinecone for storage, along with OpenAI's GPT models and Anthropic's Claude for query answering and report generation. The project aims to deliver a professional document interaction experience, featuring a Claude.ai-inspired chat interface, advanced UX, mobile optimization, API usage monitoring, and cost tracking. The business vision is to provide a comprehensive, intuitive, and efficient platform for knowledge management and interaction across various content types, with market potential in education, research, and corporate training.

# User Preferences

Preferred communication style: Simple, everyday language with a decent amount of emojis (not excessive, but engaging).

# System Architecture

## UI/UX Decisions
- **Design Language**: Apple-inspired minimalist aesthetic with a professional productivity tool feel.
- **Typography**: Inter font for general text, Outfit font for "InnerVerse" branding.
- **Color Scheme**: Teal accent colors.
- **Key UI Components**:
    - **Smart Search Bar**: Hybrid search positioned below progress bar on dashboard. Supports season search ("Season 18"), title search ("ENFP"), category search ("CS Joseph Responds"), and keyword search. Features debounced input, dropdown results with thumbnails, keyboard shortcuts (ESC to close), and mobile-responsive design.
    - **Learning Paths Canvas**: 2D interactive course visualization with Tree View (D3.js) and Grid View. Supports AI generation UI, search/filter, and responsive design.
    - **Lesson Page**: Split-screen interface featuring content and an AI tutor chat pane (Claude Sonnet 4) that is context-aware and tracks progress.
    - **Chat Interface**: Claude.ai/ChatGPT-inspired with collapsible sidebar, search, history, real-time streaming, multi-image upload (Claude Sonnet 4 Vision), Markdown rendering (`marked.js`), XSS protection (DOMPurify), and dark/light mode.
    - **AXIS MIND Uploader**: Document upload via drag & drop, YouTube transcription, Text-to-PDF conversion with AI grammar fixes, tag library, and API cost tracking.
    - **Supplementary Library**: Browseable collection of 258 CS Joseph lessons organized into 5 categories, integrated with AI chat and video playback.

## Technical Implementations
- **Backend Framework**: FastAPI with asynchronous operations, Python, and Uvicorn.
- **Design Pattern**: Stateless API.
- **Background Workers**: Uses `threading.Thread` for reliable background task execution.
- **API Management**: Logs OpenAI API costs to PostgreSQL, with rate limiting.
- **Retry Logic**: Automatic retry with exponential backoff for Claude API errors.
- **MBTI Reference Data System**: `src/data/reference_data.json` as the source of truth for MBTI types, integrated with Claude via a `query_reference_data` tool and lesson chat.
- **Learning Paths System**:
    - **Database Schema**: `courses`, `lessons`, `user_progress`, `course_prerequisites`, `lesson_concepts` tables.
    - **AI Generation**: `CourseGenerator` and `ContentAssigner` use Claude Sonnet 4 for curriculum generation and content assignment.
    - **Semantic Concept Assignment**: Auto-assigns 3-10 relevant knowledge graph concepts to each lesson using Pinecone vector similarity and prominence scoring.
    - **Automated Lesson Content Generation**: Asynchronously generates structured HTML lesson content using Claude Sonnet 4, synthesizing from Pinecone transcript chunks.
    - **Automated Course Creation Flow**: Instant course structure generation, background concept assignment, and asynchronous lesson content generation with real-time UI progress updates.
- **Document Processing Pipeline**:
    - **PDF Parsing**: PyPDF2.
    - **Text Chunking**: LangChain's `RecursiveCharacterTextSplitter`.
    - **Intelligence Layer**: Automatic MBTI/Jungian taxonomy tagging using GPT-4o-mini with authoritative reference data validation.
    - **Audio/Video Processing**: OpenAI Whisper for transcription, `yt-dlp` for YouTube downloads.
    - **Text to PDF**: Converts text to formatted PDFs with GPT-3.5 for grammar correction.
    - **Reference Data Validator**: `src/services/reference_validator.py` for comprehensive MBTI metadata validation and auto-correction.
- **Vector Storage and Search**:
    - **Vector Database**: Pinecone (`mbti-knowledge-v2` production index, 3072 dimensions).
    - **Embedding Generation**: `text-embedding-3-large` (3072 dimensions).
    - **Hybrid Search System**: Combines vector similarity with metadata filters, smart re-ranking, and MBTI ontology-aware query rewriting.
    - **Concept Embeddings**: 1,632 knowledge graph concepts embedded for semantic lesson matching.

## API Structure
- **Core APIs**: Upload (PDF, audio, base64), querying, text-to-PDF conversion, re-processing.
- **Document Management**: CRUD for documents and chat commands.
- **Claude Chat API**: Manage project categories, conversations, messages.
- **Lesson Chat API**: AI tutor interaction, history retrieval, history clearing.
- **OpenAI-Compatible API**: `/v1/models` and `/v1/chat/completions` for LibreChat integration (wrapping Claude and Pinecone).
- **System APIs**: Migration and usage monitoring.
- **Configuration**: Environment variables (Replit Secrets) for API keys, lazy initialization for API clients.

# External Dependencies

## Vector Database
- **Pinecone**: Document embeddings storage and retrieval.

## AI/ML Services
- **OpenAI API**: `text-embedding-3-large` for embeddings, GPT-3.5-turbo for Q&A and text fixes, Whisper API for audio transcription, GPT-4o-mini for MBTI/Jungian taxonomy tagging.
- **Anthropic API**: Claude Sonnet 4 for conversational AI and content generation.

## Document Processing
- **PyPDF2**: PDF parsing.
- **LangChain**: Text splitting.
- **ReportLab**: PDF generation.
- **ffmpeg**: Audio processing.
- **poppler**: PDF rendering.
- **tesseract**: OCR.

## Data Storage
- **PostgreSQL**: Persistent storage for cost tracking, conversation history, and background job status.

## Web Framework & Libraries
- **FastAPI**: Python web framework.
- **Uvicorn**: ASGI server.
- **Pydantic**: Data validation.
- **marked.js**: Markdown rendering in frontend.
- **DOMPurify**: XSS protection in frontend.
- **D3.js**: Interactive data visualizations (Tree View).

## Integrations
- **yt-dlp**: YouTube video downloading.
- **Google Drive Picker API**: Google Drive integration.
- **Brave Search API**: Web search integration.