# Overview

This is a FastAPI-based PDF Q&A application with a modern web interface that allows users to upload PDF documents, processes them into chunks, stores them in Pinecone vector database, and enables querying the documents using OpenAI's GPT for intelligent answers based on document content. The app features both a drag-and-drop upload interface and an integrated chat system for asking questions about uploaded documents.

# Recent Changes (October 14, 2025)

## Dropdown Multi-Select & UI Fixes (Latest)
- ✅ **Checkbox multi-select** - Added checkboxes to dropdown for selecting multiple files
- ✅ **Copy Selected button** - New button copies only checked files in tab-separated format
- ✅ **Dropdown footer redesign** - Updated with "📋 Copy Selected", "📋 Copy All", "🗂️ Archive" buttons
- ✅ **Cancel button positioning fix** - Moved cancel button to right side (120px padding) to prevent overlap with error messages
- ✅ **Cache refresh** - Updated to v=5 to force browser reload of new CSS and JavaScript

## UI/UX Redesign - Modern Purple Theme
- ✅ **Complete visual redesign** with purple/lavender gradient backgrounds
- ✅ **Glowing brain circuit icon** - Animated SVG with neon green glow effect
- ✅ **Light/Dark mode toggle** - Persistent theme switcher with sun/moon icons in top-right
- ✅ Updated typography: "AXIS MIND" bold title + "Where cognition becomes code." tagline
- ✅ Redesigned buttons: Purple "Start uploading" primary button + white Google Drive button
- ✅ Modern glassmorphism effects with backdrop blur on all UI elements
- ✅ Enhanced upload area with larger rounded corners and semi-transparent background
- ✅ Consistent color theming across all components (dropdowns, modals, chat)
- ✅ Smooth animations: floating brain icon, theme transitions, hover effects
- ✅ Improved responsive design for mobile and tablet devices

## Google Drive Integration (Official Google Picker API)
- ✅ **Official Google Drive Picker** - Real Google Drive interface for browsing and selecting files
- ✅ Blue "📁 Google Drive" button opens the native Google Drive file picker
- ✅ Browse folders, navigate your entire Drive, and search for files
- ✅ Multi-select support - choose multiple PDFs at once
- ✅ Full Google Drive UI with thumbnails, file details, and navigation
- ✅ Automatic download and processing with progress tracking
- ✅ Backend endpoints: /api/google-api-key, /api/gdrive-token, /api/gdrive-download/{file_id}
- ✅ Uses Replit Google Drive connector for OAuth + Google API key for Picker
- ✅ Secure: API key stored in Replit Secrets (GOOGLE_API_KEY)
- ✅ Fixed white square issue by setting origin to 'https://replit.com' (required for iframe environment)
- ⚠️ **Important**: Add `https://replit.com` to Authorized JavaScript origins in Google Cloud Console

## UI Fixes & Enhancements
- ✅ Fixed dropdown bug: now closes when clicking outside or toggling again
- ✅ Added click-outside-to-close functionality for document dropdown
- ✅ Added horizontal scrolling to dropdown (overflow-x: auto)
- ✅ Enhanced copy buttons to include Filename, Document ID, and Timestamp in tab-separated format
- ✅ "Copy" button copies in order: PDF Title → Document ID → Timestamp (for Google Sheets columns)
- ✅ "Copy All IDs" button copies all documents with filename, ID, and date (each in separate columns)
- ✅ Added cancel upload feature with red "✕ Cancel" button that appears during uploads
- ✅ Cancel button aborts all ongoing fetch requests using AbortController API
- ✅ Cancelled uploads are marked with "(Cancelled)" label and error styling
- ✅ Works for both local file uploads and Google Drive uploads

## Previous Features (Earlier October 14, 2025)
- ✅ Added scrollable upload status box showing up to 10 files with individual progress bars
- ✅ Implemented multi-file upload support (drag & drop or browse multiple PDFs)
- ✅ Created real-time progress tracking with thin loading bars that fill during processing
- ✅ Added visual status indicators: light green background/green border for success, light red/red border for errors
- ✅ Built static summary bar showing uploaded/completed/error counts
- ✅ Display filename for each file being processed
- ✅ Added "Copy All IDs" button to dropdown for bulk document ID copying
- ✅ Enhanced dropdown to display filename, document ID (shortened), and upload timestamp
- ✅ Increased dropdown width to 420px to prevent horizontal scrolling
- ✅ Fixed error handling for legacy files in localStorage missing ID/timestamp fields
- ✅ Fixed critical JavaScript ID mismatch bug (archive-close button) that crashed the app
- ✅ Fixed CSS specificity issue preventing archive modal from closing
- ✅ Implemented persistent duplicate detection using localStorage (survives page refreshes)
- ✅ Complete frontend rebuild with modern drag-and-drop UI (index.html, style.css, script.js)
- ✅ Fixed /query endpoint to accept JSON body (QueryRequest model with document_id and question)
- ✅ Integrated chat interface that tracks uploaded document_id and enables Q&A
- ✅ Added clipboard auto-copy for document IDs after upload
- ✅ Fixed static file serving with proper /static/ mount paths
- ✅ Added cache control headers to prevent browser caching issues
- ✅ Removed duplicate Pydantic import and cleaned up code structure

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Interface**: Single-page application with drag-and-drop PDF upload
- **Design**: Modern glassmorphic UI with animated SVG brain icon and purple gradient theme
- **Theme System**: Light/Dark mode toggle with persistent localStorage, CSS custom properties for dynamic theming
- **Upload Flow**: Converts PDF to base64 → sends to /upload-base64 → displays document_id and chunk count
- **Chat Flow**: Stores document_id → sends questions with document_id to /query → displays GPT answers
- **Features**: Auto-clipboard copy, Enter key support, disabled button during processing, animated brain icon, theme switcher

## Backend Architecture
- **Framework**: FastAPI with async/await patterns for handling file uploads
- **Runtime**: Python with uvicorn ASGI server
- **Design Pattern**: Stateless API - frontend tracks document_id, backend queries Pinecone

## Document Processing Pipeline
- **PDF Parsing**: PyPDF2 library extracts text from uploaded PDF files
- **Text Chunking**: LangChain's RecursiveCharacterTextSplitter breaks documents into overlapping chunks (1000 chars with 200 char overlap)
- **Rationale**: Overlapping chunks preserve context across boundaries, improving retrieval quality

## Vector Storage Strategy
- **Database**: Pinecone vector database (index: "mbti-knowledge")
- **Purpose**: Stores document embeddings for semantic search and retrieval
- **Design Choice**: Cloud-hosted vector DB chosen for scalability and managed infrastructure
- **Query Strategy**: Filters by doc_id to retrieve only chunks from specified document

## Embedding Generation
- **Provider**: OpenAI API (text-embedding-ada-002 model)
- **Integration**: Direct OpenAI client usage (not through LangChain)
- **Performance**: Batch processing all embeddings before upserting to Pinecone

## API Structure
- **Upload Binary**: `POST /upload` - Accepts multipart/form-data PDF files
- **Upload Base64**: `POST /upload-base64` - Accepts JSON with pdf_base64 and filename (for ChatGPT integration)
- **Query**: `POST /query` - Accepts JSON with document_id and question (Pydantic QueryRequest model)
- **Frontend**: `GET /` - Serves index.html with cache control headers
- **Static Files**: `/static/*` - Serves CSS, JS, and other static assets
- **Docs**: `GET /docs` - Built-in FastAPI Swagger UI documentation
- **Response Format**: JSONResponse for standardized API responses
- **CORS**: Enabled for all origins

## Configuration Management
- **Environment Variables**: Replit Secrets for API keys (OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX)
- **Client Initialization**: Lazy initialization pattern with helper functions that check for API keys before creating clients
- **Port**: 5000 (configurable via PORT env var)

# File Structure

```
/
├── main.py              # FastAPI backend with all endpoints
├── index.html           # Frontend HTML with upload and chat UI
├── style.css            # Complete styling (base + upload + chat)
├── script.js            # Upload + chat functionality with document_id tracking
├── requirements.txt     # Python dependencies
└── replit.md           # This documentation file
```

# External Dependencies

## Vector Database
- **Pinecone**: Cloud vector database for storing and querying embeddings
- **Index Name**: "mbti-knowledge" (suggests MBTI personality-related knowledge base)
- **Authentication**: API key-based

## AI/ML Services
- **OpenAI API**: Text embedding (text-embedding-ada-002) and GPT-3.5-turbo for Q&A
- **Authentication**: API key-based via Replit Secrets
- **Error Handling**: Comprehensive try/catch blocks with debug logging

## Document Processing
- **PyPDF2**: PDF parsing and text extraction
- **LangChain**: Text splitting utilities (RecursiveCharacterTextSplitter)

## Web Framework
- **FastAPI**: Async web framework for REST API
- **Uvicorn**: ASGI server for running the application
- **Pydantic**: Data validation with QueryRequest model

## Deployment
- **Platform**: Replit with 24/7 uptime capability
- **Run Command**: `python main.py`
- **Port**: 5000
- **Secrets Required**: OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX
- **Production URL**: https://axis-of-mind.replit.app
