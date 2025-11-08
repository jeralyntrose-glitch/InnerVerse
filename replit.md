# Overview

InnerVerse is a FastAPI-based PDF Q&A application designed for intelligent knowledge retrieval from various sources like PDFs, audio, and YouTube videos. It uses chunking, embedding, and Pinecone for storage, and leverages OpenAI's GPT models and Anthropic's Claude for answering queries and generating reports. The project aims to provide an intuitive and professional document interaction experience, featuring a Claude.ai-inspired chat interface, advanced UX, mobile optimization, API usage monitoring, and cost tracking.

# User Preferences

Preferred communication style: Simple, everyday language with a decent amount of emojis (not excessive, but engaging).

# System Architecture

## Frontend Architecture
- **UI/UX**: Apple-inspired minimalist design with a professional productivity tool aesthetic, featuring Inter font, a thin header, teal accent colors, and compact spacing. Branding uses "InnerVerse" in Outfit font with a simplified teal brain logo.
- **Learning Paths Canvas (`/learning-paths`)**: 2D interactive course visualization using D3.js for hierarchical display, category-colored course cards, AI generation UI, search/filter, and responsive design.
- **Lesson Page (`/learning-paths/{course_id}/{lesson_id}`)**: Split-screen interface with content pane (lesson info, progress, video, transcript, notes) and an AI tutor chat pane. The AI tutor (Claude Sonnet 4) is context-aware, tracks progress, and persists conversations in PostgreSQL.
- **Chat Interface (`/chat` and `/claude`)**: Claude.ai/ChatGPT-inspired interface with a collapsible sidebar for conversation management, comprehensive search, one-click message copy, and persistent history. Features synchronous chat with real-time streaming responses and optimized performance. Includes multi-image upload and analysis using Claude Sonnet 4 Vision API with client-side compression, full markdown rendering via `marked.js`, and comprehensive XSS protection via DOMPurify. Supports dark/light mode with localStorage persistence.
- **Migration Dashboard (`/migration`)**: Real-time dashboard for embedding upgrades.
- **AXIS MIND Uploader (`/uploader`)**: Document upload and management with drag & drop PDF, YouTube transcription, Text-to-PDF conversion with AI grammar fixes, tag library, API cost tracker, and document reporting.

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations, Python, and Uvicorn.
- **Design Pattern**: Stateless API.
- **Deployment**: VM deployment with health checks and robust logging.
- **API Management**: Logs OpenAI API costs to PostgreSQL, accessible via `/api/usage`, with rate limiting.
- **Retry Logic**: Automatic retry with exponential backoff for Claude API errors.
- **Migration System**: Background task-based API for live embedding upgrades.
- **MBTI Reference Data System**: Uses `src/data/reference_data.json` (generated from `four_sides_map.py`) as a source of truth for all 16 MBTI types. Integrated with Claude via a `query_reference_data` tool and with lesson chat for pre-formatted answers. Prioritizes JSON reference, then Pinecone search, then Claude synthesis. Loaded once at startup for performance.

## Learning Paths System
- **Overview**: Structured learning tracks for MBTI education with AI-powered course generation and smart content assignment.
- **Database Schema**: `courses`, `lessons`, `user_progress`, `course_prerequisites`, and `lesson_concepts` tables.
- **AI Generation**: `CourseGenerator` uses Claude Sonnet 4 for curriculum generation. `ContentAssigner` uses a 3-tier confidence system for content assignment. Both track costs.
- **Business Logic**: Full CRUD for courses/lessons, progress tracking, and helper methods for AI integration. Uses JSONB fields for flexible metadata.
- **API Endpoints**: Comprehensive API for course and lesson management, progress tracking, AI-powered course generation (`POST /api/courses/generate`), smart content assignment (`POST /api/courses/assign-content`), AI cost statistics, and concept retrieval (`GET /api/lessons/{lesson_id}/concepts`).
- **Knowledge Graph Integration**: Fetches single concepts and performs semantic concept searches for AI generation.
- **Phase 6 - Semantic Concept Assignment (COMPLETED 2025-11-08)**: Auto-assigns 3-10 relevant knowledge graph concepts to each lesson using Pinecone vector similarity. System embedded 1,632 concepts to Pinecone with `type='concept'` metadata, generated 1,001 assignments across 121 lessons (avg 8.3/lesson) with confidence scores (high/medium/low). Backend uses composite scoring (70% vector similarity, 30% prominence) with API endpoint returning concept details with O(1) lookup performance. Scripts: `scripts/embed_concepts_to_pinecone.py`, `scripts/assign_concepts_to_lessons.py`. Cost: $0.0052 for embeddings. **Phase 6.5 (UI Polish)**: Frontend concept rendering pending - page loads successfully but browser XHR reception issue persists. API endpoint verified working (returns 200 OK). Concepts accessible via API but UI cards not displaying yet. **PWA Infrastructure Removed (2025-11-08)**: Removed service worker, BackgroundMessageManager, and all PWA code in preparation for native iOS app. Chat now uses synchronous mode exclusively.

## Document Processing Pipeline
- **PDF Parsing**: PyPDF2 for text extraction.
- **Text Chunking**: LangChain's `RecursiveCharacterTextSplitter`.
- **Intelligence Layer**: Automatic MBTI/Jungian taxonomy tagging using GPT-4o-mini with authoritative reference data validation. Upgraded 2025-11-08 with three-layer accuracy system: (1) Reference data injection into GPT prompt, (2) Post-processing validation against `reference_data.json`, (3) Auto-correction for case variations and common errors. Filters invalid types/functions and logs all corrections. Tags stored in Pinecone.
- **Metadata Extraction**: Extracts season/episode, MBTI types, and cognitive functions with validation.
- **Audio/Video Processing**: OpenAI Whisper API for transcription, ReportLab for PDF generation, and `yt-dlp` for YouTube downloads.
- **Text to PDF**: Converts text to formatted PDFs with GPT-3.5 for grammar correction.
- **Large File Support**: Efficient binary uploads and batch processing for Pinecone upserts.
- **Reference Data Validator**: Module at `src/services/reference_validator.py` provides comprehensive validation for all MBTI metadata (types, functions, quadras, temperaments, interaction styles). Supports auto-correction, case-insensitive matching, and detailed logging. Performance: 1000 validations in ~1.3ms.

## Vector Storage and Search
- **Vector Database**: Pinecone (`mbti-knowledge-v2` production index, 3072 dimensions).
- **Embedding Generation**: `text-embedding-3-large` (3072 dimensions) for all embeddings.
- **Hybrid Search System**: Combines vector similarity with metadata filters, smart re-ranking, and MBTI ontology-aware query rewriting.
- **Concept Embeddings**: 1,632 knowledge graph concepts embedded with `type='concept'` metadata for semantic lesson matching (Phase 6).

## API Structure
- **Core APIs**: For upload (PDF, audio, base64), querying, text-to-PDF conversion, and re-processing.
- **Document Management**: CRUD operations for documents and chat commands.
- **Claude Chat API**: Endpoints for managing project categories, conversations, and messages.
- **Lesson Chat API**: `POST /api/chat/lesson` for AI tutor interaction, `GET /api/chat/lesson/{lesson_id}/history` for history retrieval, and `DELETE /api/chat/lesson/{lesson_id}/history` to clear history.
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