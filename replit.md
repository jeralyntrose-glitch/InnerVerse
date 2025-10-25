# Overview

InnerVerse is a FastAPI-based PDF Q&A application designed for intelligent knowledge retrieval from uploaded documents. It enables users to upload PDFs via a modern web interface, transcribe audio and YouTube videos into searchable PDFs, and generate document reports. The core functionality involves chunking, embedding, and storing document content in Pinecone, then leveraging OpenAI's GPT models for answering user queries. The application also provides robust API usage monitoring with real-time cost tracking and rate limiting, offering an intuitive and efficient experience for document interaction.

# Recent Changes (October 25, 2025)

**Mobile Network Resilience (October 25, 2025)**
- Fixed "Message failed to send" errors on mobile when server actually processed messages successfully
- ROOT CAUSE: Mobile networks drop SSE (Server-Sent Events) streaming connections mid-response
- Server logs show 200 OK (success), but frontend loses connection before receiving full stream
- SOLUTION: Auto-recovery mechanism - when stream fails, check if message was saved on server
- If message exists in database, reload entire conversation to display the response
- Only shows "failed" if message truly wasn't processed
- Eliminates false failures from network interruptions
- Users see responses even when mobile connection is unstable

**Hamburger Menu Fix (October 25, 2025)**
- Fixed unresponsive hamburger menu requiring 4-5 taps on iOS
- ROOT CAUSE: iOS Safari has 300ms delay on click events (to detect double-tap zoom)
- SOLUTION: Use touchstart event with preventDefault to bypass the delay entirely
- Dual-listener setup: touchstart for mobile (instant), click for desktop (fallback)
- Flag prevents double-firing when both touchstart and click fire
- Increased tap target from 44px to 48px for better touch accuracy
- Fixed z-index layering: hamburger (z-index: 50) now goes behind sidebar (z-index: 1000) when open
- Added explicit pointer-events: none to all hamburger child elements (icon, spans) so only parent button catches taps
- Added hardware acceleration transforms (-webkit-transform: translateZ(0)) for instant touch response
- Hamburger now hides behind sidebar when open, no longer overlaps search bar
- Instant response on first tap - no more frustrating multi-tap requirement

**Streaming Backend Stability (October 25, 2025)**
- Fixed server crashes from improper database connection handling in streaming endpoint
- ROOT CAUSE: Generator function tried to use closed database cursor, causing crashes after first message
- SOLUTION: Close initial connection immediately, create fresh connection in generator for saving responses
- Proper try/finally blocks guarantee database cleanup even on errors
- Added comprehensive error logging with stack traces for debugging

**Smooth Streaming UX Optimization**
- Pre-allocates space (60px min-height) for Claude's response before text starts appearing
- Scrolls to bottom ONCE when response container is created (no more jumpy scrolling)
- Text fills in smoothly without pushing the screen up continuously
- Creates smooth, polished typing effect - reserve space first, then fill it in
- Significantly improves ADHD-friendly experience by eliminating visual jumpiness

**Message Deletion Feature**
- Added delete button (🗑️) to each message in Claude chat interface
- Delete buttons appear on hover with smooth opacity transition
- Confirmation dialog prevents accidental deletions
- Backend endpoint `DELETE /claude/messages/{id}` handles message removal
- Conversation reloads automatically after deletion to show updated state
- Clean UI with proper alignment for both user and assistant messages

**Performance Optimization: Real-Time Streaming Implementation**
- Replaced external API call (`axis-of-mind.replit.app`) with local Pinecone vector search for faster response times
- Implemented real Claude Sonnet 4 streaming using Server-Sent Events (SSE) via Anthropic's streaming API
- Created new `/claude/conversations/{id}/message/stream` endpoint for streaming responses
- Updated frontend to consume SSE streams and display text in real-time as it arrives from Claude
- Added visual search indicator (🔍 Searching knowledge base...) during Pinecone queries
- Performance improvement: Sub-500ms Pinecone queries + real-time word-by-word streaming (ADHD-friendly)

**Web Search Integration**
- Integrated Brave Search API for accessing current information and public knowledge
- Added `search_web_brave()` function in `claude_api.py` for web searches
- Claude automatically determines when to use Pinecone (MBTI content), web search (current events/facts), or both
- System prompt updated to include web search tool alongside InnerVerse knowledge base
- Visual indicator (🌐 Searching the web...) shows when web searches are happening
- Supports hybrid queries combining CS Joseph content with current public information

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Interface**: Single-page application with a glassmorphic UI, animated SVG brain icon, purple gradient theme, and a live visual cost tracker.
- **Theme System**: Light/Dark mode toggle with persistence.
- **Upload Flow**: Supports drag-and-drop PDF uploads, Google Drive integration, and YouTube MP3 transcription with progress tracking and persistent error notifications. Mobile-optimized.
- **Tag Library**: Cloud-based visual tag library with interactive tag clouds, frequency counts, document browsing by tags, and a document rename feature. Supports filtering by single-clicking tags and auto-filling chat with questions by double-clicking.
- **Chat Flow**: iPhone-style chat interface for document Q&A and management via commands (e.g., `list docs`, `delete doc [id]`). Answers are generated by GPT models across all uploaded documents.
- **Claude Master Interface** (`/claude`): Advanced conversational workspace powered by Claude Sonnet 4 with a production-ready ChatGPT-style interface. Features 7 organized project categories, persistent conversations stored in PostgreSQL, and a ChatGPT-style sidebar with full-height design. Responsive design (fixed position on desktop with 260px width, overlay mode on mobile with close button). Includes a welcome screen with suggested prompts and robust state management. Security features include HTML escaping to prevent XSS. Integrates automatic InnerVerse backend queries and web search capabilities via Claude API function calling. Supports PWA for mobile installation.
  - **ChatGPT-Style Sidebar**: Fixed-position full-height (100dvh) sidebar with light gray background (#f7f7f8). Top section contains search bar (no new chat icon for cleaner design). Navigation includes "InnerVerse" home button, collapsible "All Chats" section (shows all conversations across all projects), and collapsible "Projects" section with 7 project folders. Each project folder expands to show nested conversations filtered by project_id. User profile footer shows "Jeralyn". **Performance optimized**: All conversations preloaded in parallel on page load for instant folder expansion (<200ms) with 150ms CSS transitions. Simple click handlers for hamburger menu and folder dropdowns ensure instant response times. XSS-protected via escapeHtml on all conversation/project names. Mobile features: close button (X) in top-right, click-outside-to-close with backdrop, auto-close when selecting conversations. Desktop: always visible at 260px width, push mode layout. Tablet (768-1024px): push mode. Mobile (<768px): overlay mode with 280px width (max 85vw).
  - **Browser History Routing**: Full browser back/forward button support using HTML5 History API. Back button navigates within app hierarchy (Chat → Project → Home) without exiting. Each navigation action (openProject, openConversation, showHomeView) pushes history state with pushState. popstate listener handles browser navigation events to restore correct view state.
  - **Conversation List**: ChatGPT-style compact design with single-line items, timestamps on right (e.g., "now", "5m", "2h", "Jan 15"), and delete functionality. Each item shows conversation name with ellipsis truncation, timestamp, and trash icon button. Delete requires confirmation dialog. Active conversation highlighted with persistent background color (var(--bg-active)) that survives hover states. Hover effects only apply to non-active items to preserve visual selection. Instant navigation with loading spinner (<200ms) - no artificial delays.
  - **Auto-Expanding Textarea**: Input grows from 40px (1 line) to 120px (5 lines) maximum, with debounced scrollbar updates for smooth performance.
  - **Streaming Responses**: Typewriter effect displays AI responses in 5-character chunks every 8ms with optimized scrolling (every 10 chunks) for engaging, performant UX.
  - **iOS Optimization**: iPhone 14 Pro optimized with viewport locking (position: fixed + overscroll-behavior) to prevent page sliding while preserving native scrolling in message containers. Input bar positioned with `calc(12px + env(safe-area-inset-bottom))` for proper safe area handling.
  - **Thinking Indicator**: Subtle breathing/pulsing indicator (8px blue dot with "thinking" text) appears bottom-right during AI processing to maintain user engagement (ADHD-friendly design).
  - **Offline Resilience**: PWA-optimized message persistence handles interrupted API calls gracefully. Messages are saved to localStorage before sending with unique IDs, marked as failed on error, and automatically present retry UI on app resume. Handles iOS app backgrounding, duplicate messages (e.g., "Yes", "OK"), and includes XSS protection via textContent rendering. Visibility change and pageshow listeners detect app resume to restore failed messages.
  - **Performance**: DOM element caching, parallel API fetches, debounced input handlers, optimized rendering with fade-in effects, instant conversation/project switching with non-blocking background loads, and single-fetch architecture eliminating duplicate network requests.

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations.
- **Runtime**: Python with Uvicorn ASGI server.
- **Design Pattern**: Stateless API where `document_id` is managed by the frontend.
- **Deployment**: VM deployment with health checks, robust database initialization, and detailed logging.
- **API Usage and Cost Tracking**: Logs and persists OpenAI API call costs to PostgreSQL, accessible via `/api/usage`, with a rate limit of 100 requests per hour.

## Document Processing Pipeline
- **PDF Parsing**: Uses PyPDF2 for text extraction, supporting encrypted PDFs.
- **Text Chunking**: LangChain's `RecursiveCharacterTextSplitter` for overlapping text chunks.
- **InnerVerse Intelligence Layer**: Automatic MBTI/Jungian taxonomy tagging using GPT-3.5, storing tags in Pinecone metadata.
- **YouTube MP3 Transcription**: Processes uploaded audio (MP3, M4A, WAV, MP4) up to 24MB via OpenAI Whisper API, generates formatted PDFs using ReportLab, auto-tags, and indexes in Pinecone.
- **Text to PDF**: Converts text to formatted PDFs with GPT-3.5 for punctuation and grammar fixes.
- **Reprocess PDF**: Enhances existing Whisper-transcribed PDFs by extracting text, cleaning with GPT-3.5, and returning an improved PDF.
- **Large File Support**: Efficient binary uploads and batch processing for Pinecone upserts.

## Vector Storage Strategy
- **Database**: Pinecone vector database ("mbti-knowledge" index).
- **Query Strategy**: Filters by `document_id` for specific documents or performs global searches.

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
- **PWA Support**: Service worker, manifest, and icons for mobile installation.
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