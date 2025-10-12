# Overview

This is a FastAPI-based PDF knowledge management system that processes uploaded PDF documents, chunks their content, and stores embeddings in Pinecone vector database for retrieval. The system uses OpenAI for generating embeddings and LangChain for intelligent text splitting. It's designed to build a knowledge base from PDF documents that can be queried later (likely for RAG-based applications).

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
- **Provider**: OpenAI API for creating text embeddings
- **Integration**: Direct OpenAI client usage (not through LangChain)
- **Note**: The upload endpoint appears incomplete - embedding generation and Pinecone upsert logic is not yet implemented

## API Structure
- **Health Check**: `GET /test-connection` - Simple status endpoint
- **Upload**: `POST /upload` - Accepts PDF files via multipart/form-data
- **Response Format**: JSONResponse for standardized API responses

## Configuration Management
- **Environment Variables**: API keys stored in environment (PINECONE_API_KEY, OPENAI_API_KEY)
- **Client Initialization**: Lazy initialization pattern with helper functions that check for API keys before creating clients

# External Dependencies

## Vector Database
- **Pinecone**: Cloud vector database for storing and querying embeddings
- **Index Name**: "mbti-knowledge" (suggests MBTI personality-related knowledge base)
- **Authentication**: API key-based

## AI/ML Services
- **OpenAI API**: Text embedding generation (model not specified in code)
- **Authentication**: API key-based
- **Error Handling**: OpenAIError exception imported but not yet implemented

## Document Processing
- **PyPDF2**: PDF parsing and text extraction
- **LangChain**: Text splitting utilities (RecursiveCharacterTextSplitter)

## Web Framework
- **FastAPI**: Async web framework for REST API
- **Uvicorn**: ASGI server for running the application

## Testing Infrastructure
- **Deployment Target**: Replit hosting platform (evidenced by test_upload.py URL)
- **Test Client**: Simple requests-based uploader for manual testing