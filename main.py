import os
import uuid
import io
import base64
import json
import httpx
import csv
import tempfile
import subprocess
from datetime import datetime, timezone, timedelta
from collections import deque
from contextlib import asynccontextmanager
from urllib.parse import quote
from fastapi import FastAPI, UploadFile, File, Request, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
from pinecone import Pinecone
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from pydub import AudioSegment
import psycopg2
from psycopg2.extras import RealDictCursor
import pytz
from youtube_transcript_api import YouTubeTranscriptApi
import re
import requests
from http.cookiejar import MozillaCookieJar

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
DATABASE_URL = os.getenv("DATABASE_URL")

# === Startup Logging ===
print("🚀 Starting InnerVerse...")
print(f"✅ OPENAI_API_KEY: {'SET' if OPENAI_API_KEY else 'MISSING'}")
print(f"✅ PINECONE_API_KEY: {'SET' if PINECONE_API_KEY else 'MISSING'}")
print(f"✅ PINECONE_INDEX: {'SET' if PINECONE_INDEX else 'MISSING'}")
print(f"✅ DATABASE_URL: {'SET' if DATABASE_URL else 'MISSING'}")

# === YouTube Cookies Helper ===
def get_youtube_session_with_cookies():
    """Create a requests session with YouTube cookies loaded"""
    session = requests.Session()
    cookies_file = "youtube_cookies.txt"
    
    if os.path.exists(cookies_file):
        try:
            cookie_jar = MozillaCookieJar(cookies_file)
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cookie_jar
            print(f"✅ Loaded YouTube cookies for transcript API")
        except Exception as e:
            print(f"⚠️ Could not load cookies: {e}")
    else:
        print(f"⚠️ youtube_cookies.txt not found - FREE transcripts may be blocked by YouTube")
    
    return session

# === Usage Tracking ===
usage_log = deque(maxlen=1000)  # Keep last 1000 API calls
request_timestamps = deque(maxlen=1000)  # For rate limiting

# Pricing per 1K tokens (as of Oct 2025)
PRICING = {
    "text-embedding-ada-002": 0.0001,  # per 1K tokens
    "gpt-3.5-turbo-input": 0.0005,     # per 1K tokens
    "gpt-3.5-turbo-output": 0.0015,    # per 1K tokens
    "whisper-1": 0.006,                # per minute of audio
}

# === Database Functions ===
def get_db_connection():
    """Get PostgreSQL database connection"""
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set - cost tracking will not work")
        return None
    return psycopg2.connect(DATABASE_URL)

def init_database():
    """Initialize database tables for API usage tracking with robust error handling"""
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set - skipping database initialization (cost tracking disabled)")
        return False
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempting database connection (attempt {attempt + 1}/{max_retries})...")
            conn = get_db_connection()
            if not conn:
                print(f"⚠️ Database connection returned None")
                return False
            
            cursor = conn.cursor()
            
            # Create api_usage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    operation VARCHAR(100) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cost DECIMAL(10, 6) NOT NULL
                )
            """)
            
            # Create index on timestamp for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp 
                ON api_usage(timestamp DESC)
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Database initialized successfully")
            return True
            
        except psycopg2.OperationalError as e:
            print(f"⚠️ Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                import time
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"❌ Database initialization failed after {max_retries} attempts - app will continue without cost tracking")
                return False
        except Exception as e:
            print(f"❌ Unexpected database error: {str(e)}")
            return False
    
    return False

def log_api_usage(operation, model, input_tokens=0, output_tokens=0, cost=0.0):
    """Log API usage with timestamp and cost to database"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_usage (operation, model, input_tokens, output_tokens, cost)
            VALUES (%s, %s, %s, %s, %s)
        """, (operation, model, input_tokens, output_tokens, round(cost, 6)))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"💰 API Usage: {operation} | Model: {model} | Cost: ${cost:.6f}")
    except Exception as e:
        print(f"❌ Failed to log API usage: {str(e)}")
        # Fallback to in-memory logging if database fails
        usage_log.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 6)
        })

def check_rate_limit(max_requests_per_hour=100):
    """Check if rate limit is exceeded"""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    
    # Remove old timestamps
    while request_timestamps and datetime.fromisoformat(request_timestamps[0]) < one_hour_ago:
        request_timestamps.popleft()
    
    # Check limit
    if len(request_timestamps) >= max_requests_per_hour:
        return False, len(request_timestamps)
    
    # Add current timestamp
    request_timestamps.append(now.isoformat())
    return True, len(request_timestamps)

# Initialize clients
def get_openai_client():
    openai.api_key = OPENAI_API_KEY
    return openai


def get_pinecone_client():
    if not PINECONE_API_KEY or not PINECONE_INDEX:
        return None
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)


# Split PDF text into chunks
def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                              chunk_overlap=chunk_overlap)
    chunks = splitter.split_text(text)
    return chunks


# Load InnerVerse taxonomy schema
def load_innerverse_schema():
    """Load the MBTI/Jungian taxonomy schema for auto-tagging"""
    try:
        with open('innerverse_schema.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ innerverse_schema.json not found - auto-tagging disabled")
        return None


# Auto-tag document using GPT and InnerVerse schema
async def auto_tag_document(text, filename, openai_client):
    """
    Analyze document content and extract MBTI/Jungian taxonomy tags using GPT.
    Returns a list of relevant tags from the InnerVerse Intelligence Layer.
    """
    schema = load_innerverse_schema()
    if not schema:
        return []
    
    # Sample first 3000 chars for analysis (balance cost vs accuracy)
    sample_text = text[:3000] if len(text) > 3000 else text
    
    # Build prompt with schema context
    prompt = f"""You are an expert in MBTI, Jungian psychology, and cognitive functions. Analyze this document and extract ALL relevant taxonomy tags from the InnerVerse Intelligence Layer schema.

Document Title: {filename}
Document Sample: {sample_text}

TAXONOMY SCHEMA (6 Layers):

1. COGNITIVE ARCHITECTURE
- Cognitive Functions: Fe, Fi, Te, Ti, Ne, Ni, Se, Si
- Function Axes: Fe-Ti, Te-Fi, Ne-Si, Ni-Se
- Cognitive Roles: Hero, Parent, Child, Inferior, Nemesis, Critic, Trickster, Demon
- Cognitive Polarities: Thinking vs Feeling, Intuition vs Sensing, Judging vs Perceiving

2. TYPOLOGICAL STRUCTURES
- Four Sides of Mind: Ego, Subconscious, Unconscious, Shadow, Superego
- Interaction Styles: Directing, Initiating, Responding, Informing
- Temperaments: Artisan, Guardian, Idealist, Rational
- Quadras: Alpha, Beta, Gamma, Delta
- Loops & Grips: Ne-Fi loop, Ti-Ne loop, Se-Ni grip, etc.

3. TYPE-SPECIFIC INDEXING
- MBTI Types: INTJ, INTP, ENTJ, ENTP, INFJ, INFP, ENFJ, ENFP, ISTJ, ISFJ, ESTJ, ESFJ, ISTP, ISFP, ESTP, ESFP
- Type Pair Dynamics: Golden Pair, Silver Pair, Shadow Pair
- Intertype Relations: Duality, Conflict, Mirage, Supervision, Activation
- Compatibility Themes: Love Languages, Empathy Mismatches
- Developmental Stages: Childhood Imprinting, Midlife Individuation

4. DEPTH PSYCHOLOGY & JUNGIAN
- Archetypes: Hero, Anima, Animus, Shadow, Self, Trickster
- Shadow Integration, Individuation Process
- Complexes: Mother Complex, Father Complex, Inferiority Complex
- Dream Symbolism, Active Imagination

5. BEHAVIORAL EXPRESSION
- Communication Styles: Fe Harmony Speech, Ti Precision Speech, etc.
- Emotional Regulation: Fi Internal Processing, Fe External Harmony
- Conflict Resolution, Energy Management
- Shadow Triggers & Defense Mechanisms

6. INTEGRATION & META
- Function Interaction Maps: Fe → Ne, Ti → Si, etc.
- Cross-System Overlays: MBTI + Enneagram, MBTI + Temperament
- Type Evolution: Type Maturation, Age-Based Development
- Consciousness Levels, Metaphorical Frameworks

INSTRUCTIONS:
1. Read the document sample carefully
2. Identify ALL relevant tags from the taxonomy above
3. Return ONLY short tag names - NO category prefixes (e.g., "Sexual Compatibility" NOT "Compatibility Themes: Sexual Compatibility")
4. Return ONLY a JSON array of tag strings, nothing else
5. Be thorough - include any tag that's clearly discussed in the document
6. Format: ["tag1", "tag2", "tag3"]

CORRECT examples:
["Fe", "ENFJ", "Fe-Ti", "Golden Pair", "Shadow Integration", "Sexual Compatibility", "Emotional Compatibility"]

WRONG examples (DO NOT DO THIS):
["Compatibility Themes: Sexual Compatibility", "Developmental Stages: Relationship Success"]

Your response (JSON array only):"""

    try:
        print(f"🏷️ Auto-tagging document: {filename}")
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert MBTI/Jungian analyst. Extract taxonomy tags from documents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # Track usage (calculate cost from input + output tokens)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens / 1000) * PRICING["gpt-3.5-turbo-input"] + \
               (output_tokens / 1000) * PRICING["gpt-3.5-turbo-output"]
        log_api_usage("auto_tagging", "gpt-3.5-turbo", 
                      input_tokens=input_tokens, 
                      output_tokens=output_tokens, 
                      cost=cost)
        
        # Parse tags from response
        response_text = response.choices[0].message.content.strip()
        tags = json.loads(response_text)
        
        print(f"✅ Extracted {len(tags)} tags: {tags[:5]}..." if len(tags) > 5 else f"✅ Extracted {len(tags)} tags: {tags}")
        
        return tags
        
    except Exception as e:
        print(f"⚠️ Auto-tagging failed: {str(e)}")
        return []




# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app on startup and cleanup on shutdown"""
    print("🚀 FastAPI lifespan startup triggered")
    print("📋 Initializing InnerVerse...")
    
    db_initialized = init_database()
    
    if db_initialized:
        print("✅ Database connection verified")
    else:
        print("⚠️ App starting without database - cost tracking unavailable")
    
    print("✅ App initialization complete - ready to accept requests")
    print("🌐 Health check available at /health")
    
    yield
    
    print("👋 Shutting down InnerVerse...")

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Axis of Mind API Docs")


# Pydantic model for base64 upload
class Base64Upload(BaseModel):
    pdf_base64: str
    filename: str = "document.pdf"


# === Upload PDF (Base64 for ChatGPT) ===
@app.post("/upload-base64")
async def upload_pdf_base64(data: Base64Upload):
    try:
        # Log the raw incoming JSON structure
        print(f"📥 Raw JSON received: {data.model_dump()}")
        print(f"🛬 Received base64 file: {data.filename}")
        print(f"📊 Base64 length: {len(data.pdf_base64)} characters")
        
        # Fix base64 padding if needed
        base64_str = data.pdf_base64
        missing_padding = len(base64_str) % 4
        if missing_padding:
            base64_str += '=' * (4 - missing_padding)
            print(f"🔧 Added {4 - missing_padding} padding characters")
        
        # Decode base64 to bytes
        pdf_bytes = base64.b64decode(base64_str)
        
        # Check for PDF EOF marker
        if not pdf_bytes.endswith(b'%%EOF'):
            print("⚠️ PDF may be corrupted or incomplete (EOF not found)")
        
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        page_count = len(pdf_reader.pages)
        text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
        chunks = chunk_text(text)
        print(f"📄 Uploading {len(chunks)} chunks to Pinecone")

        doc_id = str(uuid.uuid4())
        openai_client = get_openai_client()
        pinecone_index = get_pinecone_client()

        if not openai_client or not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "OpenAI or Pinecone client not initialized"})

        # Auto-tag document with InnerVerse taxonomy
        tags = await auto_tag_document(text, data.filename, openai_client)

        # Batch embedding + upsert
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            # Show progress for large documents
            if i % 50 == 0 and i > 0:
                print(f"📊 Processing chunk {i}/{len(chunks)}...")
            
            response = openai_client.embeddings.create(
                input=chunk, model="text-embedding-ada-002", timeout=60)
            vector = response.data[0].embedding
            vectors_to_upsert.append((f"{doc_id}-{i}", vector, {
                "text": chunk,
                "doc_id": doc_id,
                "filename": data.filename,
                "upload_timestamp": datetime.now().isoformat(),
                "tags": tags
            }))

        # Upload in batches to avoid Pinecone's 4MB request limit
        if vectors_to_upsert:
            batch_size = 50  # Safe batch size to stay under 4MB
            total_batches = (len(vectors_to_upsert) + batch_size - 1) // batch_size
            
            for batch_num in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[batch_num:batch_num + batch_size]
                pinecone_index.upsert(vectors=batch)
                current_batch = (batch_num // batch_size) + 1
                print(f"📤 Uploaded batch {current_batch}/{total_batches} ({len(batch)} vectors)")
            
            print(f"✅ Successfully uploaded {len(vectors_to_upsert)} total chunks")

        return {
            "message": "PDF uploaded and indexed with InnerVerse Intelligence Layer",
            "document_id": doc_id,
            "chunks_count": len(chunks),
            "tags": tags,
            "tags_count": len(tags)
        }

    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Upload PDF (File for regular clients) ===
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # ✅ Debug log — confirms if file is even received
        file_size_mb = 0
        print(f"🛬 Received file: {file.filename}")

        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)  # Convert to MB
        print(f"📦 File size: {file_size_mb:.2f} MB")
        
        pdf_reader = PdfReader(io.BytesIO(contents))
        page_count = len(pdf_reader.pages)
        text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
        chunks = chunk_text(text)
        print(f"📄 Processing {len(chunks)} chunks from {page_count} pages")

        doc_id = str(uuid.uuid4())
        openai_client = get_openai_client()
        pinecone_index = get_pinecone_client()

        if not openai_client or not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "OpenAI or Pinecone client not initialized"})

        # Auto-tag document with InnerVerse taxonomy
        tags = await auto_tag_document(text, file.filename, openai_client)

        # Batch embedding + upsert
        vectors_to_upsert = []
        embed_start = datetime.now()
        
        for i, chunk in enumerate(chunks):
            # Show progress for large documents
            if i % 50 == 0:
                elapsed = (datetime.now() - embed_start).total_seconds()
                print(f"📊 Processing chunk {i}/{len(chunks)} (elapsed: {elapsed:.1f}s)...")
            
            try:
                response = openai_client.embeddings.create(
                    input=chunk, model="text-embedding-ada-002", timeout=120)  # Increased timeout
                vector = response.data[0].embedding
                vectors_to_upsert.append((f"{doc_id}-{i}", vector, {
                    "text": chunk,
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "upload_timestamp": datetime.now().isoformat(),
                    "tags": tags
                }))
            except Exception as embed_error:
                print(f"❌ Embedding error on chunk {i}: {str(embed_error)}")
                raise Exception(f"Failed to embed chunk {i}/{len(chunks)}: {str(embed_error)}")

        # Upload in batches to avoid Pinecone's 4MB request limit
        if vectors_to_upsert:
            batch_size = 50  # Safe batch size to stay under 4MB
            total_batches = (len(vectors_to_upsert) + batch_size - 1) // batch_size
            upsert_start = datetime.now()
            
            for batch_num in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[batch_num:batch_num + batch_size]
                try:
                    pinecone_index.upsert(vectors=batch)
                    current_batch = (batch_num // batch_size) + 1
                    print(f"📤 Uploaded batch {current_batch}/{total_batches} ({len(batch)} vectors)")
                except Exception as upsert_error:
                    print(f"❌ Pinecone upsert error on batch {current_batch}: {str(upsert_error)}")
                    raise Exception(f"Failed to upload to Pinecone: {str(upsert_error)}")
            
            upsert_elapsed = (datetime.now() - upsert_start).total_seconds()
            total_elapsed = (datetime.now() - embed_start).total_seconds()
            print(f"✅ Successfully uploaded {len(vectors_to_upsert)} chunks")
            print(f"⏱️ Total time: {total_elapsed:.1f}s (upload: {upsert_elapsed:.1f}s)")

        return {
            "message": "PDF uploaded and indexed with InnerVerse Intelligence Layer",
            "document_id": doc_id,
            "chunks_count": len(chunks),
            "filename": file.filename,
            "tags": tags,
            "tags_count": len(tags)
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Upload error for {file.filename if 'file' in locals() else 'unknown'}: {error_msg}")
        # Return more detailed error
        return JSONResponse(status_code=500, content={
            "error": f"Upload failed: {error_msg}",
            "filename": file.filename if 'file' in locals() else "unknown"
        })


# === Delete ALL Documents ===
@app.delete("/documents/all")
async def delete_all_documents():
    """Delete ALL vectors from Pinecone index"""
    try:
        pinecone_index = get_pinecone_client()
        
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"})
        
        # Delete all vectors (delete_all is faster than filtering)
        pinecone_index.delete(delete_all=True)
        
        print(f"✅ Deleted ALL vectors from Pinecone index")
        
        return {
            "message": "All documents deleted successfully"
        }
        
    except Exception as e:
        print(f"❌ Delete all error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Delete Single Document ===
@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete all vectors associated with a document ID"""
    try:
        pinecone_index = get_pinecone_client()
        
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"})
        
        # Delete all vectors with this doc_id using metadata filter
        pinecone_index.delete(filter={"doc_id": document_id})
        
        print(f"✅ Deleted all vectors for document: {document_id}")
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id
        }
        
    except Exception as e:
        print(f"❌ Delete error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Rename Document ===
class RenameDocumentRequest(BaseModel):
    new_filename: str

@app.patch("/documents/{document_id}/rename")
async def rename_document(document_id: str, request: RenameDocumentRequest):
    """Rename a document by updating its filename metadata in all vectors"""
    try:
        pinecone_index = get_pinecone_client()
        
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"})
        
        # First, fetch all vectors for this document
        dummy_vector = [0.0] * 1536
        query_response = pinecone_index.query(
            vector=dummy_vector,
            filter={"doc_id": document_id},
            top_k=10000,
            include_metadata=True
        )
        
        # Get matches
        try:
            matches = query_response.matches
        except AttributeError:
            matches = query_response.get("matches", [])
        
        if not matches:
            return JSONResponse(
                status_code=404,
                content={"error": "Document not found"})
        
        # Update each vector's metadata with new filename
        updates = []
        for match in matches:
            vector_id = getattr(match, "id", None) or match.get("id")
            metadata = getattr(match, "metadata", None) or match.get("metadata", {})
            
            # Update filename in metadata
            updated_metadata = dict(metadata) if hasattr(metadata, "items") else metadata
            updated_metadata["filename"] = request.new_filename
            
            updates.append({
                "id": vector_id,
                "metadata": updated_metadata
            })
        
        # Batch update in Pinecone (50 at a time)
        batch_size = 50
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            
            # Use upsert with same IDs to update metadata
            upsert_data = []
            for item in batch:
                # Get the original vector values
                fetch_response = pinecone_index.fetch(ids=[item["id"]])
                if hasattr(fetch_response, "vectors"):
                    vectors_dict = fetch_response.vectors
                else:
                    vectors_dict = fetch_response.get("vectors", {})
                
                if item["id"] in vectors_dict:
                    vector_data = vectors_dict[item["id"]]
                    values = getattr(vector_data, "values", None) or vector_data.get("values", [])
                    
                    upsert_data.append((
                        item["id"],
                        values,
                        item["metadata"]
                    ))
            
            if upsert_data:
                pinecone_index.upsert(vectors=upsert_data)
        
        print(f"✅ Renamed document {document_id} to '{request.new_filename}' ({len(updates)} vectors updated)")
        
        return {
            "message": "Document renamed successfully",
            "document_id": document_id,
            "new_filename": request.new_filename,
            "vectors_updated": len(updates)
        }
        
    except Exception as e:
        print(f"❌ Rename error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Generate Document Report ===
@app.get("/documents/report")
async def get_documents_report():
    """Generate a CSV report of all uploaded documents"""
    try:
        pinecone_index = get_pinecone_client()
        
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"})
        
        # Query Pinecone to get documents
        # We'll use a dummy vector query with high top_k to get many results
        dummy_vector = [0.0] * 1536  # OpenAI ada-002 has 1536 dimensions
        
        query_response = pinecone_index.query(
            vector=dummy_vector,
            top_k=10000,  # Get up to 10k results
            include_metadata=True
        )
        
        # Extract unique documents with timestamps
        documents = {}
        try:
            matches = query_response.matches  # type: ignore
        except AttributeError:
            matches = query_response.get("matches", [])  # type: ignore
        
        for match in matches:
            metadata = getattr(match, "metadata", None)
            if not metadata:
                try:
                    metadata = match.get("metadata", {})
                except (AttributeError, TypeError):
                    metadata = {}
            
            if metadata:
                doc_id = metadata.get("doc_id") if hasattr(metadata, "get") else getattr(metadata, "doc_id", None)
                filename = metadata.get("filename", "Unknown") if hasattr(metadata, "get") else getattr(metadata, "filename", "Unknown")
                timestamp = metadata.get("upload_timestamp", "N/A") if hasattr(metadata, "get") else getattr(metadata, "upload_timestamp", "N/A")
                
                if doc_id and doc_id not in documents:
                    documents[doc_id] = {"filename": filename, "timestamp": timestamp}
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["document_id", "title", "uploaded_at"])
        
        # Sort documents chronologically (earliest to latest) by timestamp
        sorted_docs = sorted(
            documents.items(),
            key=lambda x: x[1]["timestamp"] if x[1]["timestamp"] != "N/A" else "9999-99-99"
        )
        
        # Hawaii timezone (HST = UTC-10)
        hawaii_tz = timezone(timedelta(hours=-10))
        
        for doc_id, doc_info in sorted_docs:
            # Format timestamp nicely if available
            timestamp_str = doc_info["timestamp"]
            if timestamp_str != "N/A":
                try:
                    # Convert ISO format to Hawaii time
                    dt = datetime.fromisoformat(timestamp_str)
                    # If no timezone info, assume UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    # Convert to Hawaii time
                    dt_hawaii = dt.astimezone(hawaii_tz)
                    timestamp_str = dt_hawaii.strftime("%Y-%m-%d %I:%M %p")
                except:
                    pass  # Keep as-is if parsing fails
            
            writer.writerow([doc_id, doc_info["filename"], timestamp_str])
        
        # Return as downloadable file
        csv_content = output.getvalue()
        output.close()
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=document_report.csv"
            }
        )
        
    except Exception as e:
        print(f"❌ Report generation error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Get Tagged Documents (Cloud-based Tag Library) ===
@app.get("/api/tagged-documents")
async def get_tagged_documents():
    """Get all documents with their tags from Pinecone (cloud-based tag library)"""
    try:
        pinecone_index = get_pinecone_client()
        
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"})
        
        # Query Pinecone to get all documents
        dummy_vector = [0.0] * 1536  # OpenAI ada-002 has 1536 dimensions
        
        query_response = pinecone_index.query(
            vector=dummy_vector,
            top_k=10000,  # Get up to 10k results
            include_metadata=True
        )
        
        # Extract unique documents with tags
        documents = {}
        try:
            matches = query_response.matches
        except AttributeError:
            matches = query_response.get("matches", [])
        
        for match in matches:
            metadata = getattr(match, "metadata", None)
            if not metadata:
                try:
                    metadata = match.get("metadata", {})
                except (AttributeError, TypeError):
                    metadata = {}
            
            if metadata:
                doc_id = metadata.get("doc_id") if hasattr(metadata, "get") else getattr(metadata, "doc_id", None)
                filename = metadata.get("filename", "Unknown") if hasattr(metadata, "get") else getattr(metadata, "filename", "Unknown")
                timestamp = metadata.get("upload_timestamp", None) if hasattr(metadata, "get") else getattr(metadata, "upload_timestamp", None)
                tags = metadata.get("tags", []) if hasattr(metadata, "get") else getattr(metadata, "tags", [])
                
                if doc_id and doc_id not in documents:
                    documents[doc_id] = {
                        "filename": filename,
                        "tags": tags if isinstance(tags, list) else [],
                        "timestamp": timestamp or datetime.now().isoformat()
                    }
        
        print(f"✅ Retrieved {len(documents)} tagged documents from Pinecone")
        
        return {
            "documents": documents
        }
        
    except Exception as e:
        print(f"❌ Tagged documents retrieval error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Query PDF for an answer ===
class QueryRequest(BaseModel):
    document_id: str = ""  # Optional - empty string means search all documents
    question: str
    tags: list = []  # Optional - filter by InnerVerse taxonomy tags

# === YouTube Transcription Request ===
class YouTubeTranscribeRequest(BaseModel):
    youtube_url: str

# === YouTube URL Download Request (with Proxy) ===
class YouTubeDownloadRequest(BaseModel):
    youtube_url: str

# === Text to PDF Request ===
class TextToPDFRequest(BaseModel):
    text: str
    title: str = "Document"

@app.post("/query")
async def query_pdf(request: QueryRequest, authorization: str = Header(None)):
    # API Key validation (only if Authorization header is provided)
    # Web app can call without auth, but external calls (custom GPT) must provide valid token
    if authorization:
        expected_api_key = os.getenv("API_KEY")
        if not expected_api_key:
            raise HTTPException(status_code=500, detail="Server configuration error: API key not set")
        
        # Support both "Bearer <token>" and direct token formats
        token = authorization.replace("Bearer ", "").strip()
        if token != expected_api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Rate limiting check
    allowed, count = check_rate_limit(max_requests_per_hour=100)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": f"Rate limit exceeded. Maximum 100 requests per hour. You've made {count} requests in the last hour. Please try again later."
            }
        )
    
    document_id = request.document_id
    question = request.question
    filter_tags = request.tags
    openai_client = get_openai_client()
    pinecone_index = get_pinecone_client()

    if not openai_client or not pinecone_index:
        return JSONResponse(
            status_code=500,
            content={"error": "OpenAI or Pinecone client not initialized"})

    try:
        embed_response = openai_client.embeddings.create(
            input=question, model="text-embedding-ada-002")
        question_vector = embed_response.data[0].embedding
        
        # Log embedding usage
        embed_tokens = embed_response.usage.total_tokens
        embed_cost = (embed_tokens / 1000) * PRICING["text-embedding-ada-002"]
        log_api_usage("query_embedding", "text-embedding-ada-002", input_tokens=embed_tokens, cost=embed_cost)

        # Build Pinecone filter based on document_id and tags
        filter_conditions = []
        if document_id and document_id.strip():
            filter_conditions.append({"doc_id": document_id})
        if filter_tags and len(filter_tags) > 0:
            # Filter for documents that contain ANY of the specified tags
            filter_conditions.append({"tags": {"$in": filter_tags}})
        
        # Build final filter
        if len(filter_conditions) == 0:
            # No filters - search all documents
            print(f"🔍 Searching across ALL documents")
            query_response = pinecone_index.query(
                vector=question_vector,
                top_k=5,
                include_metadata=True
            )
        elif len(filter_conditions) == 1:
            # Single filter
            filter_str = f"doc_id={document_id}" if document_id else f"tags={filter_tags}"
            print(f"🔍 Searching with filter: {filter_str}")
            query_response = pinecone_index.query(
                vector=question_vector,
                top_k=5,
                include_metadata=True,
                filter=filter_conditions[0]
            )
        else:
            # Multiple filters - use $and
            print(f"🔍 Searching with filters: doc_id={document_id}, tags={filter_tags}")
            query_response = pinecone_index.query(
                vector=question_vector,
                top_k=5,
                include_metadata=True,
                filter={"$and": filter_conditions}
            )

        try:
            matches = query_response.matches  # type: ignore
        except AttributeError:
            matches = query_response.get("matches", [])  # type: ignore
        
        contexts = []
        source_docs = set()
        
        for m in matches:
            if "metadata" in m and "text" in m["metadata"]:
                contexts.append(m["metadata"]["text"])
                # Track which documents the answer came from
                if "filename" in m["metadata"]:
                    source_docs.add(m["metadata"]["filename"])
        
        if not contexts:
            return {"answer": "No relevant information found in your documents."}

        context_text = "\n\n".join(contexts)
        print(f"\n🔍 Sending context from {len(source_docs)} document(s) to GPT\n")

        # Include source information in the prompt
        sources_text = f"\n\nSources: {', '.join(source_docs)}" if source_docs else ""
        
        prompt = f"Answer the question based on the context below.\n\nContext:\n{context_text}\n\nQuestion: {question}\nAnswer:"

        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "You are a helpful assistant that answers questions based on uploaded documents. Provide clear, accurate answers based on the context provided."
            }, {
                "role": "user",
                "content": prompt
            }],
            timeout=15  # Prevents hanging
        )

        answer = completion.choices[0].message.content or "No answer generated."
        
        # Log chat completion usage
        if completion.usage:
            input_tokens = completion.usage.prompt_tokens
            output_tokens = completion.usage.completion_tokens
            chat_cost = (input_tokens / 1000) * PRICING["gpt-3.5-turbo-input"] + (output_tokens / 1000) * PRICING["gpt-3.5-turbo-output"]
            log_api_usage("chat_completion", "gpt-3.5-turbo", input_tokens=input_tokens, output_tokens=output_tokens, cost=chat_cost)
        
        # Add source information to answer if searching all docs
        if not document_id or not document_id.strip():
            if source_docs:
                answer += f"\n\n📚 Sources: {', '.join(sorted(source_docs))}"
        
        return {"answer": answer}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Google Drive Integration ===
async def get_gdrive_access_token():
    """Get Google Drive access token from Replit Connector"""
    try:
        hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
        x_replit_token = (
            f"repl {os.getenv('REPL_IDENTITY')}" if os.getenv('REPL_IDENTITY')
            else f"depl {os.getenv('WEB_REPL_RENEWAL')}" if os.getenv('WEB_REPL_RENEWAL')
            else None
        )
        
        if not x_replit_token or not hostname:
            return None
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-drive",
                headers={
                    "Accept": "application/json",
                    "X_REPLIT_TOKEN": x_replit_token
                }
            )
            data = response.json()
            if data.get("items") and len(data["items"]) > 0:
                settings = data["items"][0].get("settings", {})
                return settings.get("access_token") or settings.get("oauth", {}).get("credentials", {}).get("access_token")
        return None
    except Exception as e:
        print(f"❌ Google Drive token error: {e}")
        return None

@app.get("/api/google-api-key")
async def get_google_api_key():
    """Return Google API key for Picker"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return JSONResponse(status_code=500, content={"error": "Google API key not configured"})
    return {"api_key": api_key}

@app.get("/api/gdrive-token")
async def get_gdrive_token():
    """Get Google Drive OAuth access token"""
    token = await get_gdrive_access_token()
    if not token:
        return JSONResponse(status_code=401, content={"error": "Google Drive not connected"})
    return {"access_token": token}

@app.get("/api/gdrive-list-pdfs")
async def list_gdrive_pdfs():
    """List all PDF files from Google Drive"""
    try:
        token = await get_gdrive_access_token()
        if not token:
            return JSONResponse(status_code=401, content={"error": "Google Drive not connected"})
        
        async with httpx.AsyncClient() as client:
            # List PDF files from Google Drive
            response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "q": "mimeType='application/pdf' and trashed=false",
                    "fields": "files(id,name,size,modifiedTime)",
                    "orderBy": "modifiedTime desc",
                    "pageSize": 100
                }
            )
            
            if response.status_code != 200:
                return JSONResponse(status_code=response.status_code, content={"error": "Failed to list files"})
            
            data = response.json()
            return {"files": data.get("files", [])}
            
    except Exception as e:
        print(f"❌ Google Drive list error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/gdrive-download/{file_id}")
async def download_gdrive_file(file_id: str):
    """Download a file from Google Drive and return as base64"""
    try:
        token = await get_gdrive_access_token()
        if not token:
            return JSONResponse(status_code=401, content={"error": "Google Drive not connected"})
        
        async with httpx.AsyncClient() as client:
            # Download file from Google Drive
            response = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                return JSONResponse(status_code=response.status_code, content={"error": "Failed to download file"})
            
            # Convert to base64
            pdf_bytes = response.content
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            return {"pdf_base64": pdf_base64}
            
    except Exception as e:
        print(f"❌ Google Drive download error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === YouTube Transcription to PDF ===
@app.post("/transcribe-youtube")
async def transcribe_youtube(request: YouTubeTranscribeRequest):
    """Download YouTube audio, transcribe with Whisper, and generate PDF"""
    try:
        youtube_url = request.youtube_url
        print(f"🎬 Processing YouTube URL: {youtube_url}")
        
        # Create temp directory for audio files
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "audio.mp3")
        
        # Step 1: Download audio using yt-dlp
        print("📥 Downloading audio from YouTube...")
        try:
            # Check if yt-dlp is available
            try:
                yt_dlp_check = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=5)
                if yt_dlp_check.returncode != 0:
                    raise Exception("yt-dlp is not installed or not working")
            except FileNotFoundError:
                return JSONResponse(status_code=500, content={
                    "error": "System error: transcription service unavailable. Please try again later."
                })
            
            # Check for YouTube cookies file FIRST (before any yt-dlp commands)
            cookies_path = None
            cookies_file = "youtube_cookies.txt"
            
            if os.path.exists(cookies_file):
                # Read cookies from file
                with open(cookies_file, "r") as f:
                    cookies_content = f.read().strip()
                
                # Only use if file has actual cookies (not just comments)
                if cookies_content and not cookies_content.startswith("# Paste your"):
                    cookies_path = os.path.join(temp_dir, "cookies.txt")
                    with open(cookies_path, "w") as f:
                        f.write(cookies_content)
                    print(f"✅ Using YouTube cookies from file for authentication")
                else:
                    print(f"⚠️ youtube_cookies.txt exists but is empty or not configured")
            else:
                print(f"⚠️ youtube_cookies.txt not found - some videos may be restricted")
            
            # Get video info first (WITH cookies for age-restricted/login-required videos)
            info_command = [
                "yt-dlp",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--referer", "https://www.youtube.com/",
                "--print", "%(title)s|||%(duration)s",
                youtube_url
            ]
            
            # Add proxy if configured (helps bypass YouTube datacenter IP blocks)
            proxy_url = os.environ.get("YT_PROXY")
            if proxy_url:
                info_command.insert(1, "--proxy")
                info_command.insert(2, proxy_url)
                print(f"🌐 Using proxy for YouTube access")
            
            # Add cookies to info command if available
            if cookies_path:
                info_command.insert(1, "--cookies")
                info_command.insert(2, cookies_path)
                print(f"🔐 Metadata probe using cookies for authentication")
            
            info_result = subprocess.run(info_command, capture_output=True, text=True, timeout=30)
            
            if info_result.returncode != 0:
                # Parse error to provide helpful message
                error_msg = info_result.stderr.lower()
                
                if "private video" in error_msg or "members-only" in error_msg:
                    return JSONResponse(status_code=403, content={
                        "error": "This video is private or members-only. Try a different video."
                    })
                elif "age-restricted" in error_msg or "sign in to confirm your age" in error_msg:
                    return JSONResponse(status_code=403, content={
                        "error": "Age-restricted video. Your cookies may have expired. Update youtube_cookies.txt file."
                    })
                elif "video unavailable" in error_msg or "removed" in error_msg:
                    return JSONResponse(status_code=404, content={
                        "error": "Video unavailable or removed. Try a different video."
                    })
                elif "region" in error_msg or "not available in your country" in error_msg:
                    return JSONResponse(status_code=403, content={
                        "error": "Video blocked in this region. Try a different video."
                    })
                else:
                    return JSONResponse(status_code=400, content={
                        "error": "Unable to access video. If multiple videos fail, your YouTube cookies may be expired - update youtube_cookies.txt and republish. Otherwise, check the URL or try a different video."
                    })
            
            info_parts = info_result.stdout.strip().split("|||")
            video_title = info_parts[0] if len(info_parts) > 0 else "YouTube Video"
            video_duration = int(info_parts[1]) if len(info_parts) > 1 and info_parts[1].isdigit() else 0
            
            print(f"📺 Video: {video_title} ({video_duration}s / {video_duration//60} min)")
            
            # Try to find ffmpeg location
            ffmpeg_location = None
            try:
                ffmpeg_result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True, timeout=5)
                if ffmpeg_result.returncode == 0 and ffmpeg_result.stdout.strip():
                    ffmpeg_location = ffmpeg_result.stdout.strip()
                    print(f"✅ Found ffmpeg at: {ffmpeg_location}")
                else:
                    print("⚠️ ffmpeg not found in PATH")
            except Exception as e:
                print(f"⚠️ Could not check for ffmpeg: {e}")
            
            # Download audio with compression (32kbps mono for Whisper)
            # This keeps files under 25MB for videos up to ~90 minutes
            download_command = [
                "yt-dlp",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--referer", "https://www.youtube.com/",
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000 -b:a 32k",  # Mono, 16kHz, 32kbps
                "-o", audio_path,
                youtube_url
            ]
            
            # Add proxy if configured
            if proxy_url:
                download_command.insert(1, "--proxy")
                download_command.insert(2, proxy_url)
            
            # Add cookies if available
            if cookies_path:
                download_command.insert(1, "--cookies")
                download_command.insert(2, cookies_path)
            
            # Add ffmpeg location if found
            if ffmpeg_location and os.path.dirname(ffmpeg_location):
                download_command.insert(1, "--ffmpeg-location")
                download_command.insert(2, os.path.dirname(ffmpeg_location))
            
            result = subprocess.run(download_command, capture_output=True, text=True, timeout=1800)
            
            if result.returncode != 0:
                # Parse download error
                error_msg = result.stderr.lower()
                
                if "http error 403" in error_msg or "forbidden" in error_msg:
                    return JSONResponse(status_code=403, content={
                        "error": "Video blocked. Your cookies may have expired. Update youtube_cookies.txt file."
                    })
                elif "http error 404" in error_msg:
                    return JSONResponse(status_code=404, content={
                        "error": "Video not found. Check the URL and try again."
                    })
                elif "sign in" in error_msg or "login" in error_msg:
                    return JSONResponse(status_code=401, content={
                        "error": "Login required. Add your cookies to youtube_cookies.txt file to access this video."
                    })
                else:
                    return JSONResponse(status_code=500, content={
                        "error": "Download failed. Try a different video or refresh your cookies."
                    })
            
            # Check if file was created
            if not os.path.exists(audio_path):
                return JSONResponse(status_code=500, content={
                    "error": "Audio extraction failed. Try a different video."
                })
                
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"✅ Audio downloaded: {file_size_mb:.1f}MB")
            
        except subprocess.TimeoutExpired:
            return JSONResponse(status_code=408, content={
                "error": "Download timed out after 30 minutes. This could be due to slow network, video restrictions, or expired cookies. Try refreshing your cookies or a different video."
            })
        except Exception as e:
            error_str = str(e).lower()
            if "cookie" in error_str:
                return JSONResponse(status_code=401, content={
                    "error": "Cookie error. Check your youtube_cookies.txt file."
                })
            else:
                return JSONResponse(status_code=500, content={
                    "error": f"Unable to process video. Try a different one."
                })
        
        # Step 2: Transcribe with OpenAI Whisper
        print("🎤 Transcribing with Whisper...")
        try:
            openai_client = get_openai_client()
            if not openai_client:
                return JSONResponse(status_code=500, content={"error": "OpenAI client not initialized"})
            
            file_size = os.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # If file is under 25MB, transcribe directly
            if file_size < 25 * 1024 * 1024:
                print(f"📝 File size {file_size_mb:.1f}MB - transcribing directly")
                
                # Get audio duration for cost calculation
                audio = AudioSegment.from_file(audio_path)
                duration_minutes = len(audio) / (1000 * 60)  # Convert ms to minutes
                
                with open(audio_path, "rb") as audio_file:
                    transcript_response = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                        timeout=600  # 10 minute timeout for Whisper
                    )
                transcript = transcript_response if isinstance(transcript_response, str) else transcript_response.text
                
                # Log Whisper API usage
                whisper_cost = duration_minutes * PRICING["whisper-1"]
                log_api_usage("whisper", "whisper-1", input_tokens=0, output_tokens=0, cost=whisper_cost)
                print(f"💰 Whisper cost: ${whisper_cost:.4f} ({duration_minutes:.2f} minutes)")
                
            else:
                # File is too large - split into chunks
                print(f"📝 File size {file_size_mb:.1f}MB - splitting into chunks for transcription")
                
                # Load audio with pydub
                audio = AudioSegment.from_file(audio_path)
                chunk_length_ms = 10 * 60 * 1000  # 10 minutes per chunk
                total_chunks = len(audio) // chunk_length_ms + (1 if len(audio) % chunk_length_ms else 0)
                total_duration_minutes = len(audio) / (1000 * 60)
                
                transcriptions = []
                
                for i in range(0, len(audio), chunk_length_ms):
                    chunk = audio[i:i + chunk_length_ms]
                    chunk_path = os.path.join(temp_dir, f"chunk_{i//chunk_length_ms}.mp3")
                    chunk_duration_minutes = len(chunk) / (1000 * 60)
                    
                    # Export chunk as compressed MP3
                    chunk.export(chunk_path, format="mp3", bitrate="32k", parameters=["-ac", "1", "-ar", "16000"])
                    
                    # Transcribe chunk
                    chunk_num = i // chunk_length_ms + 1
                    print(f"  📝 Transcribing chunk {chunk_num}/{total_chunks}...")
                    
                    with open(chunk_path, "rb") as chunk_file:
                        chunk_response = openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=chunk_file,
                            response_format="text",
                            timeout=600  # 10 minute timeout per chunk
                        )
                    
                    chunk_transcript = chunk_response if isinstance(chunk_response, str) else chunk_response.text
                    transcriptions.append(chunk_transcript)
                    
                    # Log Whisper API usage for this chunk
                    chunk_cost = chunk_duration_minutes * PRICING["whisper-1"]
                    log_api_usage("whisper", "whisper-1", input_tokens=0, output_tokens=0, cost=chunk_cost)
                    
                    # Clean up chunk file
                    os.remove(chunk_path)
                
                # Combine all transcriptions
                transcript = " ".join(transcriptions)
                print(f"✅ Combined {len(transcriptions)} chunks")
                print(f"💰 Total Whisper cost: ${total_duration_minutes * PRICING['whisper-1']:.4f} ({total_duration_minutes:.2f} minutes)")
            
            print(f"✅ Transcription complete: {len(transcript)} characters")
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "quota" in error_str or "rate limit" in error_str:
                return JSONResponse(status_code=429, content={
                    "error": "OpenAI rate limit reached. Wait a few minutes and try again."
                })
            elif "api key" in error_str or "unauthorized" in error_str:
                return JSONResponse(status_code=401, content={
                    "error": "OpenAI API key error. Check your OPENAI_API_KEY in Secrets."
                })
            elif "timeout" in error_str:
                return JSONResponse(status_code=408, content={
                    "error": "Transcription timed out. Try a shorter video."
                })
            else:
                return JSONResponse(status_code=500, content={
                    "error": "Transcription failed. The audio may be corrupted or too complex."
                })
        finally:
            # Clean up audio file
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
        
        # Step 3: Generate PDF
        print("📄 Generating PDF...")
        try:
            pdf_filename = f"transcript_{uuid.uuid4().hex[:8]}.pdf"
            pdf_path = os.path.join("/tmp", pdf_filename)
            
            # Create PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#5B21B6',
                spaceAfter=12
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=16,
                alignment=TA_LEFT
            )
            
            # Build PDF content
            story = []
            
            # Title
            story.append(Paragraph(f"<b>{video_title}</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            story.append(Paragraph(f"Transcribed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", metadata_style))
            story.append(Paragraph(f"Source: {youtube_url}", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Transcript text - split into paragraphs
            paragraphs = transcript.split('\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
                    story.append(Spacer(1, 0.15*inch))
            
            # Build PDF
            doc.build(story)
            print(f"✅ PDF created: {pdf_path}")
            
            # Return the PDF as a download
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"{video_title[:50].replace('/', '-')}.pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{video_title[:50].replace('/', '-')}.pdf\""
                }
            )
            
        except Exception as e:
            return JSONResponse(status_code=500, content={
                "error": "Failed to create PDF. The transcription may contain special characters."
            })
        
    except Exception as e:
        print(f"❌ YouTube transcription error: {str(e)}")
        return JSONResponse(status_code=500, content={
            "error": "Something went wrong. Please try again or use a different video."
        })


# === FREE YouTube Transcript (No Whisper Cost) ===
@app.post("/transcribe-youtube-free")
async def transcribe_youtube_free(request: YouTubeTranscribeRequest):
    """Get FREE YouTube transcript (no Whisper API costs) - only works for videos with captions"""
    try:
        youtube_url = request.youtube_url
        print(f"🎬 Getting FREE transcript for: {youtube_url}")
        
        # Extract video ID from URL
        video_id = None
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)',
            r'youtube\.com/embed/([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            return JSONResponse(status_code=400, content={
                "error": "Invalid YouTube URL. Please check the URL and try again."
            })
        
        print(f"📺 Video ID: {video_id}")
        
        # Try to get the transcript
        try:
            # Get transcript (tries manual first, then auto-generated, any language)
            # Use cookies to bypass YouTube's IP blocking for cloud providers
            session = get_youtube_session_with_cookies()
            ytt_api = YouTubeTranscriptApi(http_client=session)
            transcript_list = ytt_api.list(video_id)
            
            transcript_data = None
            language = 'unknown'
            
            # Try manual transcripts first (any language)
            try:
                for transcript in transcript_list:
                    if not transcript.is_generated:
                        transcript_data = transcript.fetch()
                        language = transcript.language
                        print(f"📝 Found manual transcript in {language}")
                        break
            except:
                pass
            
            # If no manual transcript, try auto-generated (any language)
            if not transcript_data:
                try:
                    for transcript in transcript_list:
                        if transcript.is_generated:
                            transcript_data = transcript.fetch()
                            language = f"{transcript.language} (auto)"
                            print(f"🤖 Found auto-generated transcript in {language}")
                            break
                except:
                    pass
            
            # If still nothing, try the simple fetch method as fallback
            if not transcript_data:
                transcript_data = ytt_api.fetch(video_id, languages=['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'ko', 'zh', 'ru', 'ar', 'hi'])
                language = 'fallback'
            
            # Combine all transcript segments into one text
            transcript = ' '.join([entry['text'] for entry in transcript_data])
            
            print(f"✅ FREE transcript retrieved ({len(transcript)} characters, {language})")
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"❌ Transcript error: {e}")
            
            if 'transcript' in error_str and 'disabled' in error_str:
                return JSONResponse(status_code=404, content={
                    "error": "This video has captions disabled. Use the 'Transcribe with Whisper' button instead (costs ~$0.006/min)."
                })
            elif 'subtitles are disabled' in error_str or 'no transcript' in error_str:
                return JSONResponse(status_code=404, content={
                    "error": "No captions available for this video. Use the 'Transcribe with Whisper' button instead (costs ~$0.006/min)."
                })
            elif 'private' in error_str or 'unavailable' in error_str:
                return JSONResponse(status_code=403, content={
                    "error": "Video is private or unavailable. Try a different video."
                })
            else:
                return JSONResponse(status_code=404, content={
                    "error": f"Could not get captions for this video. Use the 'Transcribe with Whisper' button instead (costs ~$0.006/min)."
                })
        
        # Get video title using yt-dlp
        video_title = "YouTube Video"
        try:
            info_command = ["yt-dlp", "--print", "%(title)s", youtube_url]
            info_result = subprocess.run(info_command, capture_output=True, text=True, timeout=10)
            if info_result.returncode == 0 and info_result.stdout.strip():
                video_title = info_result.stdout.strip()
        except:
            pass  # Use default title if yt-dlp fails
        
        # Generate PDF
        print("📄 Generating FREE PDF...")
        try:
            pdf_filename = f"transcript_free_{uuid.uuid4().hex[:8]}.pdf"
            pdf_path = os.path.join("/tmp", pdf_filename)
            
            # Create PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#5B21B6',
                spaceAfter=12
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=16,
                alignment=TA_LEFT
            )
            
            # Build PDF content
            story = []
            
            # Title
            story.append(Paragraph(f"<b>{video_title}</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            story.append(Paragraph(f"FREE Transcript - {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", metadata_style))
            story.append(Paragraph(f"Source: {youtube_url}", metadata_style))
            story.append(Paragraph(f"Language: {language}", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Transcript text - split into paragraphs
            paragraphs = transcript.split('. ')  # Split on sentences for better formatting
            current_para = ""
            for sentence in paragraphs:
                current_para += sentence + ". "
                # Create a new paragraph every ~500 characters
                if len(current_para) > 500:
                    story.append(Paragraph(current_para.strip(), body_style))
                    story.append(Spacer(1, 0.15*inch))
                    current_para = ""
            
            # Add any remaining text
            if current_para.strip():
                story.append(Paragraph(current_para.strip(), body_style))
            
            # Build PDF
            doc.build(story)
            print(f"✅ FREE PDF created: {pdf_path}")
            
            # Return the PDF as a download
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"{video_title[:50].replace('/', '-')}_FREE_transcript.pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{video_title[:50].replace('/', '-')}_FREE_transcript.pdf\""
                }
            )
            
        except Exception as e:
            return JSONResponse(status_code=500, content={
                "error": "Failed to create PDF from transcript."
            })
        
    except Exception as e:
        print(f"❌ FREE YouTube transcript error: {str(e)}")
        return JSONResponse(status_code=500, content={
            "error": "Something went wrong. Please try again or use the Whisper transcription."
        })


# === Text to PDF with Punctuation Fixing ===
@app.post("/text-to-pdf")
async def text_to_pdf(request: TextToPDFRequest):
    """Convert text to PDF with AI-powered punctuation and grammar fixes"""
    try:
        openai_client = get_openai_client()
        if not openai_client:
            return JSONResponse(
                status_code=500,
                content={"error": "OpenAI client not initialized"})
        
        print(f"📝 Processing text for PDF generation...")
        
        # Use GPT to fix punctuation and grammar
        print("🔧 Fixing punctuation and grammar with AI...")
        try:
            completion = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional editor optimizing text for semantic search and vector embeddings. Your tasks: 1) Fix all punctuation, grammar, and formatting errors. 2) Remove speech filler words (so, yeah, anyway, basically, um, you know, etc.) only when they add no meaning. Preserve 'like' when used for comparisons or analogies. 3) Remove only the redundant clauses of meta-commentary (e.g., 'we'll get into that later', 'as I mentioned before') while keeping the substantive content of those sentences. 4) Normalize conversational tone to clear, direct statements while preserving all conceptual content, examples, and technical terminology. 5) Add proper paragraph breaks at topic transitions. Return only the cleaned text with NO explanations or comments."
                    },
                    {
                        "role": "user",
                        "content": request.text
                    }
                ],
                temperature=0.3
            )
            
            content = completion.choices[0].message.content
            cleaned_text = content.strip() if content else request.text
            print("✅ Text cleaned and formatted")
            
        except Exception as e:
            print(f"⚠️ Punctuation fix failed: {str(e)}, using original text")
            cleaned_text = request.text
        
        # Generate PDF
        print("📄 Generating PDF...")
        try:
            pdf_filename = f"document_{uuid.uuid4().hex[:8]}.pdf"
            pdf_path = os.path.join("/tmp", pdf_filename)
            
            # Create PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#5B21B6',
                spaceAfter=12
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=16,
                alignment=TA_LEFT
            )
            
            # Build PDF content
            story = []
            
            # Title
            story.append(Paragraph(f"<b>{request.title}</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            story.append(Paragraph(f"Created on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Text content - split into paragraphs
            paragraphs = cleaned_text.split('\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
                    story.append(Spacer(1, 0.15*inch))
            
            # Build PDF
            doc.build(story)
            print(f"✅ PDF created: {pdf_path}")
            
            # Return the PDF as a download
            safe_filename = request.title[:50].replace('/', '-').replace('\\', '-')
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"{safe_filename}.pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{safe_filename}.pdf\""
                }
            )
            
        except Exception as e:
            print(f"❌ PDF generation error: {str(e)}")
            return JSONResponse(status_code=500, content={
                "error": "Failed to create PDF. Please try again with different text."
            })
        
    except Exception as e:
        print(f"❌ Text to PDF error: {str(e)}")
        return JSONResponse(status_code=500, content={
            "error": "Something went wrong. Please try again."
        })


# === Reprocess PDF (Extract text, enhance with GPT, return improved PDF) ===
@app.post("/reprocess-pdf")
async def reprocess_pdf(file: UploadFile = File(...)):
    """Upload an existing PDF, extract text, enhance with GPT cleanup, return improved PDF"""
    try:
        print(f"📄 Received PDF for reprocessing: {file.filename}")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"error": "Please upload a PDF file"}
            )
        
        # Read PDF content
        contents = await file.read()
        print(f"📦 File size: {len(contents) / 1024:.2f} KB")
        
        # Save temporarily
        temp_pdf_path = os.path.join(tempfile.gettempdir(), f"temp_{uuid.uuid4().hex[:8]}.pdf")
        with open(temp_pdf_path, 'wb') as f:
            f.write(contents)
        
        try:
            # Extract text from PDF
            print("📖 Extracting text from PDF...")
            pdf_text = ""
            pdf_reader = PdfReader(temp_pdf_path)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        pdf_text += page_text + "\n"
                except Exception as e:
                    print(f"⚠️ Could not extract text from page {page_num + 1}: {e}")
            
            if not pdf_text.strip():
                return JSONResponse(
                    status_code=400,
                    content={"error": "Could not extract text from PDF. The PDF might be image-based or encrypted."}
                )
            
            print(f"✅ Extracted {len(pdf_text)} characters from PDF")
            
            # Use enhanced GPT cleanup (same as Text to PDF)
            openai_client = get_openai_client()
            if not openai_client:
                return JSONResponse(
                    status_code=500,
                    content={"error": "OpenAI client not initialized"}
                )
            
            print("✨ Enhancing text with GPT-3.5 (removing filler, optimizing for embeddings)...")
            try:
                completion = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional editor optimizing text for semantic search and vector embeddings. Your tasks: 1) Fix all punctuation, grammar, and formatting errors. 2) Remove speech filler words (so, yeah, anyway, basically, um, you know, etc.) only when they add no meaning. Preserve 'like' when used for comparisons or analogies. 3) Remove only the redundant clauses of meta-commentary (e.g., 'we'll get into that later', 'as I mentioned before') while keeping the substantive content of those sentences. 4) Normalize conversational tone to clear, direct statements while preserving all conceptual content, examples, and technical terminology. 5) Add proper paragraph breaks at topic transitions. Return only the cleaned text with NO explanations or comments."
                        },
                        {
                            "role": "user",
                            "content": pdf_text
                        }
                    ],
                    temperature=0.3
                )
                
                cleaned_text = completion.choices[0].message.content.strip()
                print("✅ Text enhanced successfully")
                
            except Exception as e:
                print(f"⚠️ GPT enhancement failed: {e}, using original text")
                cleaned_text = pdf_text
            
            # Generate improved PDF
            print("📄 Creating improved PDF...")
            output_pdf_path = os.path.join(tempfile.gettempdir(), f"enhanced_{uuid.uuid4().hex[:8]}.pdf")
            
            doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#5B21B6',
                spaceAfter=12
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=16,
                alignment=TA_LEFT
            )
            
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            
            # Build PDF content
            story = []
            
            # Title (use original filename)
            original_title = file.filename.replace('.pdf', '').replace('_', ' ')
            story.append(Paragraph(f"<b>{original_title} (Enhanced)</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            story.append(Paragraph(f"Reprocessed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Content
            paragraphs = cleaned_text.split('\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
                    story.append(Spacer(1, 0.15*inch))
            
            # Build PDF
            doc.build(story)
            print(f"✅ Enhanced PDF created")
            
            # Return the improved PDF
            safe_filename = file.filename.replace('.pdf', '_enhanced.pdf').replace('/', '-').replace('\\', '-')
            return FileResponse(
                output_pdf_path,
                media_type="application/pdf",
                filename=safe_filename,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{safe_filename}\""
                }
            )
            
        finally:
            # Clean up temp file
            try:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
            except:
                pass
        
    except Exception as e:
        print(f"❌ PDF reprocessing error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to reprocess PDF: {str(e)}"}
        )


# === Upload Audio File (MP3/M4A/WAV) for Transcription ===
@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file, transcribe with Whisper, generate PDF, auto-tag, and index in Pinecone"""
    try:
        print(f"🎵 Received audio file: {file.filename}")
        
        # Validate file type
        allowed_extensions = ['.mp3', '.m4a', '.wav', '.m4v', '.mp4']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file type. Please upload MP3, M4A, WAV, or MP4 files."}
            )
        
        # Read file content
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        print(f"📦 File size: {file_size_mb:.2f} MB")
        
        # Check file size (Whisper has 25MB limit)
        if file_size_mb > 24:
            return JSONResponse(
                status_code=400,
                content={"error": f"File too large ({file_size_mb:.1f}MB). Maximum size is 24MB. Please compress the audio or split into smaller files."}
            )
        
        # Create temp directory for audio processing
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, file.filename)
        
        try:
            # Save uploaded file
            with open(audio_path, 'wb') as f:
                f.write(contents)
            print(f"✅ Audio file saved temporarily")
            
            # Transcribe with OpenAI Whisper
            print("🎤 Transcribing with Whisper...")
            openai_client = get_openai_client()
            if not openai_client:
                return JSONResponse(
                    status_code=500,
                    content={"error": "OpenAI client not initialized"})
            
            # Get audio duration for cost calculation
            audio = AudioSegment.from_file(audio_path)
            duration_minutes = len(audio) / (1000 * 60)  # Convert ms to minutes
            
            with open(audio_path, "rb") as audio_file:
                transcript_response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    timeout=900  # 15 minute timeout for Whisper
                )
            
            transcript = transcript_response if isinstance(transcript_response, str) else transcript_response.text
            
            # Log Whisper API usage
            whisper_cost = duration_minutes * PRICING["whisper-1"]
            log_api_usage("whisper", "whisper-1", input_tokens=0, output_tokens=0, cost=whisper_cost)
            print(f"✅ Transcription complete: {len(transcript)} characters")
            print(f"💰 Whisper cost: ${whisper_cost:.4f} ({duration_minutes:.2f} minutes)")
            
        finally:
            # Clean up temp audio file
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
        
        # Generate PDF from transcript
        print("📄 Generating PDF from transcript...")
        pdf_filename = f"transcript_{file.filename}".replace(file_ext, '.pdf')
        pdf_bytes = None
        
        try:
            pdf_path = os.path.join(tempfile.gettempdir(), f"temp_{uuid.uuid4().hex[:8]}.pdf")
            
            # Create PDF with ReportLab
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#5B21B6',
                spaceAfter=12
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=16,
                alignment=TA_LEFT
            )
            
            # Build PDF content
            story = []
            
            # Title
            title_text = file.filename.replace(file_ext, '')
            story.append(Paragraph(f"<b>{title_text}</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata (Hawaii timezone)
            hawaii_tz = pytz.timezone('Pacific/Honolulu')
            hawaii_time = datetime.now(hawaii_tz)
            
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            story.append(Paragraph(f"Transcribed on {hawaii_time.strftime('%B %d, %Y at %I:%M %p')} HST", metadata_style))
            story.append(Paragraph(f"Source: {file.filename} ({duration_minutes:.1f} minutes)", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Transcript text - split into paragraphs
            paragraphs = transcript.split('\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
                    story.append(Spacer(1, 0.15*inch))
            
            # Build PDF
            doc.build(story)
            
            # Read PDF as bytes
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # Clean up temp PDF
            os.remove(pdf_path)
            
            print(f"✅ PDF generated successfully")
            
        except Exception as e:
            print(f"❌ PDF generation error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to generate PDF from transcript"}
            )
        
        # Now process the PDF like a regular upload: extract text, chunk, embed, and index
        print("📚 Indexing transcript in Pinecone...")
        
        try:
            # Read PDF text
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
            chunks = chunk_text(text)
            
            doc_id = str(uuid.uuid4())
            pinecone_index = get_pinecone_client()
            
            if not pinecone_index:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Pinecone client not initialized"})
            
            # Auto-tag document with InnerVerse taxonomy
            tags = await auto_tag_document(text, pdf_filename, openai_client)
            
            # Batch embedding + upsert
            vectors_to_upsert = []
            for i, chunk in enumerate(chunks):
                if i % 50 == 0 and i > 0:
                    print(f"📊 Processing chunk {i}/{len(chunks)}...")
                
                response = openai_client.embeddings.create(
                    input=chunk, model="text-embedding-ada-002", timeout=120)
                vector = response.data[0].embedding
                vectors_to_upsert.append((f"{doc_id}-{i}", vector, {
                    "text": chunk,
                    "doc_id": doc_id,
                    "filename": pdf_filename,
                    "upload_timestamp": datetime.now().isoformat(),
                    "tags": tags,
                    "source": "audio_upload"
                }))
            
            # Upload in batches to Pinecone
            if vectors_to_upsert:
                batch_size = 50
                total_batches = (len(vectors_to_upsert) + batch_size - 1) // batch_size
                
                for batch_num in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[batch_num:batch_num + batch_size]
                    pinecone_index.upsert(vectors=batch)
                    current_batch = (batch_num // batch_size) + 1
                    print(f"📤 Uploaded batch {current_batch}/{total_batches} ({len(batch)} vectors)")
                
                print(f"✅ Successfully indexed {len(vectors_to_upsert)} chunks in Pinecone")
            
            return {
                "message": "Audio transcribed and indexed with InnerVerse Intelligence Layer",
                "document_id": doc_id,
                "filename": pdf_filename,
                "chunks_count": len(chunks),
                "tags": tags,
                "tags_count": len(tags),
                "duration_minutes": round(duration_minutes, 2),
                "whisper_cost": round(whisper_cost, 4)
            }
            
        except Exception as e:
            print(f"❌ Indexing error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Transcription succeeded but indexing failed: {str(e)}"}
            )
        
    except Exception as e:
        print(f"❌ Audio upload error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Audio upload failed: {str(e)}"}
        )


# === Download YouTube Video with Proxy ===
@app.post("/download-youtube")
async def download_youtube(request: YouTubeDownloadRequest):
    """Download YouTube audio using Decodo residential proxy, transcribe, auto-tag, and index"""
    try:
        youtube_url = request.youtube_url
        print(f"🎬 Processing YouTube URL with proxy: {youtube_url}")
        
        # Check if proxy credentials are set
        proxy_host = os.getenv("DECODO_PROXY_HOST")
        proxy_port = os.getenv("DECODO_PROXY_PORT")
        proxy_user = os.getenv("DECODO_PROXY_USER")
        proxy_pass = os.getenv("DECODO_PROXY_PASS")
        
        if not all([proxy_host, proxy_port, proxy_user, proxy_pass]):
            return JSONResponse(status_code=500, content={
                "error": "Proxy configuration not set. Please configure Decodo proxy credentials."
            })
        
        # Build proxy URL for SOCKS5 (URL-encode username and password to handle special characters)
        encoded_user = quote(proxy_user, safe='')
        encoded_password = quote(proxy_pass, safe='')
        socks5_port = "7000"
        proxy_url = f"socks5://{encoded_user}:{encoded_password}@{proxy_host}:{socks5_port}"
        print(f"🌐 Using Decodo residential proxy (SOCKS5): {proxy_host}:{socks5_port}")
        print(f"🔐 Username: {proxy_user} → Encoded: {encoded_user}")
        print(f"🔐 Password length: {len(proxy_pass)} → Encoded length: {len(encoded_password)}")
        
        # Create temp directory for audio files
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "youtube_audio.mp3")
        
        try:
            # Step 1: Get video metadata with proxy
            print("📋 Fetching video metadata...")
            info_command = [
                "yt-dlp",
                "--proxy", proxy_url,
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--referer", "https://www.youtube.com/",
                "--print", "%(title)s|||%(duration)s",
                youtube_url
            ]
            
            info_result = subprocess.run(info_command, capture_output=True, text=True, timeout=90)
            
            if info_result.returncode != 0:
                error_msg = info_result.stderr.lower()
                print(f"❌ yt-dlp metadata error: {info_result.stderr}")
                if "private video" in error_msg or "members-only" in error_msg:
                    return JSONResponse(status_code=403, content={
                        "error": "This video is private or members-only."
                    })
                elif "age-restricted" in error_msg:
                    return JSONResponse(status_code=403, content={
                        "error": "Age-restricted video. Cannot access with proxy."
                    })
                elif "video unavailable" in error_msg or "removed" in error_msg:
                    return JSONResponse(status_code=404, content={
                        "error": "Video unavailable or removed."
                    })
                elif "timed out" in error_msg or "timeout" in error_msg:
                    return JSONResponse(status_code=408, content={
                        "error": "Proxy connection timed out. Please try again."
                    })
                elif "407" in error_msg or "proxy authentication" in error_msg:
                    return JSONResponse(status_code=407, content={
                        "error": "Proxy authentication failed. Please check your credentials."
                    })
                else:
                    return JSONResponse(status_code=400, content={
                        "error": f"Unable to access video: {info_result.stderr[:200]}"
                    })
            
            info_parts = info_result.stdout.strip().split("|||")
            video_title = info_parts[0] if len(info_parts) > 0 else "YouTube Video"
            video_duration = int(info_parts[1]) if len(info_parts) > 1 and info_parts[1].isdigit() else 0
            
            print(f"📺 Video: {video_title} ({video_duration}s / {video_duration//60} min)")
            
            # Estimate download time (rough: 1 minute of video = ~1-2 seconds download with good connection)
            estimated_download_seconds = max(5, video_duration // 30)
            print(f"⏱️ Estimated download time: ~{estimated_download_seconds} seconds")
            
            # Step 2: Download audio with proxy
            print("📥 Downloading audio via Decodo proxy...")
            download_command = [
                "yt-dlp",
                "--proxy", proxy_url,
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--referer", "https://www.youtube.com/",
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--audio-quality", "0",  # Best quality
                "-o", audio_path,
                youtube_url
            ]
            
            # Extended timeout for long videos
            timeout_seconds = max(300, video_duration * 3)  # At least 5 minutes, or 3x video duration
            download_result = subprocess.run(download_command, capture_output=True, text=True, timeout=timeout_seconds)
            
            if download_result.returncode != 0:
                error_msg = download_result.stderr.lower()
                if "http error 403" in error_msg:
                    return JSONResponse(status_code=403, content={
                        "error": "Download blocked. The proxy may be detected by YouTube."
                    })
                elif "http error 429" in error_msg:
                    return JSONResponse(status_code=429, content={
                        "error": "Too many requests. Please wait a few minutes and try again."
                    })
                else:
                    return JSONResponse(status_code=500, content={
                        "error": "Download failed. Try again or try a different video."
                    })
            
            # Check if file was created
            if not os.path.exists(audio_path):
                return JSONResponse(status_code=500, content={
                    "error": "Audio extraction failed."
                })
            
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"✅ Downloaded: {file_size_mb:.2f} MB")
            
            # Check file size (Whisper has 25MB limit)
            if file_size_mb > 24:
                return JSONResponse(status_code=400, content={
                    "error": f"Audio file too large ({file_size_mb:.1f}MB). Whisper API has 24MB limit. Try a shorter video."
                })
            
            # Step 3: Transcribe with Whisper
            print("🎤 Transcribing with Whisper...")
            openai_client = get_openai_client()
            if not openai_client:
                return JSONResponse(status_code=500, content={
                    "error": "OpenAI client not initialized"
                })
            
            # Get audio duration for cost calculation
            audio = AudioSegment.from_file(audio_path)
            duration_minutes = len(audio) / (1000 * 60)
            
            with open(audio_path, "rb") as audio_file:
                transcript_response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    timeout=900
                )
            
            transcript = transcript_response if isinstance(transcript_response, str) else transcript_response.text
            
            # Log Whisper API usage
            whisper_cost = duration_minutes * PRICING["whisper-1"]
            log_api_usage("whisper_youtube", "whisper-1", input_tokens=0, output_tokens=0, cost=whisper_cost)
            print(f"✅ Transcription complete: {len(transcript)} characters")
            print(f"💰 Whisper cost: ${whisper_cost:.4f} ({duration_minutes:.2f} minutes)")
            
        finally:
            # Clean up temp audio file
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
        
        # Step 4: Generate PDF from transcript
        print("📄 Generating PDF from transcript...")
        pdf_filename = f"{video_title[:50].replace('/', '-')}.pdf"
        pdf_bytes = None
        
        try:
            pdf_path = os.path.join(tempfile.gettempdir(), f"temp_{uuid.uuid4().hex[:8]}.pdf")
            
            # Create PDF with ReportLab
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#5B21B6',
                spaceAfter=12
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=16,
                alignment=TA_LEFT
            )
            
            story = []
            story.append(Paragraph(f"<b>{video_title}</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            hawaii_tz = pytz.timezone('Pacific/Honolulu')
            hawaii_time = datetime.now(hawaii_tz)
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            story.append(Paragraph(f"Transcribed on {hawaii_time.strftime('%B %d, %Y at %I:%M %p')} HST", metadata_style))
            story.append(Paragraph(f"Source: {youtube_url}", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Transcript
            paragraphs = transcript.split('\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
                    story.append(Spacer(1, 0.15*inch))
            
            doc.build(story)
            
            # Read PDF as bytes
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            os.remove(pdf_path)
            print(f"✅ PDF generated successfully")
            
        except Exception as e:
            print(f"❌ PDF generation error: {str(e)}")
            return JSONResponse(status_code=500, content={
                "error": "Failed to generate PDF from transcript"
            })
        
        # Step 5: Index in Pinecone with auto-tagging
        print("📚 Indexing transcript in Pinecone...")
        
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
            chunks = chunk_text(text)
            
            doc_id = str(uuid.uuid4())
            pinecone_index = get_pinecone_client()
            
            if not pinecone_index:
                return JSONResponse(status_code=500, content={
                    "error": "Pinecone client not initialized"
                })
            
            # Auto-tag document
            tags = await auto_tag_document(text, pdf_filename, openai_client)
            
            # Batch embedding + upsert
            vectors_to_upsert = []
            for i, chunk in enumerate(chunks):
                if i % 50 == 0 and i > 0:
                    print(f"📊 Processing chunk {i}/{len(chunks)}...")
                
                response = openai_client.embeddings.create(
                    input=chunk, model="text-embedding-ada-002", timeout=120)
                vector = response.data[0].embedding
                vectors_to_upsert.append((f"{doc_id}-{i}", vector, {
                    "text": chunk,
                    "doc_id": doc_id,
                    "filename": pdf_filename,
                    "upload_timestamp": datetime.now().isoformat(),
                    "tags": tags,
                    "source": "youtube_url"
                }))
            
            # Upload in batches to Pinecone
            if vectors_to_upsert:
                batch_size = 50
                total_batches = (len(vectors_to_upsert) + batch_size - 1) // batch_size
                
                for batch_num in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[batch_num:batch_num + batch_size]
                    pinecone_index.upsert(vectors=batch)
                    current_batch = (batch_num // batch_size) + 1
                    print(f"📤 Uploaded batch {current_batch}/{total_batches} ({len(batch)} vectors)")
                
                print(f"✅ Successfully indexed {len(vectors_to_upsert)} chunks in Pinecone")
            
            return {
                "message": "YouTube video downloaded, transcribed, and indexed successfully",
                "document_id": doc_id,
                "filename": pdf_filename,
                "video_title": video_title,
                "chunks_count": len(chunks),
                "tags": tags,
                "tags_count": len(tags),
                "duration_minutes": round(duration_minutes, 2),
                "whisper_cost": round(whisper_cost, 4),
                "file_size_mb": round(file_size_mb, 2)
            }
            
        except Exception as e:
            print(f"❌ Indexing error: {str(e)}")
            return JSONResponse(status_code=500, content={
                "error": f"Download and transcription succeeded but indexing failed: {str(e)}"
            })
        
    except Exception as e:
        print(f"❌ YouTube download error: {str(e)}")
        return JSONResponse(status_code=500, content={
            "error": f"YouTube download failed: {str(e)}"
        })


# === Smart YouTube Transcript (Free + GPT Cleanup + Auto-Tag + Index) ===
@app.post("/transcript-youtube-smart")
async def transcript_youtube_smart(request: YouTubeTranscribeRequest):
    """Get FREE YouTube transcript, clean with GPT-3.5, auto-tag, and index to Pinecone"""
    try:
        youtube_url = request.youtube_url
        print(f"🎬 Smart transcription starting for: {youtube_url}")
        
        # Step 1: Extract video ID
        video_id = None
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)',
            r'youtube\.com/embed/([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            return JSONResponse(status_code=400, content={
                "error": "Invalid YouTube URL. Please check the URL and try again."
            })
        
        print(f"📺 Video ID: {video_id}")
        
        # Step 2: Fetch YouTube transcript (FREE)
        try:
            # Try to get transcript (tries multiple languages automatically)
            ytt_api = YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(video_id, languages=['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'ko', 'zh', 'ru', 'ar', 'hi'])
            
            # Combine all transcript segments
            raw_transcript = ' '.join([entry['text'] for entry in fetched_transcript])
            print(f"✅ Raw transcript retrieved ({len(raw_transcript)} characters)")
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"❌ Transcript error: {e}")
            
            if 'disabled' in error_str or 'no transcript' in error_str:
                return JSONResponse(status_code=404, content={
                    "error": "No captions available for this video. Captions must be enabled by the video creator."
                })
            elif 'private' in error_str or 'unavailable' in error_str:
                return JSONResponse(status_code=403, content={
                    "error": "Video is private or unavailable."
                })
            elif 'blocking' in error_str or 'ip has been blocked' in error_str or 'cloud provider' in error_str:
                return JSONResponse(status_code=403, content={
                    "error": "YouTube is blocking cloud server IPs. Manual workaround: (1) Click 'Show transcript' on the YouTube video, (2) Copy the text, (3) Use the 'Text to PDF' tab to convert it, (4) Upload the PDF to get auto-tagging and search indexing."
                })
            else:
                return JSONResponse(status_code=404, content={
                    "error": f"Could not get captions: {str(e)}"
                })
        
        # Step 3: Get video title
        video_title = "YouTube Video"
        try:
            info_command = ["yt-dlp", "--print", "%(title)s", youtube_url]
            info_result = subprocess.run(info_command, capture_output=True, text=True, timeout=10)
            if info_result.returncode == 0 and info_result.stdout.strip():
                video_title = info_result.stdout.strip()
                print(f"📺 Video title: {video_title}")
        except:
            pass
        
        # Step 4: Clean up transcript with GPT-3.5 (add punctuation, fix grammar)
        print("✨ Cleaning transcript with GPT-3.5 (adding punctuation & fixing grammar)...")
        openai_client = get_openai_client()
        
        if not openai_client:
            return JSONResponse(status_code=500, content={
                "error": "OpenAI client not initialized"
            })
        
        try:
            # Truncate if too long (GPT-3.5 has 16K context window)
            max_chars = 60000
            if len(raw_transcript) > max_chars:
                print(f"⚠️ Transcript too long ({len(raw_transcript)} chars), truncating to {max_chars}")
                raw_transcript = raw_transcript[:max_chars] + "...[truncated]"
            
            cleanup_prompt = f"""You are a professional transcript editor. Your task is to clean up this YouTube transcript by:
1. Adding proper punctuation (periods, commas, question marks, etc.)
2. Adding proper capitalization
3. Breaking into logical paragraphs
4. Fixing obvious transcription errors/typos
5. Making it readable and professional

Keep the content exactly as spoken - DO NOT summarize or change the meaning. Just fix formatting and readability.

Raw transcript:
{raw_transcript}

Return ONLY the cleaned transcript with proper formatting, nothing else."""
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional transcript editor who adds punctuation and fixes formatting without changing content."},
                    {"role": "user", "content": cleanup_prompt}
                ],
                temperature=0.3,
                max_tokens=16000
            )
            
            cleaned_transcript = response.choices[0].message.content.strip()
            
            # Log GPT usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            gpt_cost = (input_tokens * PRICING["gpt-3.5-turbo-input"] / 1000) + (output_tokens * PRICING["gpt-3.5-turbo-output"] / 1000)
            log_api_usage("transcript_cleanup", "gpt-3.5-turbo", input_tokens, output_tokens, gpt_cost)
            
            print(f"✅ Transcript cleaned ({len(cleaned_transcript)} characters)")
            print(f"💰 GPT cleanup cost: ${gpt_cost:.4f}")
            
        except Exception as e:
            print(f"❌ GPT cleanup error: {str(e)}")
            # Fallback to raw transcript if GPT fails
            cleaned_transcript = raw_transcript
        
        # Step 5: Generate PDF
        print("📄 Generating PDF...")
        pdf_filename = f"{video_title[:50].replace('/', '-')}.pdf"
        pdf_bytes = None
        
        try:
            pdf_path = os.path.join(tempfile.gettempdir(), f"temp_{uuid.uuid4().hex[:8]}.pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#5B21B6',
                spaceAfter=12
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=16,
                alignment=TA_LEFT
            )
            
            story = []
            story.append(Paragraph(f"<b>{video_title}</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            hawaii_tz = pytz.timezone('Pacific/Honolulu')
            hawaii_time = datetime.now(hawaii_tz)
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            story.append(Paragraph(f"Transcribed on {hawaii_time.strftime('%B %d, %Y at %I:%M %p')} HST", metadata_style))
            story.append(Paragraph(f"Source: {youtube_url}", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Transcript paragraphs
            paragraphs = cleaned_transcript.split('\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
                    story.append(Spacer(1, 0.15*inch))
            
            doc.build(story)
            
            # Read PDF as bytes
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            os.remove(pdf_path)
            print(f"✅ PDF generated successfully")
            
        except Exception as e:
            print(f"❌ PDF generation error: {str(e)}")
            return JSONResponse(status_code=500, content={
                "error": "Failed to generate PDF from transcript"
            })
        
        # Step 6: Auto-tag with MBTI taxonomy
        print("🏷️ Auto-tagging with MBTI taxonomy...")
        tags = await auto_tag_document(cleaned_transcript, pdf_filename, openai_client)
        print(f"✅ Auto-tagged with {len(tags)} tags: {tags[:5]}...")
        
        # Step 7: Index in Pinecone
        print("📚 Indexing in Pinecone...")
        
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
            chunks = chunk_text(text)
            
            doc_id = str(uuid.uuid4())
            pinecone_index = get_pinecone_client()
            
            if not pinecone_index:
                return JSONResponse(status_code=500, content={
                    "error": "Pinecone client not initialized"
                })
            
            # Create embeddings and vectors
            vectors_to_upsert = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = get_embedding_with_logging(chunk)
                    vector_id = f"{doc_id}_{i}"
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": embedding,
                        "metadata": {
                            "document_id": doc_id,
                            "filename": pdf_filename,
                            "chunk_index": i,
                            "text": chunk[:1000],
                            "tags": tags,
                            "source": "youtube_transcript",
                            "video_url": youtube_url
                        }
                    })
                except Exception as e:
                    print(f"⚠️ Skipping chunk {i} due to error: {e}")
            
            # Batch upsert to Pinecone
            if vectors_to_upsert:
                batch_size = 50
                total_batches = (len(vectors_to_upsert) + batch_size - 1) // batch_size
                
                for batch_num in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[batch_num:batch_num + batch_size]
                    pinecone_index.upsert(vectors=batch)
                    current_batch = (batch_num // batch_size) + 1
                    print(f"📤 Uploaded batch {current_batch}/{total_batches} ({len(batch)} vectors)")
                
                print(f"✅ Successfully indexed {len(vectors_to_upsert)} chunks in Pinecone")
            
            return {
                "message": "YouTube transcript fetched, cleaned, tagged, and indexed successfully!",
                "document_id": doc_id,
                "filename": pdf_filename,
                "video_title": video_title,
                "chunks_count": len(chunks),
                "tags": tags,
                "tags_count": len(tags),
                "transcript_length": len(cleaned_transcript),
                "cleanup_cost": round(gpt_cost, 4),
                "total_cost": round(gpt_cost, 4),
                "note": "FREE transcript + GPT cleanup (~$0.001-0.002 per video) - 44x cheaper than Whisper!"
            }
            
        except Exception as e:
            print(f"❌ Indexing error: {str(e)}")
            return JSONResponse(status_code=500, content={
                "error": f"Transcript cleaned but indexing failed: {str(e)}"
            })
        
    except Exception as e:
        print(f"❌ Smart transcript error: {str(e)}")
        return JSONResponse(status_code=500, content={
            "error": f"Smart transcription failed: {str(e)}"
        })


# === API Usage Endpoint ===
@app.get("/api/usage")
async def get_usage_stats():
    """Return API usage statistics for cost tracker"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                "total_cost": 0.0,
                "last_24h_cost": 0.0,
                "by_operation": {},
                "recent_calls": []
            }
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total cost
        cursor.execute("SELECT COALESCE(SUM(cost), 0) as total_cost FROM api_usage")
        result = cursor.fetchone()
        total_cost = float(result["total_cost"]) if result else 0.0
        
        # Get last 24h cost (convert to Hawaii timezone for display)
        cursor.execute("""
            SELECT COALESCE(SUM(cost), 0) as last_24h_cost 
            FROM api_usage 
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
        """)
        result = cursor.fetchone()
        last_24h_cost = float(result["last_24h_cost"]) if result else 0.0
        
        # Group by operation
        cursor.execute("""
            SELECT operation, 
                   COALESCE(SUM(cost), 0) as cost, 
                   COUNT(*) as count
            FROM api_usage
            GROUP BY operation
        """)
        by_operation = {}
        for row in cursor.fetchall():
            by_operation[row["operation"]] = {
                "cost": float(row["cost"]),
                "count": row["count"]
            }
        
        # Get recent 10 calls (convert to Hawaii timezone)
        cursor.execute("""
            SELECT operation, 
                   cost, 
                   timestamp
            FROM api_usage
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        recent_calls = []
        hawaii_tz = pytz.timezone('Pacific/Honolulu')
        for row in cursor.fetchall():
            # Convert UTC timestamp to Hawaii timezone
            utc_time = row["timestamp"]
            if utc_time.tzinfo is None:
                utc_time = pytz.utc.localize(utc_time)
            hawaii_time = utc_time.astimezone(hawaii_tz)
            
            recent_calls.append({
                "operation": row["operation"],
                "cost": float(row["cost"]),
                "timestamp": hawaii_time.isoformat()
            })
        
        cursor.close()
        conn.close()
        
        return {
            "total_cost": round(total_cost, 6),
            "last_24h_cost": round(last_24h_cost, 6),
            "by_operation": by_operation,
            "recent_calls": recent_calls
        }
    except Exception as e:
        print(f"❌ Error calculating usage stats: {str(e)}")
        return {
            "total_cost": 0.0,
            "last_24h_cost": 0.0,
            "by_operation": {},
            "recent_calls": []
        }


# === Serve Frontend ===
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/health", include_in_schema=False)
def health_check():
    """Health check endpoint for deployments"""
    return {"status": "healthy", "app": "InnerVerse"}

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/privacy", include_in_schema=False)
def serve_privacy():
    return FileResponse("privacy.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="."), name="static")


# === Run the app ===
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Starting server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
