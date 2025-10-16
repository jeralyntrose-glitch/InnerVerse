# Overview

This project is a FastAPI-based PDF Q&A application designed to provide intelligent answers from uploaded PDF documents.

# Recent Changes (October 16, 2025)

## Persistent Error Notifications (Latest)
- ✅ **Persistent error modal** - Errors now stay visible until you dismiss them with an OK button
- ✅ **No missed errors** - Walk away during uploads/transcriptions and still see what went wrong when you return
- ✅ **Clean design** - Modal overlay with backdrop blur, smooth animations
- ✅ **All operations covered** - Upload failures, YouTube transcription errors, text-to-PDF errors, chat errors, and more
- ✅ **Mobile optimized** - Proper positioning, sizing, and tap targets for iPhone
- ✅ **Improved error messages** - Timeout errors now explain actual causes (network, restrictions, cookies) instead of assuming video length

## Search All Documents Update
- ✅ **Global document search** - Chat now searches ALL uploaded documents at once instead of requiring specific document IDs
- ✅ **Source attribution** - Answers automatically include which documents the information came from
- ✅ **Simplified UI** - No more document ID input needed, just ask questions and get answers from your entire library
- ✅ **Better context** - System message updated to clarify it answers from uploaded documents

## YouTube Transcription Timeout Fix
- ✅ **Fixed stalling/disappearing loading bar** - Added explicit 5-minute timeout on frontend and 3-minute timeout on Whisper API calls
- ✅ **Better error handling** - Now shows clear timeout errors instead of silently failing
- ✅ **Prevents hanging** - Backend Whisper calls won't hang indefinitely anymore

## Pinecone Batch Upload Fix
- ✅ **Fixed large PDF uploads** - Now batches vector uploads in groups of 50 to avoid Pinecone's 4MB request limit
- ✅ **Supports books up to 1000+ pages** - Can handle very large documents by splitting uploads into safe batch sizes
- ✅ **Progress logging** - Shows batch upload progress in server logs (e.g., "Uploaded batch 3/8")

## Upload Optimization & Large File Support
- ✅ **Efficient binary uploads** - Switched from base64 to multipart/form-data (33% smaller, faster, uses less memory)
- ✅ **Large file support** - Warning for files >20MB, increased embedding timeout to 60s, progress tracking every 50 chunks
- ✅ **Better error messages** - File read errors and network failures now show specific error messages to user
- ✅ **File size display** - Large uploads (>10MB) show file size in upload UI
- ✅ **Notification sound** - Delicate iPhone-style "ting" plays when YouTube transcription or text-to-PDF completes (1200Hz, 0.2s duration)
- ✅ **Text-to-PDF progress bar** - Green-themed progress bar with status stages (Analyzing → Fixing → Generating → Complete)

## Text to PDF Feature
- ✅ **New text-to-PDF converter** - Convert text to formatted PDFs with automatic punctuation and grammar fixes using GPT-3.5
- ✅ **Smart formatting** - AI cleans up text before converting to professional PDF document
- ✅ **Green-themed UI** - Distinct design from YouTube section for easy identification
- ✅ **Mobile optimized** - Works smoothly on iPhone with proper input sizing

## Document Report Enhancements
- ✅ **Hawaii timezone** - Timestamps now display in Hawaii time (HST/UTC-10) instead of UTC
- ✅ **Chronological sorting** - Documents sorted from earliest to latest upload
- ✅ **Upload timestamps** - CSV report includes "uploaded_at" column (formatted as "YYYY-MM-DD HH:MM AM/PM")

## Cookie Storage System
- ✅ **File-based YouTube cookies** - Switched from Replit Secrets to youtube_cookies.txt file for easier updates and no size limits
- ✅ **Bypassed 64KB Secret limit** - No more publishing errors from oversized cookie data

## Error Handling Improvements
- ✅ **Better YouTube error messages** - User-friendly error messages for blocked videos, expired cookies, region locks, private videos, and download failures
- ✅ **Whisper API error handling** - Clear messages for rate limits, API key issues, and transcription timeouts
- ✅ **PDF generation errors** - Helpful feedback when PDF creation fails
- ✅ **Actionable guidance** - Error messages suggest next steps (refresh cookies, try different video, wait for rate limit, etc.)

## UI Enhancements
- ✅ **iPhone-style chat bubbles** - Updated chat interface with rounded bubbles, purple gradient for user messages, smooth animations
- ✅ **Fixed Delete All button** - Reordered API routes so `/documents/all` is matched before `/documents/{document_id}`

## YouTube Transcription Fixes
- ✅ **Fixed download timeout** - Increased to 30 minutes to handle 90+ minute videos
- ✅ **Fixed ffmpeg missing in production** - Changed deployment from Autoscale to VM to include Nix packages
- ✅ **VM deployment includes system packages** - VM deployments include all Nix system packages (ffmpeg) in production
- ✅ **Added ffmpeg detection** - Backend automatically finds and specifies ffmpeg location to yt-dlp
- ✅ **Minimized cancel button** - Made very small (9px font, 2px/6px padding) to prevent overlap

## Mobile UI Enhancements
- ✅ **Compact branding** - Adjusted brain icon (70px), title (24px), and tagline (13px) sizes for mobile
- ✅ **Thinner progress bars** - Reduced to 6px height on mobile for cleaner look
- ✅ **Fixed chat bubble** - Proper width constraints and positioning for mobile devices
- ✅ **Cancel button improvements** - Ultra-compact on mobile (9px font, auto width, no min-height) It features a modern web interface with drag-and-drop upload capabilities, processes documents by chunking and embedding their content, stores these embeddings in Pinecone, and leverages OpenAI's GPT models for answering user queries based on the document content. The application aims to offer an intuitive user experience for document interaction and knowledge retrieval, including the ability to transcribe YouTube videos into searchable PDFs and generate document reports.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Interface**: Single-page application with a modern, glassmorphic UI, animated SVG brain icon, and a purple gradient theme.
- **Theme System**: Light/Dark mode toggle with persistence via localStorage.
- **Upload Flow**: Supports drag-and-drop PDF uploads, Google Drive integration, and YouTube video transcription to PDF. Progress tracking and real-time status updates are provided for all uploads.
- **Chat Flow**: Integrates a chat interface that allows users to ask questions about uploaded documents, with answers generated by GPT models.
- **Features**: Auto-clipboard copy for document IDs, responsive design for mobile, and various UI enhancements for user interaction.

## Backend Architecture
- **Framework**: FastAPI with asynchronous operations.
- **Runtime**: Python with Uvicorn ASGI server.
- **Design Pattern**: Stateless API where the frontend manages `document_id` and the backend uses it for Pinecone queries.

## Document Processing Pipeline
- **PDF Parsing**: Uses PyPDF2 for text extraction from PDFs.
- **Text Chunking**: Employs LangChain's `RecursiveCharacterTextSplitter` to break documents into overlapping chunks (1000 characters with 200 character overlap) to maintain context.
- **YouTube Transcription**: Utilizes `yt-dlp` for audio extraction from YouTube videos, OpenAI Whisper API for transcription, and ReportLab for PDF generation, supporting videos of any length through smart chunking.

## Vector Storage Strategy
- **Database**: Pinecone vector database (index: "mbti-knowledge") for storing document embeddings.
- **Query Strategy**: Filters by `document_id` to ensure queries are answered from the specified document's content.

## Embedding Generation
- **Provider**: OpenAI API (`text-embedding-ada-002` model) for generating embeddings.
- **Performance**: Embeddings are batch processed before upserting to Pinecone.

## API Structure
- **Upload**: `POST /upload` (multipart/form-data) and `POST /upload-base64` (JSON) for PDF uploads.
- **Query**: `POST /query` for document-specific Q&A.
- **YouTube Transcription**: `POST /transcribe-youtube` for converting YouTube videos to searchable PDFs.
- **Text to PDF**: `POST /text-to-pdf` for converting text to formatted PDFs with AI-powered punctuation fixes.
- **Document Report**: `GET /documents/report` for CSV export of uploaded documents.
- **Delete Document**: `DELETE /documents/{document_id}` for removing document data from Pinecone.
- **Static Files**: Serves frontend assets and documentation (`/docs` for Swagger UI).
- **CORS**: Enabled for all origins.

## Configuration Management
- **Environment Variables**: API keys (OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX) are managed via Replit Secrets.
- **Client Initialization**: Lazy initialization pattern is used for API clients.

# External Dependencies

## Vector Database
- **Pinecone**: Cloud-based vector database for storing and querying embeddings.

## AI/ML Services
- **OpenAI API**: Used for text embeddings (text-embedding-ada-002), GPT-3.5-turbo for Q&A, and Whisper API for audio transcription.

## Document Processing
- **PyPDF2**: For PDF parsing and text extraction.
- **LangChain**: For text splitting utilities.
- **yt-dlp**: For downloading audio from YouTube videos.
- **OpenAI Whisper API**: For transcribing audio.
- **ReportLab**: For generating formatted PDFs from transcriptions.

## Web Framework
- **FastAPI**: Python web framework.
- **Uvicorn**: ASGI server.
- **Pydantic**: Data validation.

## Integrations
- **Google Drive Picker API**: For seamless integration with Google Drive for file selection.
- **ffmpeg**: System dependency for audio processing with `yt-dlp`.