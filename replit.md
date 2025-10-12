# Overview

This is a FastAPI-based PDF Q&A application that allows users to upload PDF documents, processes them into chunks, stores them in Pinecone vector database, and enables querying the documents using OpenAI's GPT for intelligent answers based on document content. The app is fully functional and ready for deployment on Replit with 24/7 uptime.

# Recent Changes (October 12, 2025)

- ✅ Migrated to new Pinecone API (Pinecone class instead of deprecated pinecone.init())
- ✅ Optimized upload performance with batch Pinecone upserts (prevents timeouts)
- ✅ Added CORS middleware for cross-origin access
- ✅ Using FastAPI's built-in /docs and /openapi.json endpoints
- ✅ Added comprehensive debug logging (🛬 file receipt, ❌ errors, ✅ success)
- ✅ All dependencies confirmed in requirements.txt
- ✅ Server configured to run on port 5000

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: FastAPI with async/await patterns for handling file uploads
- **Runtime**: Python with uvicorn ASGI server
- **Design Pattern**: Stateless API with in-memory temporary storage (`pdf_store` dict) for tracking uploaded PDFs

## Document Processing Pipeline
- **PDF Parsing**: PyPDF2 library extracts text from uploaded PDF files
- **Text Chunking**: LangChain's RecursiveCharacterTextSplitter breaks documents into overlapping chunks (1000 chars with 200 char overlap)
- **Rationale**: Overlapping chunks preserve context across boundaries, improving retrieval quality

## Vector Storage Strategy
- **Database**: Pinecone vector database (index: "mbti-knowledge")
- **Purpose**: Stores document embeddings for semantic search and retrieval
- **Design Choice**: Cloud-hosted vector DB chosen for scalability and managed infrastructure

## Embedding Generation
- **Provider**: OpenAI API (text-embedding-ada-002 model)
- **Integration**: Direct OpenAI client usage (not through LangChain)
- **Performance**: Batch processing all embeddings before upserting to Pinecone

## API Structure
- **Upload**: `POST /upload` - Accepts PDF files, chunks text, generates embeddings, stores in Pinecone
- **Query**: `POST /query` - Accepts document_id and question, retrieves relevant chunks, generates GPT answer
- **Docs**: `GET /docs` - Built-in FastAPI Swagger UI documentation
- **OpenAPI**: `GET /openapi.json` - API schema
- **Response Format**: JSONResponse for standardized API responses
- **CORS**: Enabled for all origins

## Configuration Management
- **Environment Variables**: Replit Secrets for API keys (OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX)
- **Client Initialization**: Lazy initialization pattern with helper functions that check for API keys before creating clients
- **Port**: 5000 (configurable via PORT env var)

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

## Deployment
- **Platform**: Replit with 24/7 uptime capability
- **Run Command**: `python main.py`
- **Port**: 5000
- **Secrets Required**: OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX
- **URL**: https://mbti-pdf-api--jeralynfrose.replit.app