# Overview

InnerVerse is a FastAPI-based PDF Q&A application designed for intelligent knowledge retrieval from various sources like PDFs, audio, and YouTube videos. It uses chunking, embedding, and Pinecone for storage, and leverages OpenAI's GPT models and Anthropic's Claude for answering queries and generating reports. The project aims to provide an intuitive and professional document interaction experience, featuring a Claude.ai-inspired chat interface, advanced UX, mobile optimization, API usage monitoring, and cost tracking.

# User Preferences

Preferred communication style: Simple, everyday language with a decent amount of emojis (not excessive, but engaging).

# System Architecture

## Frontend Architecture
- **UI/UX**: Apple-inspired minimalist design with a professional productivity tool aesthetic, featuring Inter font, a thin header, teal accent colors, and compact spacing. Branding uses "InnerVerse" in Outfit font with a simplified teal brain logo.
- **Learning Paths Canvas (`/learning-paths`)**: 2D interactive course visualization with dual view modes: (1) Tree View - D3.js hierarchical tree with zoom/pan controls, (2) Grid View - responsive card grid grouped by category with hover effects. Toggle button switches between views, hiding zoom controls in grid mode. AI generation UI, search/filter, and responsive design.
- **Lesson Page (`/learning-paths/{course_id}/{lesson_id}`)**: Split-screen interface with content pane (lesson info, progress, video, transcript, notes) and an AI tutor chat pane. The AI tutor (Claude Sonnet 4) is context-aware, tracks progress, and persists conversations in PostgreSQL.
- **Chat Interface (`/chat` and `/claude`)**: Claude.ai/ChatGPT-inspired interface with a collapsible sidebar for conversation management, comprehensive search, one-click message copy, and persistent history. Features synchronous chat with real-time streaming responses and optimized performance. Includes multi-image upload and analysis using Claude Sonnet 4 Vision API with client-side compression, full markdown rendering via `marked.js`, and comprehensive XSS protection via DOMPurify. Supports dark/light mode with localStorage persistence.
- **Migration Dashboard (`/migration`)**: Real-time dashboard for embedding upgrades.
- **AXIS MIND Uploader (`/uploader`)**: Document upload and management with drag & drop PDF, YouTube transcription, Text-to-PDF conversion with AI grammar fixes, tag library, API cost tracker, and document reporting.

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations, Python, and Uvicorn.
- **Design Pattern**: Stateless API.
- **Deployment**: VM deployment with health checks and robust logging.
- **Background Workers**: Uses `threading.Thread` with daemon=True for reliable background task execution. FastAPI BackgroundTasks not used due to environment compatibility issues.
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
- **Phase 6 - Semantic Concept Assignment (COMPLETED 2025-11-08)**: Auto-assigns 3-10 relevant knowledge graph concepts to each lesson using Pinecone vector similarity. System embedded 1,632 concepts to Pinecone with `type='concept'` metadata, generated 1,001 assignments across 121 lessons (avg 8.3/lesson) with confidence scores (high/medium/low). Backend uses composite scoring (70% vector similarity, 30% prominence) with API endpoint returning concept details with O(1) lookup performance. Scripts: `scripts/embed_concepts_to_pinecone.py`, `scripts/assign_concepts_to_lessons.py`. Cost: $0.0052 for embeddings. **FULLY FUNCTIONAL** - API verified working (returns concepts in 0.6s), frontend fetch logic implemented with timeout protection and comprehensive error handling. **Known Limitation**: Replit IDE webview proxy blocks fetch responses; use direct public URL (axis-of-mind.replit.app) for testing, not Replit preview iframe. **PWA Infrastructure Removed (2025-11-08)**: Removed service worker, BackgroundMessageManager, and all PWA code in preparation for native iOS app. Chat now uses synchronous mode exclusively.
- **Phase 6.5 - Content Management & UI Polish (COMPLETED 2025-11-09)**: Redesigned concept cards from grid to stacked rectangular layout with expand/collapse functionality. Added comprehensive delete functionality with 2-step confirmations: delete lesson button (lesson sidebar), delete course button (Learning Paths cards, hover-reveal), and nuclear reset endpoint (`DELETE /api/admin/reset-all`). All DELETE endpoints use proper connection management with try/except/finally blocks, automatic rollback on errors, and audit logging. Course cards redesigned with centered category badges and keyboard-accessible delete buttons. "View Course Details" button now navigates to first lesson. Files: `static/learning_paths.js`, `static/learning_paths.css`, `static/lesson_page.js`, `static/lesson_page.css`, `main.py`.
- **Phase 6.5b - Automated Lesson Content Generation (COMPLETED 2025-11-09)**: Successfully auto-generated educational content for 116 out of 120 lessons (96.7%) using Claude Sonnet 4 to synthesize content from Pinecone transcript chunks. System uses semantic search to find relevant source material, generates structured HTML content with sections (Overview, Key Concepts, Deep Dive, Practical Applications), and applies DOMPurify XSS protection on display. Database schema includes `lesson_content` TEXT column. Batch processing script (`scripts/generate_batch.py`) processes 10 lessons at a time with progress tracking, cost reporting (~$0.015-0.025 per lesson), and automatic skipping for lessons without matching transcripts. Total generation cost: ~$1.90. Frontend displays content in 3-column layout: 20% concept sidebar, 40% lesson content area, 40% AI chat pane. 4 lessons permanently skipped (no source material): "Introduction to Shadow Integration", "Cognitive Function Support Systems", "Cognitive Function Traffic Jams and Shifting", "Advanced Cognitive Function Targeting".
- **Phase 7 - Automatic Content Generation on Course Creation (COMPLETED 2025-11-09, FIXED 2025-11-10)**: Fully asynchronous lesson content generation with proper separation of concerns and automatic concept assignment. **FLOW**: (1) User clicks "✨ Generate Course", (2) Claude generates course structure immediately (~3-5s), (3) Backend returns course ID + job ID instantly (200 OK), (4) Course appears in tree/grid view immediately with empty lessons, (5) **ConceptAssigner automatically assigns 3-10 knowledge graph concepts to each lesson** (0.3-0.5s per lesson) using Pinecone vector similarity + prominence scoring, (6) Background worker generates detailed lesson content asynchronously using Claude + Pinecone (30-60s per lesson), (7) Frontend polls `/api/courses/structure-generation/{job_id}` every 2s and shows animated progress bar with shimmer effects, (8) Modal auto-closes when complete. **Architecture**: `ConceptAssigner` service (`src/services/concept_assigner.py`) automatically assigns concepts during structure generation with composite scoring (70% vector similarity, 30% prominence), `LessonContentGenerator` service synthesizes content from Pinecone transcript chunks using assigned concepts for semantic search, `BackgroundJobService` tracks job status/progress/cost in PostgreSQL (`background_jobs` table) with payload update support, `threading.Thread` with daemon=True runs `generate_course_structure_worker()` asynchronously (non-blocking), resilient error handling (per-lesson failure doesn't kill job), defensive DB updates (try/except on progress updates). **Key Features**: Course creation never blocks (instant response), concepts auto-assigned before content generation, content generates in background (users can navigate away), per-lesson status tracking (pending/generating/complete/error), progress polling with 10-min timeout, comprehensive cost tracking (Claude + concept embeddings), job payload properly updated with `courses_created` array for frontend consumption. **UI Enhancement**: Beautiful gradient progress bar with shimmer animation, real-time updates (percentage, lesson count, cost, elapsed time), color-coded completion states (green/orange/red). **Technical Fix (2025-11-10)**: Switched from FastAPI BackgroundTasks (not executing in Replit environment) to `threading.Thread` for reliable worker execution. Added `payload_updates` parameter to `BackgroundJobService.complete_job()` to properly save created course IDs to database. Files: `main.py`, `src/services/concept_assigner.py`, `src/services/lesson_content_generator.py`, `src/services/background_job_service.py`, `static/learning_paths.js`, `static/learning_paths.css`.

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