import os
import uuid
import io
import base64
import json
import httpx
import csv
import tempfile
import subprocess
import secrets
from datetime import datetime, timezone, timedelta
from collections import deque
from contextlib import asynccontextmanager
from urllib.parse import quote
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, Request, Response, Header, HTTPException, BackgroundTasks, Cookie, Depends
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
import anthropic
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
import threading
import asyncio
import traceback

# Knowledge Graph imports
from src.services.concept_extractor import extract_concepts
from src.services.knowledge_graph_manager import KnowledgeGraphManager

# Background Job Service
from src.services.background_job_service import BackgroundJobService

# Lesson Content Generator
from src.services.lesson_content_generator import LessonContentGenerator

# Reference Data Validator
from src.services.reference_validator import VALIDATOR

# Learning Paths UI Router
from src.routes.learning_paths_routes import router as learning_paths_ui_router

# Chat Router
from src.routes.chat_routes import router as chat_router

# Query Intelligence (2025-11-20)
from src.services.query_intelligence import analyze_and_filter, rerank_results, QueryConfig

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
DATABASE_URL = os.getenv("DATABASE_URL")

# === Startup Logging ===
print("🚀 Starting InnerVerse...")
print(f"✅ OPENAI_API_KEY: {'SET' if OPENAI_API_KEY else 'MISSING'}")
print(f"✅ ANTHROPIC_API_KEY: {'SET' if ANTHROPIC_API_KEY else 'MISSING'}")
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

# Pricing per 1K tokens (as of Nov 2025)
PRICING = {
    "text-embedding-ada-002": 0.0001,  # per 1K tokens (legacy)
    "text-embedding-3-large": 0.00013,  # per 1K tokens (improved semantic matching)
    "gpt-3.5-turbo-input": 0.0005,     # per 1K tokens
    "gpt-3.5-turbo-output": 0.0015,    # per 1K tokens
    "gpt-4o-mini-input": 0.00015,      # per 1K tokens (better structured output, cheaper than 3.5!)
    "gpt-4o-mini-output": 0.0006,      # per 1K tokens
    "whisper-1": 0.006,                # per minute of audio
    "claude-sonnet-4-input": 0.003,    # per 1K tokens
    "claude-sonnet-4-output": 0.015,   # per 1K tokens
}

# === Database Functions ===
def get_db_connection():
    """Get PostgreSQL database connection"""
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set - cost tracking will not work")
        return None
    return psycopg2.connect(DATABASE_URL)

def get_db():
    """Alias for get_db_connection() - used by curriculum routes"""
    return get_db_connection()

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
            
            # Create lesson_concepts table for Phase 6
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lesson_concepts (
                    id SERIAL PRIMARY KEY,
                    lesson_id VARCHAR(255) NOT NULL,
                    concept_id VARCHAR(255) NOT NULL,
                    confidence VARCHAR(10) CHECK(confidence IN ('high', 'medium', 'low')) NOT NULL,
                    similarity_score REAL NOT NULL,
                    metadata_overlap_score REAL NOT NULL,
                    assignment_rank INTEGER NOT NULL,
                    assigned_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(lesson_id, concept_id)
                )
            """)
            
            # Create indexes for lesson_concepts
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lesson_concepts_lesson 
                ON lesson_concepts(lesson_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lesson_concepts_confidence 
                ON lesson_concepts(confidence)
            """)
            
            # === Phase 7: YouTube Integration Tables ===
            
            # Create doc_type enum if not exists
            cursor.execute("""
                DO $$ BEGIN
                    CREATE TYPE doc_type AS ENUM ('youtube', 'pdf', 'transcript', 'audio');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
            
            # Create pending_status enum if not exists
            cursor.execute("""
                DO $$ BEGIN
                    CREATE TYPE pending_status AS ENUM ('unmatched', 'pending_review', 'linked', 'rejected');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
            
            # Create documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    doc_type doc_type NOT NULL,
                    source_url TEXT,
                    provider_video_id VARCHAR(100),
                    title VARCHAR(500) NOT NULL,
                    season VARCHAR(50),
                    episode VARCHAR(50),
                    duration_seconds INTEGER,
                    transcript_text TEXT,
                    transcript_status VARCHAR(50) DEFAULT 'pending',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(provider_video_id)
                )
            """)
            
            # Create indexes for documents table
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_type 
                ON documents(doc_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_provider_video_id 
                ON documents(provider_video_id) WHERE provider_video_id IS NOT NULL
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_season 
                ON documents(season) WHERE season IS NOT NULL
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_metadata 
                ON documents USING GIN(metadata)
            """)
            
            # Create lesson_documents join table
            # ⚠️ DISABLED FOR PHASE 7.1: References old "lessons" table which was replaced by "curriculum" table
            # cursor.execute("""
            #     CREATE TABLE IF NOT EXISTS lesson_documents (
            #         id SERIAL PRIMARY KEY,
            #         lesson_id VARCHAR(36) NOT NULL,
            #         document_id UUID NOT NULL,
            #         relationship_type VARCHAR(50) DEFAULT 'primary_resource',
            #         display_order INTEGER DEFAULT 0,
            #         created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            #         UNIQUE(lesson_id, document_id),
            #         FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
            #         FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            #     )
            # """)
            
            # # Create indexes for lesson_documents
            # cursor.execute("""
            #     CREATE INDEX IF NOT EXISTS idx_lesson_documents_lesson 
            #     ON lesson_documents(lesson_id)
            # """)
            
            # cursor.execute("""
            #     CREATE INDEX IF NOT EXISTS idx_lesson_documents_document 
            #     ON lesson_documents(document_id)
            # """)
            
            # cursor.execute("""
            #     CREATE INDEX IF NOT EXISTS idx_lesson_documents_order 
            #     ON lesson_documents(lesson_id, display_order)
            # """)
            
            # Create pending_youtube_videos table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_youtube_videos (
                    id SERIAL PRIMARY KEY,
                    provider_video_id VARCHAR(100) NOT NULL,
                    source_url TEXT NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    season VARCHAR(50),
                    category VARCHAR(100),
                    duration_seconds INTEGER,
                    raw_metadata JSONB DEFAULT '{}',
                    status pending_status DEFAULT 'unmatched',
                    confidence_score REAL DEFAULT 0.0,
                    matched_lesson_id VARCHAR(36),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(provider_video_id)
                )
            """)
            
            # Create indexes for pending_youtube_videos
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_videos_status 
                ON pending_youtube_videos(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_videos_season 
                ON pending_youtube_videos(season) WHERE season IS NOT NULL
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_videos_confidence 
                ON pending_youtube_videos(confidence_score DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_videos_provider_id 
                ON pending_youtube_videos(provider_video_id)
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Database initialized successfully (with YouTube integration tables)")
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


# === CSRF Protection ===
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic_settings import BaseSettings


# Generate or load CSRF secret key
_CSRF_SECRET = os.getenv("CSRF_SECRET_KEY")
if not _CSRF_SECRET:
    print("⚠️  WARNING: CSRF_SECRET_KEY not set - generating random key (not suitable for production!)")
    print("⚠️  Set CSRF_SECRET_KEY environment variable for production deployments")
    _CSRF_SECRET = secrets.token_urlsafe(32)


class CsrfSettings(BaseSettings):
    secret_key: str = _CSRF_SECRET
    cookie_samesite: str = "lax"
    cookie_secure: bool = os.getenv("PRODUCTION", "false").lower() == "true"
    cookie_httponly: bool = True  # HttpOnly protects cookie; token delivered separately via meta tag


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()


# Initialize clients
def get_openai_client():
    openai.api_key = OPENAI_API_KEY
    return openai


def get_pinecone_client():
    if not PINECONE_API_KEY or not PINECONE_INDEX:
        return None
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)


# Split PDF text into chunks with improved parameters for CS Joseph transcripts
def chunk_text(text, chunk_size=2500, chunk_overlap=500):
    """
    Improved chunking for conversational lecture transcripts:
    - 2500 chars allows complete thoughts/concepts (was 1000)
    - 500 char overlap (20%) prevents concept fragmentation (was 200)
    - Paragraph-aware splitting preserves natural boundaries
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],  # Prefer paragraph boundaries
        length_function=len
    )
    chunks = splitter.split_text(text)
    return chunks


def extract_enriched_metadata(filename: str, text_sample: str = "") -> dict:
    """
    Extract enriched metadata from filename and content for better filtering.
    Examples: 
    - "Season 12 Episode 45.pdf" -> {"season": "12", "episode": "45"}
    - "ESTP vs INTJ.pdf" -> {"types_mentioned": ["ESTP", "INTJ"]}
    """
    import re
    metadata = {}
    
    # Extract season/episode from filename
    season_match = re.search(r'[Ss]eason\s*(\d+)', filename)
    episode_match = re.search(r'[Ee]pisode\s*(\d+)', filename)
    
    if season_match:
        metadata["season"] = season_match.group(1)
    if episode_match:
        metadata["episode"] = episode_match.group(1)
    
    # Extract MBTI types mentioned in filename or text
    mbti_types = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP',
                  'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']
    
    types_found = []
    text_to_search = (filename + " " + text_sample[:500]).upper()
    for mbti_type in mbti_types:
        if mbti_type in text_to_search:
            types_found.append(mbti_type)
    
    if types_found:
        metadata["types_mentioned"] = ",".join(list(set(types_found)))[:50]  # Limit length
    
    # Extract cognitive functions mentioned
    functions = ['Fe', 'Fi', 'Te', 'Ti', 'Ne', 'Ni', 'Se', 'Si']
    functions_found = []
    for func in functions:
        if re.search(r'\b' + func + r'\b', text_to_search):
            functions_found.append(func)
    
    if functions_found:
        metadata["functions_mentioned"] = ",".join(list(set(functions_found)))[:30]
    
    return metadata


# Load InnerVerse taxonomy schema
def load_innerverse_schema():
    """Load the MBTI/Jungian taxonomy schema for auto-tagging"""
    try:
        with open('innerverse_schema.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ innerverse_schema.json not found - auto-tagging disabled")
        return None


# Auto-tag document using GPT-4o-mini for structured metadata extraction
async def auto_tag_document(text, filename, openai_client):
    """
    Analyze document content and extract structured MBTI/Jungian metadata using GPT-4o-mini.
    Uses authoritative reference data for validation and accuracy.
    Returns a validated, structured metadata dictionary for CS Joseph's teaching system.
    """
    # Sample first 3000 chars for analysis (balance cost vs accuracy)
    sample_text = text[:3000] if len(text) > 3000 else text
    
    # Get reference data summary for prompt injection
    reference_summary = {}
    if VALIDATOR:
        reference_summary = VALIDATOR.get_reference_summary()
    
    # Build enhanced prompt with reference data
    prompt = f"""You are an expert in CS Joseph's MBTI/Jungian Analytical Psychology system. Analyze this transcript and extract structured metadata.

TRANSCRIPT TITLE: {filename}
TRANSCRIPT TEXT (first 3000 chars): {sample_text}

AUTHORITATIVE REFERENCE DATA - USE ONLY THESE VALUES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Valid MBTI Types (ONLY these 16): {', '.join(reference_summary.get('valid_types', []))}
Valid Cognitive Functions (ONLY these 8): {', '.join(reference_summary.get('valid_function_codes', []))}
Valid Quadras (ONLY these 4): {', '.join(reference_summary.get('valid_quadras', []))}
Valid Temperaments: {', '.join(reference_summary.get('valid_temperaments', []))}
Valid Interaction Styles: {', '.join(reference_summary.get('valid_interaction_styles', []))}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extract the following metadata and return as valid JSON:

{{
  "content_type": "main_season | csj_responds | special | cutting_edge | celebrity_typing",
  "difficulty": "foundation | intermediate | advanced | expert",
  "primary_category": "cognitive_functions | type_profiles | relationships | personal_development | typing_methodology | four_sides | octagram | compatibility | celebrity_example",
  "types_discussed": ["INTJ", "ENFP"],
  "functions_covered": ["Ni", "Te", "Fi", "Se"],
  "relationship_type": "golden_pair | pedagogue_pair | bronze_pair | dyad_pair | none",
  "quadra": "Alpha | Beta | Gamma | Delta | none",
  "temple": "soul | heart | mind | body | multi | none",
  "topics": ["se_demon", "trust_issues", "octagram_variants"],
  "use_case": ["self_improvement", "relationship_help", "typing_others", "understanding_theory"]
}}

CRITICAL VALIDATION RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ONLY use types from the valid list above (case-insensitive ok, will be normalized)
✅ ONLY use function codes from the valid list (Ni, Ne, Ti, Te, Fi, Fe, Si, Se)
✅ ONLY use quadras from the valid list (Alpha, Beta, Gamma, Delta)
✅ DO NOT invent or hallucinate types (e.g., no INXX, XNFP, or invalid codes)
✅ DO NOT use 16personalities suffixes (INFJ-A, ENFP-T will be auto-corrected)
✅ Use "none" for fields that don't apply
✅ Use empty arrays [] for list fields with no data
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ADDITIONAL RULES:
- Return ONLY valid JSON, no extra text
- Be specific but concise
- Max 5 topics
- Infer content_type from filename patterns (Season X = main_season, CSJ Responds = csj_responds, etc.)
- When uncertain about a type or function, use "none" or [] rather than guessing

Your response (valid JSON only):"""

    try:
        print(f"🏷️ Auto-tagging document with structured metadata: {filename}")
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in CS Joseph's MBTI/Jungian system. Extract structured metadata from transcripts as valid JSON. ONLY use values from the authoritative reference data provided."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        # Track usage (calculate cost from input + output tokens)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens / 1000) * PRICING["gpt-4o-mini-input"] + \
               (output_tokens / 1000) * PRICING["gpt-4o-mini-output"]
        log_api_usage("auto_tagging", "gpt-4o-mini", 
                      input_tokens=input_tokens, 
                      output_tokens=output_tokens, 
                      cost=cost)
        
        # Parse structured metadata from response
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        raw_metadata = json.loads(response_text)
        
        # VALIDATION LAYER: Validate extracted metadata against reference data
        if VALIDATOR:
            validated_metadata, validation_report = VALIDATOR.validate_structured_metadata(raw_metadata)
            
            # Log validation results
            print(f"✅ Validated structured metadata:")
            print(f"   📁 Content Type: {validated_metadata.get('content_type', 'unknown')}")
            print(f"   📊 Difficulty: {validated_metadata.get('difficulty', 'unknown')}")
            print(f"   🎯 Category: {validated_metadata.get('primary_category', 'unknown')}")
            print(f"   👥 Types: {validated_metadata.get('types_discussed', [])} (validated)")
            print(f"   🧠 Functions: {validated_metadata.get('functions_covered', [])} (validated)")
            print(f"   🔗 Topics: {validated_metadata.get('topics', [])[:3]}...")
            
            # Log any validation issues
            has_issues = False
            for field, report in validation_report.items():
                if isinstance(report, dict):
                    for item, msg in report.items():
                        if "❌" in msg:
                            if not has_issues:
                                print(f"   ⚠️ Validation corrections:")
                                has_issues = True
                            print(f"      - {field}/{item}: {msg}")
                elif isinstance(report, str) and "❌" in report:
                    if not has_issues:
                        print(f"   ⚠️ Validation corrections:")
                        has_issues = True
                    print(f"      - {field}: {report}")
            
            return validated_metadata
        else:
            # Fallback if validator not available
            print(f"⚠️ Validator not available - using unvalidated metadata")
            print(f"✅ Extracted structured metadata:")
            print(f"   📁 Content Type: {raw_metadata.get('content_type', 'unknown')}")
            print(f"   📊 Difficulty: {raw_metadata.get('difficulty', 'unknown')}")
            print(f"   🎯 Category: {raw_metadata.get('primary_category', 'unknown')}")
            print(f"   👥 Types: {raw_metadata.get('types_discussed', [])}")
            print(f"   🧠 Functions: {raw_metadata.get('functions_covered', [])}")
            print(f"   🔗 Topics: {raw_metadata.get('topics', [])[:3]}...")
            
            return raw_metadata
        
    except Exception as e:
        print(f"⚠️ Auto-tagging failed: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty structured metadata on failure
        return {
            "content_type": "none",
            "difficulty": "none",
            "primary_category": "none",
            "types_discussed": [],
            "functions_covered": [],
            "relationship_type": "none",
            "quadra": "none",
            "temple": "none",
            "topics": [],
            "use_case": []
        }




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

# Configure Jinja2 templates with auto-reload (disable caching for development)
templates = Jinja2Templates(directory="static")
templates.env.auto_reload = True  # Disable template caching
templates.env.cache = None  # Force no caching

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSRF exception handler
@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=403,
        content={"error": "CSRF token validation failed"}
    )

# Register Learning Paths UI Router
app.include_router(learning_paths_ui_router)
app.include_router(chat_router)

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

        # Auto-tag document with structured metadata (GPT-4o-mini)
        structured_metadata = await auto_tag_document(text, data.filename, openai_client)
        
        # Extract enriched metadata
        enriched_meta = extract_enriched_metadata(data.filename, text[:2000])

        # Batch embedding + upsert with improved embeddings
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            # Show progress for large documents
            if i % 50 == 0 and i > 0:
                print(f"📊 Processing chunk {i}/{len(chunks)}...")
            
            response = openai_client.embeddings.create(
                input=chunk, model="text-embedding-3-large", timeout=60)
            vector = response.data[0].embedding
            
            # Build comprehensive metadata with structured fields
            chunk_metadata = {
                "text": chunk,
                "doc_id": doc_id,
                "filename": data.filename,
                "upload_timestamp": datetime.now().isoformat(),
                "chunk_index": i,
                # Structured metadata from GPT-4o-mini
                "content_type": structured_metadata.get("content_type", "none"),
                "difficulty": structured_metadata.get("difficulty", "none"),
                "primary_category": structured_metadata.get("primary_category", "none"),
                "types_discussed": structured_metadata.get("types_discussed", []),
                "functions_covered": structured_metadata.get("functions_covered", []),
                "relationship_type": structured_metadata.get("relationship_type", "none"),
                "quadra": structured_metadata.get("quadra", "none"),
                "temple": structured_metadata.get("temple", "none"),
                "topics": structured_metadata.get("topics", []),
                "use_case": structured_metadata.get("use_case", [])
            }
            # Add enriched metadata (season/episode parsed from filename)
            chunk_metadata.update(enriched_meta)
            
            vectors_to_upsert.append((f"{doc_id}-{i}", vector, chunk_metadata))

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
            "message": "PDF uploaded and indexed with structured metadata",
            "document_id": doc_id,
            "chunks_count": len(chunks),
            "structured_metadata": structured_metadata
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

        # Auto-tag document with structured metadata (GPT-4o-mini)
        structured_metadata = await auto_tag_document(text, file.filename, openai_client)
        
        # Extract enriched metadata
        enriched_meta = extract_enriched_metadata(file.filename, text[:2000])

        # Batch embedding + upsert with improved embeddings
        vectors_to_upsert = []
        embed_start = datetime.now()
        
        for i, chunk in enumerate(chunks):
            # Show progress for large documents
            if i % 50 == 0:
                elapsed = (datetime.now() - embed_start).total_seconds()
                print(f"📊 Processing chunk {i}/{len(chunks)} (elapsed: {elapsed:.1f}s)...")
            
            try:
                response = openai_client.embeddings.create(
                    input=chunk, model="text-embedding-3-large", timeout=120)  # Upgraded model
                vector = response.data[0].embedding
                
                # Build comprehensive metadata with structured fields
                chunk_metadata = {
                    "text": chunk,
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "upload_timestamp": datetime.now().isoformat(),
                    "chunk_index": i,
                    # Structured metadata from GPT-4o-mini
                    "content_type": structured_metadata.get("content_type", "none"),
                    "difficulty": structured_metadata.get("difficulty", "none"),
                    "primary_category": structured_metadata.get("primary_category", "none"),
                    "types_discussed": structured_metadata.get("types_discussed", []),
                    "functions_covered": structured_metadata.get("functions_covered", []),
                    "relationship_type": structured_metadata.get("relationship_type", "none"),
                    "quadra": structured_metadata.get("quadra", "none"),
                    "temple": structured_metadata.get("temple", "none"),
                    "topics": structured_metadata.get("topics", []),
                    "use_case": structured_metadata.get("use_case", [])
                }
                # Add enriched metadata (season/episode parsed from filename)
                chunk_metadata.update(enriched_meta)
                
                vectors_to_upsert.append((f"{doc_id}-{i}", vector, chunk_metadata))
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

        # Knowledge Graph Integration: Extract concepts after successful upload
        # This runs synchronously but doesn't block the response
        try:
            print(f"🔍 Extracting concepts for: {file.filename}")
            kg_start = datetime.now()
            
            # Check if document was already processed to avoid duplicates
            manager = KnowledgeGraphManager()
            graph = manager.load_graph()
            processed_docs = graph.get('metadata', {}).get('processed_documents', [])
            
            if doc_id not in processed_docs:
                # Extract concepts from document text
                extracted = await extract_concepts(
                    document_text=text,
                    document_id=doc_id
                )
                
                if extracted and extracted.get('concepts'):
                    concepts_added = 0
                    relationships_added = 0
                    
                    print(f"📊 Extracted {len(extracted.get('concepts', []))} concepts, {len(extracted.get('relationships', []))} relationships")
                    
                    # Add concepts to graph
                    print(f"📝 Adding concepts to graph...")
                    for concept in extracted.get('concepts', []):
                        node_data = {
                            'label': concept['label'],
                            'type': concept['type'],
                            'category': concept['category'],
                            'definition': concept.get('definition', ''),
                            'source_documents': [doc_id]
                        }
                        node = await manager.add_node(node_data)
                        if node:
                            concepts_added += 1
                    
                    # Add relationships to graph
                    print(f"🔗 Adding relationships to graph...")
                    for rel in extracted.get('relationships', []):
                        # Find source and target nodes (MUST use await for async functions)
                        source_node = await manager.find_node_by_label(rel['from'])
                        target_node = await manager.find_node_by_label(rel['to'])
                        
                        if source_node and target_node:
                            edge_data = {
                                'source': source_node['id'],
                                'target': target_node['id'],
                                'relationship_type': rel['type'],
                                'evidence_samples': [rel.get('evidence', '')],
                                'source_documents': [doc_id]
                            }
                            edge = await manager.add_edge(edge_data)
                            if edge:
                                relationships_added += 1
                        else:
                            print(f"⚠️ Skipping relationship: {rel['from']} -> {rel['to']} (node not found)")
                    
                    # Mark document as processed
                    if 'processed_documents' not in graph['metadata']:
                        graph['metadata']['processed_documents'] = []
                    graph['metadata']['processed_documents'].append(doc_id)
                    manager.save_graph(graph)
                    
                    kg_elapsed = (datetime.now() - kg_start).total_seconds()
                    print(f"✅ Knowledge graph updated: +{concepts_added} concepts, +{relationships_added} relationships")
                    print(f"⏱️ Concept extraction time: {kg_elapsed:.1f}s")
                else:
                    print(f"⚠️ Concept extraction returned no results for {doc_id}")
            else:
                print(f"ℹ️ Document {doc_id} already processed - skipping concept extraction")
                
        except Exception as kg_error:
            # Log but don't fail the upload
            error_traceback = traceback.format_exc()
            error_msg = f"Knowledge graph update failed: {str(kg_error)}\n{error_traceback}"
            print(f"❌ {error_msg}")
            
            # Log to file for debugging
            try:
                error_log_path = "data/kg-update-errors.json"
                os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
                
                error_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "document_id": doc_id,
                    "filename": file.filename,
                    "error": str(kg_error),
                    "traceback": error_traceback
                }
                
                # Append to error log
                errors = []
                if os.path.exists(error_log_path):
                    with open(error_log_path, 'r') as f:
                        errors = json.load(f)
                errors.append(error_entry)
                
                with open(error_log_path, 'w') as f:
                    json.dump(errors, f, indent=2)
                    
                print(f"📝 Error logged to {error_log_path}")
            except Exception as log_error:
                print(f"⚠️ Could not log KG error: {str(log_error)}")

        return {
            "message": "PDF uploaded and indexed with structured metadata",
            "document_id": doc_id,
            "chunks_count": len(chunks),
            "filename": file.filename,
            "structured_metadata": structured_metadata
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
        # Use 3072 dimensions for text-embedding-3-large
        dummy_vector = [0.0] * 3072
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
        dummy_vector = [0.0] * 3072  # text-embedding-3-large has 3072 dimensions
        
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
        dummy_vector = [0.0] * 3072  # text-embedding-3-large has 3072 dimensions
        
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


# === Get Full Structured Metadata for a Document ===
@app.get("/api/documents/{doc_id}/metadata")
async def get_document_metadata(doc_id: str):
    """Get full structured metadata for a specific document from Pinecone"""
    try:
        pinecone_index = get_pinecone_client()
        
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"})
        
        # Query Pinecone to get all chunks for this document
        dummy_vector = [0.0] * 3072
        
        query_response = pinecone_index.query(
            vector=dummy_vector,
            top_k=10000,
            include_metadata=True,
            filter={"doc_id": doc_id}
        )
        
        # Aggregate metadata across all chunks
        aggregated_metadata = {
            "doc_id": doc_id,
            "filename": None,
            "upload_timestamp": None,
            "total_chunks": 0,
            "structured_fields": {
                "content_type": None,
                "difficulty": None,
                "primary_category": None,
                "types_discussed": set(),
                "functions_covered": set(),
                "relationship_type": None,
                "quadra": None,
                "temple": None,
                "topics": set(),
                "use_case": set()
            },
            "enriched_fields": {
                "season": None,
                "episode": None,
                "types_mentioned": set(),
                "functions_mentioned": set()
            },
            "legacy_tags": set()
        }
        
        try:
            matches = query_response.matches
        except AttributeError:
            matches = query_response.get("matches", [])
        
        if not matches:
            return JSONResponse(
                status_code=404,
                content={"error": f"Document {doc_id} not found"})
        
        # Aggregate metadata from all chunks
        for match in matches:
            metadata = getattr(match, "metadata", None)
            if not metadata:
                try:
                    metadata = match.get("metadata", {})
                except (AttributeError, TypeError):
                    metadata = {}
            
            if metadata:
                aggregated_metadata["total_chunks"] += 1
                
                # Extract basic info
                if not aggregated_metadata["filename"]:
                    aggregated_metadata["filename"] = metadata.get("filename", "Unknown")
                if not aggregated_metadata["upload_timestamp"]:
                    aggregated_metadata["upload_timestamp"] = metadata.get("upload_timestamp")
                
                # Extract structured fields
                sf = aggregated_metadata["structured_fields"]
                if not sf["content_type"]:
                    sf["content_type"] = metadata.get("content_type")
                if not sf["difficulty"]:
                    sf["difficulty"] = metadata.get("difficulty")
                if not sf["primary_category"]:
                    sf["primary_category"] = metadata.get("primary_category")
                if not sf["relationship_type"]:
                    sf["relationship_type"] = metadata.get("relationship_type")
                if not sf["quadra"]:
                    sf["quadra"] = metadata.get("quadra")
                if not sf["temple"]:
                    sf["temple"] = metadata.get("temple")
                
                # Aggregate array fields
                types_discussed = metadata.get("types_discussed", [])
                if isinstance(types_discussed, list):
                    sf["types_discussed"].update(types_discussed)
                
                functions_covered = metadata.get("functions_covered", [])
                if isinstance(functions_covered, list):
                    sf["functions_covered"].update(functions_covered)
                
                topics = metadata.get("topics", [])
                if isinstance(topics, list):
                    sf["topics"].update(topics)
                
                use_case = metadata.get("use_case", [])
                if isinstance(use_case, list):
                    sf["use_case"].update(use_case)
                
                # Extract enriched fields
                ef = aggregated_metadata["enriched_fields"]
                if not ef["season"]:
                    ef["season"] = metadata.get("season")
                if not ef["episode"]:
                    ef["episode"] = metadata.get("episode")
                
                types_mentioned = metadata.get("types_mentioned", [])
                if isinstance(types_mentioned, list):
                    ef["types_mentioned"].update(types_mentioned)
                
                functions_mentioned = metadata.get("functions_mentioned", [])
                if isinstance(functions_mentioned, list):
                    ef["functions_mentioned"].update(functions_mentioned)
                
                # Extract legacy tags
                tags = metadata.get("tags", [])
                if isinstance(tags, list):
                    aggregated_metadata["legacy_tags"].update(tags)
        
        # Convert sets to sorted lists for JSON serialization
        sf = aggregated_metadata["structured_fields"]
        sf["types_discussed"] = sorted(list(sf["types_discussed"]))
        sf["functions_covered"] = sorted(list(sf["functions_covered"]))
        sf["topics"] = sorted(list(sf["topics"]))
        sf["use_case"] = sorted(list(sf["use_case"]))
        
        ef = aggregated_metadata["enriched_fields"]
        ef["types_mentioned"] = sorted(list(ef["types_mentioned"]))
        ef["functions_mentioned"] = sorted(list(ef["functions_mentioned"]))
        
        aggregated_metadata["legacy_tags"] = sorted(list(aggregated_metadata["legacy_tags"]))
        
        print(f"✅ Retrieved full metadata for document {doc_id} ({aggregated_metadata['total_chunks']} chunks)")
        
        return aggregated_metadata
        
    except Exception as e:
        print(f"❌ Document metadata retrieval error: {str(e)}")
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
        # === SMART QUERY REWRITING ===
        # Detect special query patterns and auto-filter to relevant documents
        question_lower = question.lower()
        smart_filter_applied = False
        
        # Pattern 1: "Four Sides" queries
        four_sides_patterns = ["four sides", "4 sides", "four side", "quadrants of mind", "sides of mind"]
        if any(pattern in question_lower for pattern in four_sides_patterns):
            # Auto-filter to Four Sides documents only
            if not document_id or not document_id.strip():
                # Only apply smart filter if user didn't specify a document
                print(f"🧠 Smart filter detected: 'Four Sides' query → filtering to Four Sides documents")
                smart_filter_applied = True
                # We'll use filename filtering in the Pinecone query below
        
        embed_response = openai_client.embeddings.create(
            input=question, model="text-embedding-3-large")
        question_vector = embed_response.data[0].embedding
        
        # Log embedding usage
        embed_tokens = embed_response.usage.total_tokens
        embed_cost = (embed_tokens / 1000) * PRICING["text-embedding-3-large"]
        log_api_usage("query_embedding", "text-embedding-3-large", input_tokens=embed_tokens, cost=embed_cost)

        # ============================================================================
        # INTELLIGENT QUERY ANALYSIS (NEW - 2025-11-20)
        # ============================================================================
        # Analyze query for intent, entities, and smart filtering
        import time
        query_start = time.time()
        
        analysis = analyze_and_filter(question)
        
        query_analysis_time = time.time() - query_start
        print(f"\n🧠 Query Intelligence:")
        print(f"   Intent: {analysis['intent']} (confidence: {analysis['confidence']:.2f})")
        print(f"   Entities: {analysis['entities']}")
        print(f"   Smart filters: {analysis['use_smart_filters']}")
        print(f"   📊 Adaptive top_k: {analysis['recommended_top_k']}")
        print(f"   ⏱️ Analysis took {query_analysis_time:.3f}s")
        if analysis['pinecone_filter']:
            print(f"   Filter: {analysis['pinecone_filter']}")
        
        # Build Pinecone filter combining OLD (doc_id) + NEW (smart filters)
        filter_conditions = []
        
        # Preserve existing doc_id filtering (backward compatibility)
        if document_id and document_id.strip():
            filter_conditions.append({"doc_id": document_id})
        
        # Add smart metadata filters if confidence is high enough
        if analysis['use_smart_filters'] and analysis['pinecone_filter']:
            filter_conditions.append(analysis['pinecone_filter'])
        
        # Build final filter and query with timeout protection
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        
        # Use intelligent top_k (30-50 based on query complexity vs old 5)
        search_top_k = analysis['recommended_top_k']
        
        try:
            with ThreadPoolExecutor() as executor:
                if len(filter_conditions) == 0:
                    # No filters - search all documents
                    print(f"🔍 Searching across ALL documents (top_k={search_top_k})")
                    future = executor.submit(
                        pinecone_index.query,
                        vector=question_vector,
                        top_k=search_top_k,
                        include_metadata=True
                    )
                    query_response = future.result(timeout=10.0)
                elif len(filter_conditions) == 1:
                    # Single filter
                    filter_str = f"doc_id={document_id}" if document_id else f"tags={filter_tags}"
                    print(f"🔍 Searching with filter: {filter_str} (top_k={search_top_k})")
                    future = executor.submit(
                        pinecone_index.query,
                        vector=question_vector,
                        top_k=search_top_k,
                        include_metadata=True,
                        filter=filter_conditions[0]
                    )
                    query_response = future.result(timeout=10.0)
                else:
                    # Multiple filters - use $and
                    print(f"🔍 Searching with filters: doc_id={document_id}, tags={filter_tags} (top_k={search_top_k})")
                    future = executor.submit(
                        pinecone_index.query,
                        vector=question_vector,
                        top_k=search_top_k,
                        include_metadata=True,
                        filter={"$and": filter_conditions}
                    )
                    query_response = future.result(timeout=10.0)
        except (FuturesTimeoutError, TimeoutError):
            print(f"⏱️ Pinecone query timed out after 10 seconds")
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Knowledge base search timed out. Please try again.",
                    "answer": "The search is taking longer than expected. Please try rephrasing your question or try again in a moment."
                }
            )

        try:
            matches = query_response.matches  # type: ignore
        except AttributeError:
            matches = query_response.get("matches", [])  # type: ignore
        
        # ============================================================================
        # RE-RANK RESULTS USING METADATA INTELLIGENCE (NEW)
        # ============================================================================
        # Re-rank matches based on metadata relevance if smart filters were used
        if analysis['use_smart_filters']:
            print(f"🔄 Re-ranking {len(matches)} results using metadata intelligence...")
            ranked_results = rerank_results(matches, question, analysis)
            print(f"✅ Top {len(ranked_results)} results after re-ranking")
            
            # Use re-ranked results
            contexts = [r['text'] for r in ranked_results if r['text']]
            source_docs = {r['metadata'].get('filename', 'Unknown') for r in ranked_results}
        else:
            # Use original Pinecone ranking (backward compatibility)
            # Apply smart filtering if "Four Sides" pattern detected (legacy support)
            if smart_filter_applied:
                original_count = len(matches)
                matches = [
                    m for m in matches
                    if "metadata" in m and "filename" in m["metadata"] and 
                    "four sides" in m["metadata"]["filename"].lower()
                ]
                print(f"🧠 Legacy smart filter applied: {original_count} matches → {len(matches)} Four Sides matches")
            
            contexts = []
            source_docs = set()
            
            for m in matches:
                if "metadata" in m and "text" in m["metadata"]:
                    contexts.append(m["metadata"]["text"])
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
async def text_to_pdf(request: TextToPDFRequest, background_tasks: BackgroundTasks):
    """Convert text to PDF with AI-powered punctuation and grammar fixes"""
    try:
        openai_client = get_openai_client()
        if not openai_client:
            return JSONResponse(
                status_code=500,
                content={"error": "OpenAI client not initialized"})
        
        print(f"📝 Processing text for PDF generation...")
        
        # Use GPT to fix punctuation and grammar
        # For very long texts (>10k chars), process in chunks to avoid truncation
        print("🔧 Fixing punctuation and grammar with AI...")
        
        input_length = len(request.text)
        print(f"📏 Input text length: {input_length:,} characters")
        
        try:
            # If text is very long (>12,000 chars), process in chunks
            if input_length > 12000:
                print(f"⚠️ Text is long ({input_length:,} chars). Processing in chunks to avoid truncation...")
                
                # Split into chunks of ~10k characters at paragraph boundaries
                chunks = []
                current_chunk = ""
                paragraphs = request.text.split('\n')
                
                for para in paragraphs:
                    # Handle very long single paragraphs (>10k chars)
                    if len(para) > 10000:
                        # If current chunk has content, save it first
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = ""
                        
                        # Split oversized paragraph by sentences
                        sentences = para.split('. ')
                        for sentence in sentences:
                            if len(current_chunk) + len(sentence) < 10000:
                                current_chunk += sentence + '. '
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk)
                                current_chunk = sentence + '. '
                    
                    # Normal paragraph processing
                    elif len(current_chunk) + len(para) < 10000:
                        current_chunk += para + '\n'
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = para + '\n'
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                print(f"📦 Split into {len(chunks)} chunks")
                
                # Process each chunk
                cleaned_chunks = []
                for i, chunk in enumerate(chunks):
                    print(f"  Processing chunk {i+1}/{len(chunks)}...")
                    try:
                        completion = openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are an expert editor specializing in CS Joseph's MBTI content. Clean this transcript for readability while preserving his teaching voice:\n\nREMOVE:\n• Filler words: um, uh, like (when not comparison), you know, basically, right, okay, so, anyway, yeah\n• Word 'etc.' and 'etcetera' in all forms\n• Repetitive phrases and circular statements\n• Meta-commentary: 'we'll talk about that later', 'as I mentioned', 'I've said this before'\n• Tangents and off-topic rambling\n• Redundant explanations of the same point\n\nPRESERVE:\n• ALL MBTI types, cognitive functions (Ni, Ne, Ti, Te, Fi, Fe, Si, Se)\n• Technical Jungian concepts and terminology\n• Specific examples and analogies (these are gold for learning)\n• CS Joseph's conversational teaching tone - keep it engaging and direct\n• Important context that supports the main concepts\n\nOUTPUT:\n• Fix all punctuation and grammar\n• Add paragraph breaks at topic transitions\n• Make it concise but keep the 'good stuff'\n• Return ONLY the cleaned text with NO explanations"
                                },
                                {
                                    "role": "user",
                                    "content": chunk
                                }
                            ],
                            temperature=0.3,
                            max_tokens=4096
                        )
                        
                        content = completion.choices[0].message.content
                        if content:
                            cleaned_chunks.append(content.strip())
                        else:
                            cleaned_chunks.append(chunk)
                    except Exception as chunk_error:
                        print(f"  ⚠️ Chunk {i+1} failed: {str(chunk_error)}, using original")
                        cleaned_chunks.append(chunk)
                
                cleaned_text = '\n\n'.join(cleaned_chunks)
                print(f"✅ All chunks processed. Final length: {len(cleaned_text):,} chars")
                
            else:
                # Normal processing for shorter texts
                completion = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert editor specializing in CS Joseph's MBTI content. Clean this transcript for readability while preserving his teaching voice:\n\nREMOVE:\n• Filler words: um, uh, like (when not comparison), you know, basically, right, okay, so, anyway, yeah\n• Word 'etc.' and 'etcetera' in all forms\n• Repetitive phrases and circular statements\n• Meta-commentary: 'we'll talk about that later', 'as I mentioned', 'I've said this before'\n• Tangents and off-topic rambling\n• Redundant explanations of the same point\n\nPRESERVE:\n• ALL MBTI types, cognitive functions (Ni, Ne, Ti, Te, Fi, Fe, Si, Se)\n• Technical Jungian concepts and terminology\n• Specific examples and analogies (these are gold for learning)\n• CS Joseph's conversational teaching tone - keep it engaging and direct\n• Important context that supports the main concepts\n\nOUTPUT:\n• Fix all punctuation and grammar\n• Add paragraph breaks at topic transitions\n• Make it concise but keep the 'good stuff'\n• Return ONLY the cleaned text with NO explanations"
                        },
                        {
                            "role": "user",
                            "content": request.text
                        }
                    ],
                    temperature=0.3,
                    max_tokens=4096
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
            # Ensure ASCII-only for HTTP headers
            safe_filename = safe_filename.encode('ascii', 'ignore').decode('ascii')
            if not safe_filename:
                safe_filename = "document"
            
            # Schedule cleanup after response is sent
            background_tasks.add_task(os.remove, pdf_path)
            
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"{safe_filename}.pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{safe_filename}.pdf\"",
                    "Cache-Control": "no-cache"
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
async def reprocess_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
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
                # Split into chunks to avoid GPT output token limits (4096 tokens ~= 12-16KB)
                chunk_size = 2500  # Very conservative chunk size to prevent GPT output truncation
                text_chunks = []
                
                # Split text into manageable chunks
                for i in range(0, len(pdf_text), chunk_size):
                    chunk = pdf_text[i:i + chunk_size]
                    text_chunks.append(chunk)
                
                print(f"   Processing {len(text_chunks)} chunks...")
                
                # Process each chunk
                cleaned_chunks = []
                for idx, chunk in enumerate(text_chunks):
                    print(f"   Processing chunk {idx + 1}/{len(text_chunks)}...")
                    
                    completion = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a professional editor optimizing text for semantic search and vector embeddings. Your tasks: 1) Fix all punctuation, grammar, and formatting errors. 2) Remove speech filler words (so, yeah, anyway, basically, um, you know, etc.) only when they add no meaning. Preserve 'like' when used for comparisons or analogies. 3) Remove only the redundant clauses of meta-commentary (e.g., 'we'll get into that later', 'as I mentioned before') while keeping the substantive content of those sentences. 4) Normalize conversational tone to clear, direct statements while preserving all conceptual content, examples, and technical terminology. 5) Add proper paragraph breaks at topic transitions. Return only the cleaned text with NO explanations or comments."
                            },
                            {
                                "role": "user",
                                "content": chunk
                            }
                        ],
                        temperature=0.3
                    )
                    
                    cleaned_chunk = completion.choices[0].message.content.strip()
                    cleaned_chunks.append(cleaned_chunk)
                
                # Combine all cleaned chunks
                cleaned_text = "\n\n".join(cleaned_chunks)
                print(f"✅ Text enhanced successfully ({len(cleaned_chunks)} chunks processed)")
                
            except Exception as e:
                print(f"⚠️ GPT enhancement failed: {e}, using original text")
                cleaned_text = pdf_text
            
            # Helper function to sanitize ALL text for Latin-1 encoding
            def sanitize_for_pdf(text):
                """Remove all Unicode characters that cause Latin-1 encoding errors"""
                if not text:
                    return text
                # Smart quotes
                text = text.replace('\u2018', "'").replace('\u2019', "'")  # Single quotes
                text = text.replace('\u201C', '"').replace('\u201D', '"')  # Double quotes
                # Dashes
                text = text.replace('\u2013', '-').replace('\u2014', '--')  # En/em dash
                # Other common Unicode
                text = text.replace('\u2026', '...')  # Ellipsis
                text = text.replace('\u00A0', ' ')  # Non-breaking space
                text = text.replace('\u2022', '*')  # Bullet point
                text = text.replace('\u2010', '-')  # Hyphen
                text = text.replace('\u2011', '-')  # Non-breaking hyphen
                text = text.replace('\u2012', '-')  # Figure dash
                text = text.replace('\u2015', '--')  # Horizontal bar
                # Remove any other non-ASCII characters as last resort
                text = text.encode('ascii', 'ignore').decode('ascii')
                return text
            
            # Generate improved PDF
            print("📄 Creating improved PDF...")
            print(f"   Cleaned text length: {len(cleaned_text)} characters")
            
            # SANITIZE ALL TEXT FIRST (GPT often returns smart quotes!)
            cleaned_text = sanitize_for_pdf(cleaned_text)
            original_title = file.filename.replace('.pdf', '').replace('_', ' ')
            original_title = sanitize_for_pdf(original_title)
            
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
                alignment=TA_LEFT,
                wordWrap='CJK'  # Better word wrapping
            )
            
            metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, textColor='gray')
            
            # Build PDF content
            story = []
            
            # Title
            story.append(Paragraph(f"<b>{original_title} (Enhanced)</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Metadata
            story.append(Paragraph(f"Reprocessed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", metadata_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Content - handle as continuous text with paragraph breaks
            paragraphs = cleaned_text.split('\n')
            paragraph_count = 0
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Escape HTML special characters but preserve text
                    para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(para, body_style))
                    story.append(Spacer(1, 0.15*inch))
                    paragraph_count += 1
            
            print(f"   Created {paragraph_count} paragraphs for PDF")
            
            # Build PDF
            doc.build(story)
            print(f"✅ Enhanced PDF created at {output_pdf_path}")
            
            # Return the improved PDF - sanitize filename for HTTP headers
            safe_filename = file.filename.replace('.pdf', '_enhanced.pdf').replace('/', '-').replace('\\', '-')
            safe_filename = sanitize_for_pdf(safe_filename)  # Remove Unicode characters from filename
            # Ensure ASCII-only for HTTP headers
            safe_filename = safe_filename.encode('ascii', 'ignore').decode('ascii')
            if not safe_filename or safe_filename == '_enhanced.pdf':
                safe_filename = "document_enhanced.pdf"
            
            # Schedule cleanup after response is sent
            background_tasks.add_task(os.remove, output_pdf_path)
            background_tasks.add_task(os.remove, temp_pdf_path)
            
            return FileResponse(
                output_pdf_path,
                media_type="application/pdf",
                filename=safe_filename,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{safe_filename}\"",
                    "Cache-Control": "no-cache"
                }
            )
            
        except Exception as cleanup_error:
            # Only cleanup temp_pdf_path here, output_pdf_path is handled by background task
            try:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
            except:
                pass
            raise cleanup_error
        
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
            
            # Auto-tag document with structured metadata (GPT-4o-mini)
            structured_metadata = await auto_tag_document(text, pdf_filename, openai_client)
            
            # Extract enriched metadata
            enriched_meta = extract_enriched_metadata(pdf_filename, text[:2000])
            
            # Batch embedding + upsert with improved embeddings
            vectors_to_upsert = []
            for i, chunk in enumerate(chunks):
                if i % 50 == 0 and i > 0:
                    print(f"📊 Processing chunk {i}/{len(chunks)}...")
                
                response = openai_client.embeddings.create(
                    input=chunk, model="text-embedding-3-large", timeout=120)
                vector = response.data[0].embedding
                
                # Build comprehensive metadata with structured fields
                chunk_metadata = {
                    "text": chunk,
                    "doc_id": doc_id,
                    "filename": pdf_filename,
                    "upload_timestamp": datetime.now().isoformat(),
                    "source": "audio_upload",
                    "chunk_index": i,
                    # Structured metadata from GPT-4o-mini
                    "content_type": structured_metadata.get("content_type", "none"),
                    "difficulty": structured_metadata.get("difficulty", "none"),
                    "primary_category": structured_metadata.get("primary_category", "none"),
                    "types_discussed": structured_metadata.get("types_discussed", []),
                    "functions_covered": structured_metadata.get("functions_covered", []),
                    "relationship_type": structured_metadata.get("relationship_type", "none"),
                    "quadra": structured_metadata.get("quadra", "none"),
                    "temple": structured_metadata.get("temple", "none"),
                    "topics": structured_metadata.get("topics", []),
                    "use_case": structured_metadata.get("use_case", [])
                }
                chunk_metadata.update(enriched_meta)
                
                vectors_to_upsert.append((f"{doc_id}-{i}", vector, chunk_metadata))
            
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
                "message": "Audio transcribed and indexed with structured metadata",
                "document_id": doc_id,
                "filename": pdf_filename,
                "chunks_count": len(chunks),
                "structured_metadata": structured_metadata,
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


# === YouTube Video Import & Matching ===
from src.services.youtube_matcher import YouTubeMatcher

@app.post("/api/youtube/import")
async def import_youtube_csv(
    request: Request,
    file: UploadFile = File(...),
    csrf_protect: CsrfProtect = Depends()
):
    """
    Import YouTube videos from CSV and match to lessons.
    
    Expected CSV format: season, title, category, url
    Returns match results and statistics.
    """
    try:
        # Validate CSRF token
        await csrf_protect.validate_csrf(request)
        
        print(f"📺 Received YouTube CSV file: {file.filename}")
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            return JSONResponse(
                status_code=400,
                content={"error": "File must be a CSV file"}
            )
        
        # Read CSV content
        contents = await file.read()
        csv_content = contents.decode('utf-8')
        
        print(f"📊 CSV file size: {len(csv_content)} characters")
        
        # Process CSV with matcher
        matcher = YouTubeMatcher()
        results = matcher.process_csv_import(csv_content)
        
        # Return summary
        return {
            "message": "YouTube CSV processed successfully",
            "summary": {
                "total_videos": results['total'],
                "high_confidence": results['high_confidence'],
                "medium_confidence": results['medium_confidence'],
                "low_confidence": results['low_confidence'],
                "unmatched": results['unmatched']
            },
            "matches": [
                {
                    "video_title": r.video.title,
                    "video_url": r.video.url,
                    "video_id": r.video.video_id,
                    "season": r.video.season,
                    "lesson_id": r.lesson_id,
                    "lesson_title": r.lesson_title,
                    "confidence_score": round(r.confidence_score, 3),
                    "match_type": r.match_type
                }
                for r in results['results']
            ]
        }
        
    except Exception as e:
        print(f"❌ YouTube CSV import error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process YouTube CSV: {str(e)}"}
        )


@app.get("/api/youtube/pending")
async def get_pending_videos():
    """Get all pending YouTube videos awaiting review"""
    try:
        conn = get_db_connection()
        if not conn:
            return JSONResponse(
                status_code=500,
                content={"error": "Database connection failed"}
            )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT 
                id, provider_video_id, source_url, title, season, category,
                status, confidence_score, matched_lesson_id, created_at
            FROM pending_youtube_videos
            WHERE status IN ('unmatched', 'pending_review')
            ORDER BY confidence_score DESC, created_at DESC
        """)
        
        pending = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            "count": len(pending),
            "pending_videos": [dict(video) for video in pending]
        }
        
    except Exception as e:
        print(f"❌ Error fetching pending videos: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch pending videos: {str(e)}"}
        )


@app.post("/api/youtube/link/{pending_id}/{lesson_id}")
async def link_pending_video(
    request: Request,
    pending_id: int,
    lesson_id: str,
    csrf_protect: CsrfProtect = Depends()
):
    """Link a pending YouTube video to a lesson"""
    try:
        # Validate CSRF token
        await csrf_protect.validate_csrf(request)
        
    except CsrfProtectError as e:
        raise HTTPException(status_code=403, detail="CSRF token validation failed")
    
    try:
        conn = get_db_connection()
        if not conn:
            return JSONResponse(
                status_code=500,
                content={"error": "Database connection failed"}
            )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get pending video details
        cursor.execute("""
            SELECT provider_video_id, source_url, title, season, category
            FROM pending_youtube_videos
            WHERE id = %s
        """, (pending_id,))
        
        video = cursor.fetchone()
        if not video:
            cursor.close()
            conn.close()
            return JSONResponse(
                status_code=404,
                content={"error": "Pending video not found"}
            )
        
        # Create document
        cursor.execute("""
            INSERT INTO documents (
                doc_type, source_url, provider_video_id, title, season, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider_video_id) DO UPDATE
            SET source_url = EXCLUDED.source_url,
                title = EXCLUDED.title
            RETURNING id
        """, (
            'youtube',
            video['source_url'],
            video['provider_video_id'],
            video['title'],
            video['season'],
            Json({'category': video['category'], 'manually_linked': True})
        ))
        
        document_id = cursor.fetchone()['id']
        
        # Link to lesson
        cursor.execute("""
            INSERT INTO lesson_documents (lesson_id, document_id, relationship_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (lesson_id, document_id) DO NOTHING
        """, (lesson_id, document_id, 'primary_resource'))
        
        # Update pending video status
        cursor.execute("""
            UPDATE pending_youtube_videos
            SET status = 'linked', matched_lesson_id = %s
            WHERE id = %s
        """, (lesson_id, pending_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Linked pending video {pending_id} to lesson {lesson_id}")
        
        return {
            "message": "Video linked successfully",
            "document_id": str(document_id),
            "lesson_id": lesson_id
        }
        
    except Exception as e:
        print(f"❌ Error linking video: {str(e)}")
        if conn:
            conn.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to link video: {str(e)}"}
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
            
            # Auto-tag document with structured metadata (GPT-4o-mini)
            structured_metadata = await auto_tag_document(text, pdf_filename, openai_client)
            
            # Extract enriched metadata
            enriched_meta = extract_enriched_metadata(pdf_filename, text[:2000])
            
            # Batch embedding + upsert with improved embeddings
            vectors_to_upsert = []
            for i, chunk in enumerate(chunks):
                if i % 50 == 0 and i > 0:
                    print(f"📊 Processing chunk {i}/{len(chunks)}...")
                
                response = openai_client.embeddings.create(
                    input=chunk, model="text-embedding-3-large", timeout=120)
                vector = response.data[0].embedding
                
                # Build comprehensive metadata with structured fields
                chunk_metadata = {
                    "text": chunk,
                    "doc_id": doc_id,
                    "filename": pdf_filename,
                    "upload_timestamp": datetime.now().isoformat(),
                    "source": "youtube_url",
                    "chunk_index": i,
                    # Structured metadata from GPT-4o-mini
                    "content_type": structured_metadata.get("content_type", "none"),
                    "difficulty": structured_metadata.get("difficulty", "none"),
                    "primary_category": structured_metadata.get("primary_category", "none"),
                    "types_discussed": structured_metadata.get("types_discussed", []),
                    "functions_covered": structured_metadata.get("functions_covered", []),
                    "relationship_type": structured_metadata.get("relationship_type", "none"),
                    "quadra": structured_metadata.get("quadra", "none"),
                    "temple": structured_metadata.get("temple", "none"),
                    "topics": structured_metadata.get("topics", []),
                    "use_case": structured_metadata.get("use_case", [])
                }
                chunk_metadata.update(enriched_meta)
                
                vectors_to_upsert.append((f"{doc_id}-{i}", vector, chunk_metadata))
            
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
                "message": "YouTube video downloaded, transcribed, and indexed with structured metadata",
                "document_id": doc_id,
                "filename": pdf_filename,
                "video_title": video_title,
                "chunks_count": len(chunks),
                "structured_metadata": structured_metadata,
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
        
        # Step 6: Auto-tag with structured metadata (GPT-4o-mini)
        print("🏷️ Auto-tagging with structured metadata...")
        structured_metadata = await auto_tag_document(cleaned_transcript, pdf_filename, openai_client)
        print(f"✅ Structured metadata extracted:")
        print(f"   Content Type: {structured_metadata.get('content_type')}")
        print(f"   Difficulty: {structured_metadata.get('difficulty')}")
        print(f"   Topics: {structured_metadata.get('topics', [])[:3]}...")
        
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
            
            # Create embeddings and vectors with structured metadata
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
                            "source": "youtube_transcript",
                            "video_url": youtube_url,
                            # Structured metadata from GPT-4o-mini
                            "content_type": structured_metadata.get("content_type", "none"),
                            "difficulty": structured_metadata.get("difficulty", "none"),
                            "primary_category": structured_metadata.get("primary_category", "none"),
                            "types_discussed": structured_metadata.get("types_discussed", []),
                            "functions_covered": structured_metadata.get("functions_covered", []),
                            "relationship_type": structured_metadata.get("relationship_type", "none"),
                            "quadra": structured_metadata.get("quadra", "none"),
                            "temple": structured_metadata.get("temple", "none"),
                            "topics": structured_metadata.get("topics", []),
                            "use_case": structured_metadata.get("use_case", [])
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
                "message": "YouTube transcript fetched, cleaned, and indexed with structured metadata!",
                "document_id": doc_id,
                "filename": pdf_filename,
                "video_title": video_title,
                "chunks_count": len(chunks),
                "structured_metadata": structured_metadata,
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


# ==============================================================================
# PHASE 7.1: CURRICULUM DASHBOARD ROUTES
# ==============================================================================

import logging
logger = logging.getLogger(__name__)

@app.get("/")
async def serve_mbti_chat():
    """Serve the main MBTI chat interface"""
    return FileResponse("index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/dashboard")
async def serve_curriculum_dashboard():
    """Serve the CS Joseph University curriculum dashboard"""
    return FileResponse("static/curriculum_dashboard.html")

@app.get("/innerverse")
async def innerverse_chat():
    """
    Phase 1: New chat interface (clean rebuild, no Chatscope)
    """
    return FileResponse(
        "templates/innerverse.html", 
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.get("/api/curriculum/summary")
async def get_curriculum_summary() -> Dict[str, Any]:
    """
    Get curriculum structure for dashboard display
    
    Returns:
        {
          "modules": [
            {
              "module_number": 1,
              "module_name": "Getting Started",
              "total_lessons": 3,
              "completed_lessons": 2,
              "seasons": [
                {
                  "season_number": "0",
                  "season_name": "Orientation",
                  "lesson_count": 3,
                  "completed_count": 2,
                  "last_accessed": "2025-11-14T10:30:00"
                }
              ]
            },
            ...
          ],
          "total_lessons": 742,
          "total_completed": 47
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get module summary
        cursor.execute("""
            SELECT 
                c.module_number,
                c.module_name,
                COUNT(c.lesson_id) as total_lessons,
                COUNT(CASE WHEN p.completed = TRUE THEN 1 END) as completed_lessons,
                MAX(p.last_accessed) as last_accessed
            FROM curriculum c
            LEFT JOIN progress p ON c.lesson_id = p.lesson_id
            GROUP BY c.module_number, c.module_name
            ORDER BY c.module_number
        """)
        
        modules_data = cursor.fetchall()
        modules = []
        
        for module_row in modules_data:
            module_number = int(module_row[0])
            module_name = str(module_row[1])
            total_lessons = int(module_row[2])
            completed_lessons = int(module_row[3] or 0)
            
            # Get seasons for this module
            cursor.execute("""
                SELECT 
                    c.season_number,
                    c.season_name,
                    COUNT(c.lesson_id) as lesson_count,
                    COUNT(CASE WHEN p.completed = TRUE THEN 1 END) as completed_count,
                    MAX(p.last_accessed) as last_accessed
                FROM curriculum c
                LEFT JOIN progress p ON c.lesson_id = p.lesson_id
                WHERE c.module_number = %s
                GROUP BY c.season_number, c.season_name
                ORDER BY MIN(c.order_index)
            """, (module_number,))
            
            seasons_data = cursor.fetchall()
            seasons = []
            
            for season_row in seasons_data:
                seasons.append({
                    "season_number": str(season_row[0]),
                    "season_name": str(season_row[1]),
                    "lesson_count": int(season_row[2]),
                    "completed_count": int(season_row[3] or 0),
                    "last_accessed": season_row[4].isoformat() if season_row[4] else None
                })
            
            modules.append({
                "module_number": module_number,
                "module_name": module_name,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "seasons": seasons
            })
        
        # Get overall stats
        cursor.execute("SELECT COUNT(*) FROM curriculum")
        total_lessons = int(cursor.fetchone()[0])
        
        cursor.execute("SELECT COUNT(*) FROM progress WHERE completed = TRUE")
        total_completed = int(cursor.fetchone()[0])
        
        return {
            "modules": modules,
            "total_lessons": total_lessons,
            "total_completed": total_completed
        }
        
    except Exception as e:
        logger.error(f"Error fetching curriculum summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.get("/api/progress/continue")
async def get_continue_learning() -> Dict[str, Any]:
    """
    Get the lesson to continue learning from
    
    Returns last accessed incomplete lesson, or first incomplete lesson if none accessed
    
    Returns:
        {
          "lesson_id": 6,
          "lesson_title": "Hero Function Deep Dive",
          "module_name": "Building Foundation",
          "season_name": "Jungian Cognitive Functions",
          "season_number": "1",
          "lesson_number": 3,
          "last_accessed": "2025-11-14T10:30:00",
          "progress_percent": 6.4
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Find last accessed incomplete lesson
        cursor.execute("""
            SELECT 
                c.lesson_id,
                c.lesson_title,
                c.module_name,
                c.season_name,
                c.season_number,
                c.lesson_number,
                p.last_accessed
            FROM curriculum c
            LEFT JOIN progress p ON c.lesson_id = p.lesson_id
            WHERE p.completed = FALSE OR p.completed IS NULL
            ORDER BY p.last_accessed DESC NULLS LAST, c.order_index ASC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        
        if not row:
            # All lessons complete! Return first lesson
            cursor.execute("""
                SELECT 
                    c.lesson_id,
                    c.lesson_title,
                    c.module_name,
                    c.season_name,
                    c.season_number,
                    c.lesson_number,
                    p.last_accessed
                FROM curriculum c
                LEFT JOIN progress p ON c.lesson_id = p.lesson_id
                ORDER BY c.order_index ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
        
        # Calculate overall progress
        cursor.execute("SELECT COUNT(*) FROM curriculum")
        total = int(cursor.fetchone()[0])
        
        cursor.execute("SELECT COUNT(*) FROM progress WHERE completed = TRUE")
        completed = int(cursor.fetchone()[0])
        
        progress_percent = round((completed / total * 100), 1) if total > 0 else 0.0
        
        return {
            "lesson_id": int(row[0]),
            "lesson_title": str(row[1]),
            "module_name": str(row[2]),
            "season_name": str(row[3]),
            "season_number": str(row[4]),
            "lesson_number": int(row[5]),
            "last_accessed": row[6].isoformat() if row[6] else None,
            "progress_percent": float(progress_percent)
        }
        
    except Exception as e:
        logger.error(f"Error fetching continue learning: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.get("/api/curriculum/stats")
async def get_curriculum_stats() -> Dict[str, Any]:
    """
    Get overall curriculum statistics
    
    Returns:
        {
          "total_lessons": 742,
          "completed_lessons": 47,
          "progress_percent": 6.3,
          "total_duration": "385h 22m",
          "completed_duration": "24h 15m",
          "modules_count": 5,
          "seasons_count": 32
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Total lessons
        cursor.execute("SELECT COUNT(*) FROM curriculum")
        total_lessons = int(cursor.fetchone()[0])
        
        # Completed lessons
        cursor.execute("SELECT COUNT(*) FROM progress WHERE completed = TRUE")
        completed_lessons = int(cursor.fetchone()[0])
        
        # Progress percent
        progress_percent = round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0.0
        
        # Unique modules
        cursor.execute("SELECT COUNT(DISTINCT module_number) FROM curriculum")
        modules_count = int(cursor.fetchone()[0])
        
        # Unique seasons
        cursor.execute("SELECT COUNT(DISTINCT season_number) FROM curriculum")
        seasons_count = int(cursor.fetchone()[0])
        
        # TODO: Calculate duration when we have actual duration data
        total_duration = "TBD"
        completed_duration = "TBD"
        
        return {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "progress_percent": float(progress_percent),
            "total_duration": total_duration,
            "completed_duration": completed_duration,
            "modules_count": modules_count,
            "seasons_count": seasons_count
        }
        
    except Exception as e:
        logger.error(f"Error fetching curriculum stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==============================================================================
# END PHASE 7.1 ROUTES
# ==============================================================================

# ==============================================================================
# PHASE 7.2: SEASON VIEW ROUTES
# ==============================================================================

@app.get("/season/{season_number}")
async def serve_season_view(season_number: str):
    """
    Serve the season view page for a specific season
    
    Args:
        season_number: Season number (e.g., "1", "16", "2")
    
    Returns:
        HTML page showing all lessons in the season
    """
    return FileResponse("static/season_view.html")


@app.get("/api/season/{season_number}")
async def get_season_data(season_number: str) -> Dict[str, Any]:
    """
    Get all lessons and metadata for a specific season
    
    Args:
        season_number: Season number (e.g., "1", "16", "2")
    
    Returns:
        {
          "season_info": {
            "season_number": "1",
            "season_name": "Jungian Cognitive Functions",
            "module_number": 2,
            "module_name": "Building Foundation",
            "total_lessons": 16,
            "completed_lessons": 2,
            "progress_percent": 12.5
          },
          "lessons": [
            {
              "lesson_id": 4,
              "lesson_number": 1,
              "lesson_title": "Introduction to Cognitive Functions",
              "duration": "15:22",
              "has_video": true,
              "completed": true,
              "last_accessed": "2025-11-14T10:30:00",
              "order_index": 4
            },
            ...
          ]
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get season info
        cursor.execute("""
            SELECT 
                season_number,
                season_name,
                module_number,
                module_name,
                COUNT(lesson_id) as total_lessons
            FROM curriculum
            WHERE season_number = %s
            GROUP BY season_number, season_name, module_number, module_name
        """, (season_number,))
        
        season_row = cursor.fetchone()
        
        if not season_row:
            raise HTTPException(status_code=404, detail=f"Season {season_number} not found")
        
        season_info = {
            "season_number": str(season_row[0]),
            "season_name": str(season_row[1]),
            "module_number": int(season_row[2]),
            "module_name": str(season_row[3]),
            "total_lessons": int(season_row[4])
        }
        
        # Get completion count for this season
        cursor.execute("""
            SELECT COUNT(*) 
            FROM curriculum c
            JOIN progress p ON c.lesson_id = p.lesson_id
            WHERE c.season_number = %s AND p.completed = TRUE
        """, (season_number,))
        
        completed_count = cursor.fetchone()[0] or 0
        season_info["completed_lessons"] = int(completed_count)
        season_info["progress_percent"] = round(
            (completed_count / season_info["total_lessons"] * 100), 1
        ) if season_info["total_lessons"] > 0 else 0.0
        
        # Get all lessons in this season with progress
        cursor.execute("""
            SELECT 
                c.lesson_id,
                c.lesson_number,
                c.lesson_title,
                c.duration,
                c.has_video,
                c.order_index,
                c.description,
                COALESCE(p.completed, FALSE) as completed,
                p.last_accessed
            FROM curriculum c
            LEFT JOIN progress p ON c.lesson_id = p.lesson_id
            WHERE c.season_number = %s
            ORDER BY c.lesson_number ASC
        """, (season_number,))
        
        lessons_data = cursor.fetchall()
        lessons = []
        
        for row in lessons_data:
            lessons.append({
                "lesson_id": int(row[0]),
                "lesson_number": int(row[1]),
                "lesson_title": str(row[2]),
                "duration": str(row[3]) if row[3] else None,
                "has_video": bool(row[4]),
                "order_index": int(row[5]),
                "description": str(row[6]) if row[6] else None,
                "completed": bool(row[7]),
                "last_accessed": row[8].isoformat() if row[8] else None
            })
        
        return {
            "season_info": season_info,
            "lessons": lessons
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching season data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==============================================================================
# END PHASE 7.2 ROUTES
# ==============================================================================

# ==============================================================================
# PHASE 7.3: LESSON PAGE ROUTES
# ==============================================================================

@app.get("/lesson/{lesson_id}")
async def serve_lesson_page(lesson_id: int):
    """
    Serve the lesson page HTML
    
    Args:
        lesson_id: Lesson ID from curriculum table
    
    Returns:
        HTML page with video, AI content, transcript, chat
    """
    return FileResponse("static/lesson_page.html")


@app.get("/category/{category_slug}")
async def serve_category_view(request: Request, category_slug: str):
    """
    Serve category view page for supplementary library
    
    Args:
        category_slug: URL-friendly category name
    
    Returns:
        HTML page with lesson grid for category
    """
    # Map slug to category name
    category_map = {
        'cs-joseph-responds': 'CS Joseph Responds',
        'livestream-specials': 'Livestream Specials',
        'public-qa': 'Public Q&A',
        'cs-psychic': 'CS Psychic',
        'analyzing-true-crime': 'Analyzing True Crime',
        'typing-famous-people': 'Typing Famous People'
    }
    
    category_name = category_map.get(category_slug)
    if not category_name:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get lessons for this category with progress data
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.lesson_id, 
                c.lesson_title, 
                c.transcript_id,
                COALESCE(p.completed, FALSE) as watched,
                p.last_accessed
            FROM curriculum c
            LEFT JOIN progress p ON c.lesson_id = p.lesson_id
            WHERE c.is_supplementary = 1 
            AND c.category = %s
            ORDER BY c.lesson_number
        """, (category_name,))
        
        lessons = []
        for row in cursor.fetchall():
            lessons.append({
                'lesson_id': row[0],
                'lesson_title': row[1],
                'transcript_id': row[2],
                'watched': row[3],
                'last_accessed': row[4].isoformat() if row[4] else None
            })
        
        return templates.TemplateResponse("category_view.html", {
            "request": request,
            "category_name": category_name,
            "lesson_count": len(lessons),
            "lessons": lessons
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading category {category_slug}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.get("/api/lesson/{lesson_id}")
async def get_lesson_data(lesson_id: int) -> Dict[str, Any]:
    """
    Get complete lesson data including progress and navigation
    
    Args:
        lesson_id: Lesson ID from curriculum table
    
    Returns:
        {
          "lesson": {...},
          "progress": {...},
          "navigation": {...},
          "season_lessons": [...]
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get lesson data
        cursor.execute("""
            SELECT 
                c.lesson_id,
                c.lesson_title,
                c.lesson_number,
                c.season_number,
                c.season_name,
                c.module_number,
                c.module_name,
                c.youtube_url,
                c.has_video,
                c.transcript_id,
                c.duration,
                c.order_index,
                c.description
            FROM curriculum c
            WHERE c.lesson_id = %s
        """, (lesson_id,))
        
        lesson_row = cursor.fetchone()
        
        if not lesson_row:
            raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")
        
        lesson = {
            "lesson_id": int(lesson_row[0]),
            "lesson_title": str(lesson_row[1]),
            "lesson_number": int(lesson_row[2]),
            "season_number": str(lesson_row[3]),
            "season_name": str(lesson_row[4]),
            "module_number": int(lesson_row[5]),
            "module_name": str(lesson_row[6]),
            "youtube_url": str(lesson_row[7]) if lesson_row[7] else None,
            "has_video": bool(lesson_row[8]),
            "transcript_id": str(lesson_row[9]),
            "duration": str(lesson_row[10]) if lesson_row[10] else None,
            "order_index": int(lesson_row[11]),
            "description": str(lesson_row[12]) if lesson_row[12] else None
        }
        
        current_order = lesson["order_index"]
        season_number = lesson["season_number"]
        
        # Get or create progress
        cursor.execute("""
            SELECT completed, last_accessed
            FROM progress
            WHERE lesson_id = %s
        """, (lesson_id,))
        
        progress_row = cursor.fetchone()
        
        if progress_row:
            progress = {
                "completed": bool(progress_row[0]),
                "last_accessed": progress_row[1].isoformat() if progress_row[1] else None
            }
        else:
            # Create progress entry for this lesson
            cursor.execute("""
                INSERT INTO progress (lesson_id, completed, last_accessed)
                VALUES (%s, FALSE, CURRENT_TIMESTAMP)
            """, (lesson_id,))
            conn.commit()
            
            progress = {
                "completed": False,
                "last_accessed": None
            }
        
        # Update last_accessed
        cursor.execute("""
            UPDATE progress
            SET last_accessed = CURRENT_TIMESTAMP
            WHERE lesson_id = %s
        """, (lesson_id,))
        conn.commit()
        
        # Get previous lesson (same season only)
        cursor.execute("""
            SELECT lesson_id, lesson_title
            FROM curriculum
            WHERE season_number = %s
              AND order_index < %s
            ORDER BY order_index DESC
            LIMIT 1
        """, (season_number, current_order))
        
        prev_row = cursor.fetchone()
        prev_lesson_id = int(prev_row[0]) if prev_row else None
        
        # Get next lesson (same season only)
        cursor.execute("""
            SELECT lesson_id, lesson_title
            FROM curriculum
            WHERE season_number = %s
              AND order_index > %s
            ORDER BY order_index ASC
            LIMIT 1
        """, (season_number, current_order))
        
        next_row = cursor.fetchone()
        next_lesson_id = int(next_row[0]) if next_row else None
        
        navigation = {
            "prev_lesson_id": prev_lesson_id,
            "next_lesson_id": next_lesson_id,
            "has_prev": prev_lesson_id is not None,
            "has_next": next_lesson_id is not None
        }
        
        # Get all lessons in this season (for sidebar)
        cursor.execute("""
            SELECT 
                c.lesson_id,
                c.lesson_number,
                c.lesson_title,
                c.duration,
                p.completed
            FROM curriculum c
            LEFT JOIN progress p ON c.lesson_id = p.lesson_id
            WHERE c.season_number = %s
            ORDER BY c.order_index ASC
        """, (season_number,))
        
        season_lessons = []
        for row in cursor.fetchall():
            season_lessons.append({
                "lesson_id": int(row[0]),
                "lesson_number": int(row[1]),
                "lesson_title": str(row[2]),
                "duration": str(row[3]) if row[3] else None,
                "completed": bool(row[4]) if row[4] is not None else False
            })
        
        return {
            "lesson": lesson,
            "progress": progress,
            "navigation": navigation,
            "season_lessons": season_lessons
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lesson data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.get("/api/lesson/{lesson_id}/chat")
async def get_lesson_chat(lesson_id: int) -> Dict[str, Any]:
    """
    Get chat history for a lesson
    
    Returns:
        {
          "messages": [
            {"role": "user", "content": "...", "timestamp": "..."},
            {"role": "assistant", "content": "...", "timestamp": "..."}
          ]
        }
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT messages
            FROM lesson_chats
            WHERE lesson_id = %s
        """, (lesson_id,))
        
        row = cursor.fetchone()
        
        if row and row[0]:
            messages = row[0]  # Already a list from JSONB
        else:
            messages = []
        
        return {"messages": messages}
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.post("/api/lesson/{lesson_id}/chat")
async def save_lesson_chat(lesson_id: int, message: Dict[str, str]):
    """
    Save a chat message for a lesson
    
    Args:
        message: {"role": "user"|"assistant", "content": "...", "timestamp": "..."}
    
    Returns:
        {"success": true}
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if chat history exists
        cursor.execute("""
            SELECT lesson_id FROM lesson_chats WHERE lesson_id = %s
        """, (lesson_id,))
        
        exists = cursor.fetchone()
        
        if exists:
            # Append to existing messages
            cursor.execute("""
                UPDATE lesson_chats
                SET 
                    messages = messages || %s::jsonb,
                    updated_at = CURRENT_TIMESTAMP
                WHERE lesson_id = %s
            """, (json.dumps([message]), lesson_id))
        else:
            # Create new chat history
            cursor.execute("""
                INSERT INTO lesson_chats (lesson_id, messages, created_at, updated_at)
                VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (lesson_id, json.dumps([message])))
        
        conn.commit()
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.post("/api/lesson/{lesson_id}/complete")
async def mark_lesson_complete_route(lesson_id: int, request: Dict[str, Any]):
    """
    Toggle lesson completion status
    
    Args:
        request: {"completed": true/false}
    
    Returns:
        {"success": true, "completed": true/false}
    """
    conn = None
    cursor = None
    try:
        # Get completion status from request (default to true for backward compatibility)
        completed = request.get('completed', True)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update or insert progress with the specified completion state
        cursor.execute("""
            INSERT INTO progress (lesson_id, completed, last_accessed)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (lesson_id)
            DO UPDATE SET 
                completed = %s,
                last_accessed = CURRENT_TIMESTAMP
        """, (lesson_id, completed, completed))
        
        conn.commit()
        
        logger.info(f"Lesson {lesson_id} marked {'complete' if completed else 'incomplete'}")
        
        return {"success": True, "completed": completed}
        
    except Exception as e:
        logger.error(f"Error toggling lesson completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.post("/api/lesson/{lesson_id}/ai-chat")
async def lesson_ai_chat(lesson_id: int, request: dict):
    """
    Server-side proxy for AI chat with caching
    
    PERFORMANCE OPTIMIZATION: Checks cache first to avoid unnecessary API calls
    
    Args:
        lesson_id: Lesson ID
        request: {"question": "...", "force_regenerate": false}
    
    Returns:
        StreamingResponse with AI answer (from cache or freshly generated)
    """
    import httpx
    
    question = request.get("question", "")
    force_regenerate = request.get("force_regenerate", False)
    
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    conn = None
    cursor = None
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Only cache lesson content generation, NOT chat questions
        # Lesson content starts with "Create a comprehensive lesson summary"
        is_lesson_content_generation = question.startswith("Create a comprehensive lesson summary")
        
        # Check cache FIRST (only for lesson content, unless force regenerate)
        if is_lesson_content_generation and not force_regenerate:
            cursor.execute("""
                SELECT generated_content, generated_at
                FROM lesson_content_cache
                WHERE lesson_id = %s
            """, (lesson_id,))
            
            cached_row = cursor.fetchone()
            
            if cached_row:
                cached_content = cached_row[0]
                cached_at = cached_row[1]
                
                logger.info(f"💾 Cache HIT for lesson {lesson_id} (generated at {cached_at})")
                
                # Return cached content in SSE format for consistency
                async def return_cached():
                    # Split into chunks to simulate streaming (better UX)
                    chunk_size = 100
                    for i in range(0, len(cached_content), chunk_size):
                        chunk = cached_content[i:i + chunk_size]
                        yield f"data: {chunk}\n\n".encode('utf-8')
                
                return StreamingResponse(
                    return_cached(), 
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no"
                    }
                )
        
        # Cache MISS or force regenerate - fetch lesson data and generate fresh
        logger.info(f"🔄 Cache MISS for lesson {lesson_id} - generating fresh content")
        
        cursor.execute("""
            SELECT document_id, lesson_title
            FROM curriculum
            WHERE lesson_id = %s
        """, (lesson_id,))
        
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        document_id = row[0]
        lesson_title = row[1]
        
        if not document_id:
            async def no_content_fallback():
                message = "This lesson's content is not yet available in the knowledge base. The video is available to watch above!"
                yield f"data: {message}\n\n".encode('utf-8')
            
            return StreamingResponse(
                no_content_fallback(), 
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # Query Pinecone for transcript chunks
        logger.info(f"📜 Fetching transcript from Pinecone for document_id: {document_id}")
        
        try:
            index = get_pinecone_client()
            
            # Query with dummy vector to get chunks by metadata filter
            dummy_vector = [0.0] * 3072  # text-embedding-3-large dimension
            results = index.query(
                vector=dummy_vector,
                filter={"doc_id": document_id},
                top_k=200,  # Get all chunks (most lessons have <200 chunks)
                include_metadata=True
            )
            
            # Combine chunks into full transcript, sorted by chunk_index
            chunks_with_index = []
            for match in results.matches:
                metadata = match.metadata
                if 'text' in metadata:
                    chunk_index = metadata.get('chunk_index', 0)
                    chunks_with_index.append((chunk_index, metadata['text']))
            
            # Sort by chunk_index to maintain proper order
            chunks_with_index.sort(key=lambda x: x[0])
            transcript_chunks = [text for _, text in chunks_with_index]
            transcript_text = "\n\n".join(transcript_chunks)
            
            logger.info(f"✅ Retrieved {len(transcript_chunks)} transcript chunks ({len(transcript_text)} chars)")
            
        except Exception as e:
            logger.error(f"❌ Error fetching transcript from Pinecone: {e}")
            transcript_text = ""
        
        # If no transcript found, return fallback
        if not transcript_text or len(transcript_text) < 100:
            async def no_transcript_fallback():
                message = "This lesson's transcript is not yet available. The video is available to watch above!"
                yield f"data: {message}\n\n".encode('utf-8')
            
            return StreamingResponse(
                no_transcript_fallback(), 
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        
        # Direct Claude API streaming (no AXIS backend)
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        
        if not anthropic_api_key:
            raise HTTPException(status_code=500, detail="Anthropic API key not configured")
        
        # Add personality and context to chat questions (not lesson content generation)
        # IMPORTANT: Add transcript context for BOTH lesson content generation AND chat questions
        enhanced_question = question
        
        if is_lesson_content_generation:
            # For lesson content generation, provide full transcript
            enhanced_question = f"""{question}

LESSON TRANSCRIPT:
{transcript_text}"""
        else:
            # For chat questions, add personality + transcript context
            enhanced_question = f"""You are an enthusiastic MBTI and Jungian typology expert teaching CS Joseph's curriculum. You're passionate about cognitive functions and love helping people understand how their minds work.

YOUR PERSONALITY:
- Warm, engaging, and encouraging (like a great teacher, not a robot)
- Genuinely excited about typology concepts
- Patient but direct - you explain clearly without fluff
- Use CS Joseph's teaching style: concrete examples, real scenarios, practical applications

CRITICAL RULES:
- NEVER say "I'm just an AI" or "I don't have emotions" or "As an AI assistant"
- NEVER break character as a typology teacher
- STAY in character as a knowledgeable, enthusiastic human tutor
- BE conversational and natural - talk like a real person
- NO robotic disclaimers or corporate-speak

This is about the lesson: "{lesson_title}"

LESSON TRANSCRIPT:
{transcript_text}

Student question: {question}

Answer naturally as an enthusiastic typology expert based on the transcript content, NOT as a generic AI assistant."""
        
        async def generate_and_cache():
            """Generate fresh content using Claude API, stream it, AND save to cache"""
            import anthropic
            import json
            
            full_response = ""
            
            try:
                client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
                
                # Stream directly from Claude API (ASYNC!)
                async with client.messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": enhanced_question}]
                ) as stream:
                    async for text in stream.text_stream:
                        # Stream each chunk immediately
                        full_response += text
                        yield f"data: {text}\n\n".encode('utf-8')
                
                # After streaming completes, save to cache (ONLY for lesson content, not chat)
                if is_lesson_content_generation and full_response and len(full_response) > 50:
                    cache_conn = None
                    cache_cursor = None
                    try:
                        cache_conn = get_db()
                        cache_cursor = cache_conn.cursor()
                        
                        # Upsert to cache
                        cache_cursor.execute("""
                            INSERT INTO lesson_content_cache (lesson_id, generated_content, generated_at)
                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (lesson_id) 
                            DO UPDATE SET 
                                generated_content = EXCLUDED.generated_content,
                                generated_at = CURRENT_TIMESTAMP
                        """, (lesson_id, full_response))
                        
                        cache_conn.commit()
                        logger.info(f"💾 Cached {len(full_response)} chars for lesson {lesson_id}")
                        
                    except Exception as cache_error:
                        logger.error(f"Failed to cache content: {cache_error}")
                    finally:
                        if cache_cursor:
                            cache_cursor.close()
                        if cache_conn:
                            cache_conn.close()
                elif not is_lesson_content_generation:
                    logger.info(f"💬 Chat question - not caching (conversational)")
            
            except Exception as e:
                logger.error(f"Error in AI chat: {e}")
                yield f"data: Error: {str(e)}\n\n".encode('utf-8')
        
        return StreamingResponse(
            generate_and_cache(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in AI chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get("/api/lesson/{lesson_id}/transcript")
async def get_lesson_transcript(lesson_id: int) -> Dict[str, Any]:
    """
    Get raw transcript text for a lesson by fetching ALL chunks from Pinecone
    
    Returns:
        {
          "transcript": "Full transcript text...",
          "transcript_id": "season01_01",
          "available": true
        }
    """
    conn = None
    cursor = None
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get lesson's transcript_id and document_id
        cursor.execute("""
            SELECT transcript_id, lesson_title, document_id
            FROM curriculum
            WHERE lesson_id = %s
        """, (lesson_id,))
        
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        transcript_id = row[0]
        lesson_title = row[1]
        document_id = row[2]
        
        if not document_id:
            return {
                "transcript": None,
                "transcript_id": transcript_id,
                "available": False,
                "error": "No document ID mapped for this lesson"
            }
        
        # Query Pinecone DIRECTLY to get ALL chunks for this document
        logger.info(f"📜 Fetching ALL transcript chunks for lesson {lesson_id}: {lesson_title}")
        logger.info(f"🔍 Document ID: {document_id}")
        
        # Initialize Pinecone index
        index = get_pinecone_client()
        
        # Create a dummy query vector (we'll filter by metadata only)
        dummy_vector = [0.0] * 3072
        
        # Query with metadata filter to get ALL chunks for this document_id
        # Using top_k=10000 to ensure we get all chunks
        # NOTE: Pinecone uses 'doc_id' not 'document_id' in metadata
        results = index.query(
            vector=dummy_vector,
            filter={
                "doc_id": str(document_id)
            },
            top_k=10000,  # High limit to get all chunks
            include_metadata=True
        )
        
        if not results or not results.get('matches'):
            logger.warning(f"⚠️ No transcript chunks found for document {document_id}")
            return {
                "transcript": None,
                "transcript_id": transcript_id,
                "available": False,
                "error": "No transcript chunks found in Pinecone"
            }
        
        matches = results['matches']
        logger.info(f"📊 Found {len(matches)} chunks for document {document_id}")
        
        # Sort chunks by chunk_index to maintain order
        sorted_chunks = sorted(
            matches,
            key=lambda x: int(x.get('metadata', {}).get('chunk_index', 0))
        )
        
        # Extract and concatenate all chunk texts
        transcript_parts = []
        for match in sorted_chunks:
            chunk_text = match.get('metadata', {}).get('text', '')
            if chunk_text:
                transcript_parts.append(chunk_text)
        
        # Join all chunks with double newline for readability
        full_transcript = '\n\n'.join(transcript_parts)
        
        # Detailed logging
        char_count = len(full_transcript)
        logger.info(f"✅ Assembled transcript: {char_count:,} characters from {len(transcript_parts)} chunks")
        
        if full_transcript:
            preview_length = min(200, len(full_transcript))
            logger.info(f"📝 First 200 chars: {full_transcript[:preview_length]}")
            logger.info(f"📝 Last 200 chars: {full_transcript[-preview_length:]}")
        
        if not full_transcript:
            logger.warning(f"⚠️ Empty transcript after assembling chunks")
            return {
                "transcript": None,
                "transcript_id": transcript_id,
                "available": False,
                "error": "Empty transcript after assembling chunks"
            }
        
        return {
            "transcript": full_transcript,
            "transcript_id": transcript_id,
            "available": True,
            "char_count": char_count,
            "chunk_count": len(transcript_parts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==============================================================================
# END PHASE 7.3 ROUTES
# ==============================================================================

# ==============================================================================
# ADMIN API: AXIS MIND INTEGRATION
# ==============================================================================

class AddLessonRequest(BaseModel):
    """Request model for adding lessons from AXIS MIND uploader"""
    lesson_title: str
    youtube_url: str
    youtube_id: str  # YouTube video ID (becomes transcript_id)
    document_id: str  # UUID from Pinecone
    season_number: str | None = None
    episode_number: int | None = None
    category: str = ""
    is_supplementary: int = 0
    admin_token: str | None = None  # TODO: Implement proper authentication

@app.post("/api/admin/add-lesson")
async def add_lesson_from_uploader(request: AddLessonRequest):
    """
    API endpoint for AXIS MIND uploader to add new lessons
    
    Accepts lesson data from uploader and creates database entry
    
    Expected request body:
    {
        "lesson_title": "How Do ESFPs Compare To ENFPs?",
        "youtube_url": "https://youtube.com/watch?v=ABC123",
        "youtube_id": "ABC123",
        "season_number": "11",
        "episode_number": 4,
        "document_id": "uuid-from-pinecone",
        "category": "main_curriculum" or "supplementary",
        "is_supplementary": 0 or 1
    }
    
    Returns:
    {
        "success": true,
        "lesson_id": 123,
        "message": "Lesson added successfully"
    }
    """
    # WARNING: This endpoint currently has NO AUTHENTICATION
    # TODO: Add proper authentication before deploying to production
    # Recommended: Add admin_token validation or integrate with existing auth system
    
    conn = None
    cursor = None
    
    try:
        # Validate UUID format for document_id
        try:
            uuid.UUID(request.document_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid document_id format. Must be a valid UUID."
            )
        
        # Extract and validate data from request model
        lesson_title = request.lesson_title
        youtube_url = request.youtube_url
        youtube_id = request.youtube_id  # This is the transcript_id
        season_number = request.season_number
        episode_number = request.episode_number
        document_id = request.document_id
        category = request.category
        is_supplementary = request.is_supplementary
        
        # Check if lesson already exists (prevent duplicates)
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT lesson_id FROM curriculum 
            WHERE transcript_id = %s
        """, (youtube_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            cursor.close()
            conn.close()
            return {
                "success": False,
                "error": "duplicate",
                "message": f"Lesson with YouTube ID {youtube_id} already exists",
                "lesson_id": existing[0]
            }
        
        # Determine module and season info
        if is_supplementary:
            module_number = 99
            module_name = "Supplementary Content"
            season_name = category or "Supplementary"
            season_num_str = str(season_number) if season_number else "S99"
        else:
            # Main curriculum - map season to module
            season_num = int(season_number) if season_number else 1
            if season_num <= 10:
                module_number = 1
                module_name = "Module 1: Foundations"
            elif season_num <= 20:
                module_number = 2
                module_name = "Module 2: Development"
            elif season_num <= 30:
                module_number = 3
                module_name = "Module 3: Mastery"
            else:
                module_number = 4
                module_name = "Module 4: Advanced"
            
            season_num_str = str(season_number)
            season_name = f"Season {season_number}"
        
        # Get next order_index (must be globally unique)
        cursor.execute("SELECT MAX(order_index) FROM curriculum")
        max_order = cursor.fetchone()[0]
        order_index = (max_order or 0) + 1
        
        # Determine lesson number
        lesson_number = int(episode_number) if episode_number else order_index
        
        # Insert new lesson
        cursor.execute("""
            INSERT INTO curriculum (
                module_number, module_name, season_number, season_name,
                lesson_number, lesson_title, youtube_url, transcript_id,
                document_id, category, is_supplementary, order_index,
                has_video, content_type
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING lesson_id
        """, (
            module_number, module_name, season_num_str, season_name,
            lesson_number, lesson_title, youtube_url, youtube_id,
            document_id, category, is_supplementary, order_index,
            True, 'main' if not is_supplementary else 'supplementary'
        ))
        
        new_lesson_id = cursor.fetchone()[0]
        
        conn.commit()
        
        logger.info(f"✅ Added new lesson: {lesson_title} (ID: {new_lesson_id})")
        
        return {
            "success": True,
            "lesson_id": new_lesson_id,
            "message": f"Lesson '{lesson_title}' added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding lesson: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        # Don't leak database details to external callers
        raise HTTPException(
            status_code=500, 
            detail="Internal server error while adding lesson. Check server logs for details."
        )
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

# ==============================================================================
# END ADMIN API
# ==============================================================================


# ==============================================================================
# SEARCH API
# ==============================================================================

@app.post("/api/search")
async def search_lessons(request: dict):
    """
    Smart hybrid search endpoint
    
    Detects query type and routes to appropriate search method:
    - Exact match: "Season 18", "Lesson 42"
    - Title search: "ENFP", "cognitive functions"
    - Semantic search: "how do introverts recharge"
    
    Returns:
    [
        {
            "type": "lesson" or "season",
            "lesson_id": 123,
            "title": "...",
            "youtube_id": "...",
            "meta": "Season 11 • Lesson 4",
            "score": 0.95
        }
    ]
    """
    import re
    
    query = request.get("query", "").strip()
    
    if not query:
        return []
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        results = []
        
        # DETECTION 1: Season query (e.g., "Season 18", "s18")
        season_match = re.search(r'season\s*(\d+)', query, re.IGNORECASE)
        if season_match:
            season_num = int(season_match.group(1))
            results = search_by_season(cursor, season_num)
            cursor.close()
            conn.close()
            return results
        
        # DETECTION 2: Lesson query (e.g., "Lesson 42")
        lesson_match = re.search(r'lesson\s*(\d+)', query, re.IGNORECASE)
        if lesson_match:
            lesson_num = int(lesson_match.group(1))
            results = search_by_lesson_number(cursor, lesson_num)
            cursor.close()
            conn.close()
            return results
        
        # DETECTION 3: Category query (exact match)
        category_results = search_by_category(cursor, query)
        if category_results:
            results.extend(category_results)
        
        # DETECTION 4: Title search (fuzzy match)
        title_results = search_by_title(cursor, query)
        results.extend(title_results)
        
        # DETECTION 5: Semantic search (if Pinecone available)
        # TODO: Add semantic search via Pinecone
        
        cursor.close()
        conn.close()
        
        # Remove duplicates and sort by relevance
        seen = set()
        unique_results = []
        for r in results:
            key = f"{r['type']}_{r.get('lesson_id', r.get('season_id'))}"
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        return unique_results[:20]  # Max 20 results
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error while searching. Check server logs for details."
        )


def search_by_season(cursor, season_number):
    """Find all lessons in a specific season"""
    cursor.execute("""
        SELECT 
            'lesson' as type,
            lesson_id,
            lesson_title as title,
            transcript_id as youtube_id,
            season_number as season_id,
            CONCAT('Season ', season_number, ' • Lesson ', lesson_number) as meta,
            1.0 as score
        FROM curriculum
        WHERE season_number = %s
        ORDER BY lesson_number
        LIMIT 50
    """, (str(season_number),))
    
    return [dict(zip([col[0] for col in cursor.description], row)) 
            for row in cursor.fetchall()]


def search_by_lesson_number(cursor, lesson_id):
    """Find specific lesson by ID"""
    cursor.execute("""
        SELECT 
            'lesson' as type,
            lesson_id,
            lesson_title as title,
            transcript_id as youtube_id,
            season_number as season_id,
            CONCAT('Season ', season_number, ' • Lesson ', lesson_number) as meta,
            1.0 as score
        FROM curriculum
        WHERE lesson_id = %s
    """, (lesson_id,))
    
    results = cursor.fetchall()
    return [dict(zip([col[0] for col in cursor.description], row)) 
            for row in results]


def search_by_category(cursor, query):
    """Search by exact category match"""
    cursor.execute("""
        SELECT 
            'lesson' as type,
            lesson_id,
            lesson_title as title,
            transcript_id as youtube_id,
            season_number as season_id,
            CONCAT(category, ' • Lesson ', lesson_number) as meta,
            1.0 as score
        FROM curriculum
        WHERE LOWER(category) = LOWER(%s)
        ORDER BY lesson_number
        LIMIT 20
    """, (query,))
    
    results = cursor.fetchall()
    return [dict(zip([col[0] for col in cursor.description], row)) 
            for row in results]


def search_by_title(cursor, query):
    """Fuzzy search in lesson titles"""
    # Use PostgreSQL ILIKE for case-insensitive search
    search_term = f"%{query}%"
    
    cursor.execute("""
        SELECT 
            'lesson' as type,
            lesson_id,
            lesson_title as title,
            transcript_id as youtube_id,
            season_number as season_id,
            CONCAT('Season ', season_number, ' • Lesson ', lesson_number) as meta,
            0.8 as score
        FROM curriculum
        WHERE lesson_title ILIKE %s
        ORDER BY lesson_number
        LIMIT 15
    """, (search_term,))
    
    results = cursor.fetchall()
    return [dict(zip([col[0] for col in cursor.description], row)) 
            for row in results]

# ==============================================================================
# END SEARCH API
# ==============================================================================


# === Batch Re-Tagging System ===
@app.post("/api/batch-retag")
async def batch_retag_documents():
    """
    Batch re-tag ALL existing Pinecone documents with new structured metadata system.
    
    Process:
    1. Query all vectors from Pinecone
    2. Group by document_id
    3. For each document, extract text and run GPT-4o-mini tagging
    4. Update all chunks with new structured metadata
    5. Return progress updates
    """
    try:
        print("\n" + "="*60)
        print("🚀 BATCH RE-TAGGING STARTED")
        print("="*60)
        
        # Initialize clients
        openai_client = get_openai_client()
        if not openai_client:
            return JSONResponse(status_code=500, content={
                "error": "OpenAI client not initialized"
            })
        
        pinecone_index = get_pinecone_client()
        if not pinecone_index:
            return JSONResponse(status_code=500, content={
                "error": "Pinecone client not initialized"
            })
        
        # Step 1: Query all vectors from Pinecone
        print("\n📊 Step 1: Querying all vectors from Pinecone...")
        
        # Create a dummy query vector (3072 dimensions for text-embedding-3-large)
        dummy_query = [0.0] * 3072
        
        # Query with max top_k (Pinecone limit is 10,000)
        results = pinecone_index.query(
            vector=dummy_query,
            top_k=10000,
            include_metadata=True,
            include_values=True  # CRITICAL: Must include vector values for re-upsert
        )
        
        total_vectors = len(results.matches)
        print(f"✅ Found {total_vectors} vectors to process")
        
        if total_vectors == 0:
            return {
                "message": "No documents found in Pinecone",
                "documents_processed": 0,
                "vectors_updated": 0
            }
        
        if total_vectors == 10000:
            print("⚠️ WARNING: Hit Pinecone query limit (10,000). Some documents may not be processed.")
        
        # Step 2: Group vectors by document_id
        print("\n📚 Step 2: Grouping vectors by document_id...")
        documents = {}  # {doc_id: [vectors]}
        
        for match in results.matches:
            metadata = match.metadata
            doc_id = metadata.get('doc_id') or metadata.get('document_id')
            
            if not doc_id:
                print(f"⚠️ Skipping vector {match.id} - no document_id found")
                continue
            
            if doc_id not in documents:
                documents[doc_id] = []
            
            documents[doc_id].append({
                'id': match.id,
                'metadata': metadata,
                'values': match.values if hasattr(match, 'values') else None
            })
        
        total_documents = len(documents)
        print(f"✅ Found {total_documents} unique documents")
        
        # Step 3: Process each document
        print("\n🏷️ Step 3: Re-tagging documents with GPT-4o-mini...")
        
        processed = 0
        updated_vectors = 0
        failed = 0
        errors = []
        
        for doc_id, vectors in documents.items():
            try:
                processed += 1
                
                # Extract text from first few chunks (up to 3000 chars for tagging)
                combined_text = ""
                filename = vectors[0]['metadata'].get('filename', 'Unknown')
                
                for vec in vectors[:5]:  # Use first 5 chunks
                    chunk_text = vec['metadata'].get('text', '')
                    combined_text += chunk_text + " "
                    if len(combined_text) > 3000:
                        break
                
                combined_text = combined_text[:3000].strip()
                
                print(f"\n📄 [{processed}/{total_documents}] Processing: {filename}")
                print(f"   Document ID: {doc_id}")
                print(f"   Chunks: {len(vectors)}")
                
                # Run auto-tagging with GPT-4o-mini
                structured_metadata = await auto_tag_document(combined_text, filename, openai_client)
                
                print(f"   ✅ Structured metadata extracted:")
                print(f"      Content Type: {structured_metadata.get('content_type')}")
                print(f"      Difficulty: {structured_metadata.get('difficulty')}")
                print(f"      Primary Category: {structured_metadata.get('primary_category')}")
                print(f"      Topics: {len(structured_metadata.get('topics', []))} topics")
                
                # Step 4: Update all chunks for this document
                vectors_to_update = []
                
                for vec in vectors:
                    # Fetch original vector if we don't have values
                    if vec['values'] is None:
                        fetch_result = pinecone_index.fetch(ids=[vec['id']])
                        if vec['id'] in fetch_result.vectors:
                            vec['values'] = fetch_result.vectors[vec['id']].values
                        else:
                            print(f"   ⚠️ Could not fetch vector {vec['id']} - skipping")
                            continue
                    
                    # Keep all existing metadata, just add/update structured fields
                    updated_metadata = vec['metadata'].copy()
                    updated_metadata.update({
                        'content_type': structured_metadata.get('content_type', 'none'),
                        'difficulty': structured_metadata.get('difficulty', 'none'),
                        'primary_category': structured_metadata.get('primary_category', 'none'),
                        'types_discussed': structured_metadata.get('types_discussed', []),
                        'functions_covered': structured_metadata.get('functions_covered', []),
                        'relationship_type': structured_metadata.get('relationship_type', 'none'),
                        'quadra': structured_metadata.get('quadra', 'none'),
                        'temple': structured_metadata.get('temple', 'none'),
                        'topics': structured_metadata.get('topics', []),
                        'use_case': structured_metadata.get('use_case', [])
                    })
                    
                    vectors_to_update.append({
                        'id': vec['id'],
                        'values': vec['values'],
                        'metadata': updated_metadata
                    })
                
                # Batch upsert to Pinecone
                if vectors_to_update:
                    batch_size = 50
                    for i in range(0, len(vectors_to_update), batch_size):
                        batch = vectors_to_update[i:i + batch_size]
                        pinecone_index.upsert(vectors=batch)
                    
                    updated_vectors += len(vectors_to_update)
                    print(f"   ✅ Updated {len(vectors_to_update)} chunks in Pinecone")
                
            except Exception as e:
                failed += 1
                error_msg = f"Document {doc_id} ({filename}): {str(e)}"
                errors.append(error_msg)
                print(f"   ❌ Error: {str(e)}")
                print(f"   ⏭️ Skipping to next document...")
                continue
        
        # Summary
        print("\n" + "="*60)
        print("✅ BATCH RE-TAGGING COMPLETE")
        print("="*60)
        print(f"📊 Summary:")
        print(f"   Total documents: {total_documents}")
        print(f"   Successfully processed: {processed - failed}")
        print(f"   Failed: {failed}")
        print(f"   Total vectors updated: {updated_vectors}")
        print("="*60 + "\n")
        
        return {
            "message": "Batch re-tagging completed successfully!",
            "total_documents": total_documents,
            "documents_processed": processed - failed,
            "documents_failed": failed,
            "total_vectors_updated": updated_vectors,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR in batch re-tagging: {str(e)}")
        return JSONResponse(status_code=500, content={
            "error": f"Batch re-tagging failed: {str(e)}"
        })


# === Claude Chat Endpoints ===
from claude_api import PROJECTS, chat_with_claude, chat_with_claude_streaming

@app.get("/claude/projects")
async def get_projects():
    """Get all project categories"""
    return {"projects": PROJECTS}

@app.post("/claude/conversations")
async def create_conversation(request: Request):
    """Create a new conversation in a project"""
    try:
        data = await request.json()
        project = data.get("project")
        name = data.get("name", "New Conversation")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO conversations (project, name) 
            VALUES (%s, %s) 
            RETURNING id, project, name, created_at, updated_at
        """, (project, name))
        
        conversation = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return dict(conversation)
    except Exception as e:
        print(f"❌ Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/claude/conversations/search")
async def search_conversations(q: str = ""):
    """Search conversations by title AND message content - Phase 5"""
    try:
        if not q or len(q.strip()) == 0:
            return {"conversations": []}
        
        conn = get_db_connection()
        if not conn:
            return {"conversations": []}
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        search_pattern = f"%{q.lower()}%"
        
        # Search in both conversation titles AND message content
        cursor.execute("""
            SELECT DISTINCT c.id, c.project, c.name, c.created_at, c.updated_at, c.has_unread_response
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE 
                LOWER(c.name) LIKE %s
                OR LOWER(m.content) LIKE %s
            ORDER BY c.updated_at DESC
            LIMIT 100
        """, (search_pattern, search_pattern))
        
        conversations = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {"conversations": [dict(c) for c in conversations]}
    except Exception as e:
        print(f"❌ Error searching conversations: {str(e)}", flush=True)
        return {"conversations": []}

@app.get("/claude/conversations/{project}")
async def get_conversations(project: str):
    """Get all conversations in a project, sorted by most recent"""
    try:
        conn = get_db_connection()
        if not conn:
            return {"conversations": []}
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, project, name, created_at, updated_at, has_unread_response
            FROM conversations
            WHERE project = %s
            ORDER BY updated_at DESC
        """, (project,))
        
        conversations = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {"conversations": [dict(c) for c in conversations]}
    except Exception as e:
        print(f"❌ Error fetching conversations: {str(e)}")
        return {"conversations": []}

@app.get("/claude/conversations/all/list")
async def get_all_conversations():
    """Get all conversations across all projects, sorted by most recent"""
    try:
        conn = get_db_connection()
        if not conn:
            return {"conversations": []}
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, project, name, created_at, updated_at, has_unread_response
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT 100
        """)
        
        conversations = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {"conversations": [dict(c) for c in conversations]}
    except Exception as e:
        print(f"❌ Error fetching all conversations: {str(e)}")
        return {"conversations": []}

@app.get("/claude/conversations/search/test")
async def test_search_connection():
    """Test endpoint to verify database connection and query"""
    try:
        conn = get_db_connection()
        if not conn:
            return {"error": "No database connection"}
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT COUNT(*) as count FROM conversations")
        result = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE LOWER(content) LIKE '%infj%'")
        message_count = cursor.fetchone()
        
        cursor.execute("""
            SELECT DISTINCT c.id, c.name 
            FROM conversations c 
            LEFT JOIN messages m ON m.conversation_id = c.id 
            WHERE LOWER(c.name) LIKE '%infj%' OR LOWER(m.content) LIKE '%infj%'
            LIMIT 5
        """)
        test_results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "total_conversations": result['count'] if result else 0,
            "infj_messages": message_count['count'] if message_count else 0,
            "sample_results": [dict(r) for r in test_results]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/claude/conversations/detail/{conversation_id}")
async def get_conversation_detail(conversation_id: int):
    """Get conversation with all messages"""
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, project, name, created_at, updated_at
            FROM conversations
            WHERE id = %s
        """, (conversation_id,))
        conversation = cursor.fetchone()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        cursor.execute("""
            SELECT id, role, content, created_at, status, follow_up_question
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """, (conversation_id,))
        messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "conversation": dict(conversation),
            "messages": [dict(m) for m in messages]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching conversation detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/claude/conversations/{conversation_id}/message")
async def send_message(conversation_id: int, request: Request):
    """Send a message and get Claude's response"""
    try:
        data = await request.json()
        user_message = data.get("message")
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (%s, 'user', %s)
            RETURNING id, role, content, created_at
        """, (conversation_id, user_message))
        user_msg = cursor.fetchone()
        conn.commit()
        
        cursor.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """, (conversation_id,))
        message_history = cursor.fetchall()
        
        claude_messages = []
        for msg in message_history:
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        assistant_response, tool_details, follow_up_question = chat_with_claude(claude_messages, conversation_id)
        
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, follow_up_question)
            VALUES (%s, 'assistant', %s, %s)
            RETURNING id, role, content, created_at, follow_up_question
        """, (conversation_id, assistant_response, follow_up_question))
        assistant_msg = cursor.fetchone()
        
        cursor.execute("""
            UPDATE conversations
            SET updated_at = NOW()
            WHERE id = %s
        """, (conversation_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "user_message": dict(user_msg),
            "assistant_message": dict(assistant_msg),
            "tool_use": tool_details
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/claude/conversations/{conversation_id}/message/stream")
async def send_message_streaming(conversation_id: int, request: Request):
    """Send a message and get Claude's STREAMING response in real-time (with multi-image vision support)"""
    try:
        data = await request.json()
        user_message = data.get("message")
        image_data = data.get("image")  # Single image (backward compat)
        images_data = data.get("images")  # Multiple images array
        
        # Support both single image and multiple images
        if images_data:
            all_images = images_data
        elif image_data:
            all_images = [image_data]
        else:
            all_images = None
        
        if not user_message and not all_images:
            raise HTTPException(status_code=400, detail="Message or image is required")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Save user message (store text, image(s) will be passed separately)
        image_count = len(all_images) if all_images else 0
        display_text = user_message or (f"[{image_count} image{'s' if image_count > 1 else ''} uploaded]" if image_count > 0 else "")
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (%s, 'user', %s)
            RETURNING id
        """, (conversation_id, display_text))
        conn.commit()
        
        # Get message history
        cursor.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """, (conversation_id,))
        message_history = cursor.fetchall()
        cursor.close()
        conn.close()  # Close connection NOW - generator will create its own
        
        claude_messages = []
        for msg in message_history[:-1]:  # All except the last one (which we'll add with image(s) if present)
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add the latest user message with image(s) if present
        if all_images:
            # Build content array with all images + text
            content_array = []
            
            # Add all images first
            for img_data in all_images:
                # Extract base64 data (remove data:image/...;base64, prefix if present)
                if ',' in img_data:
                    media_type_prefix = img_data.split(',')[0]
                    base64_data = img_data.split(',')[1]
                    # Extract media type (e.g., "image/jpeg")
                    media_type = media_type_prefix.split(';')[0].split(':')[1] if ':' in media_type_prefix else "image/jpeg"
                else:
                    base64_data = img_data
                    media_type = "image/jpeg"
                
                content_array.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_data
                    }
                })
            
            # Add text message after images
            content_array.append({
                "type": "text",
                "text": user_message or "Analyze these images for MBTI cognitive functions being used."
            })
            
            # Claude vision format: content array with multiple images and text
            claude_messages.append({
                "role": "user",
                "content": content_array
            })
        else:
            # Text-only message
            claude_messages.append({
                "role": "user",
                "content": user_message
            })
        
        # Create generator for streaming
        def generate():
            import json  # Import at function scope to avoid scoping issues
            full_response = []
            follow_up_question = None
            
            try:
                for chunk in chat_with_claude_streaming(claude_messages, conversation_id):
                    yield chunk
                    
                    # Collect text chunks and follow-up for database storage
                    if '"chunk"' in chunk:
                        try:
                            chunk_data = json.loads(chunk.replace("data: ", ""))
                            if "chunk" in chunk_data:
                                full_response.append(chunk_data["chunk"])
                        except:
                            pass
                    elif '"done"' in chunk:
                        # Extract follow-up question from done event
                        try:
                            done_data = json.loads(chunk.replace("data: ", ""))
                            if "follow_up" in done_data:
                                follow_up_question = done_data.get("follow_up")
                        except:
                            pass
                
                # Save assistant response to database (need new connection in generator)
                if full_response:
                    assistant_text = "".join(full_response)
                    save_conn = get_db_connection()
                    if save_conn:
                        try:
                            save_cursor = save_conn.cursor()
                            save_cursor.execute("""
                                INSERT INTO messages (conversation_id, role, content, follow_up_question)
                                VALUES (%s, 'assistant', %s, %s)
                            """, (conversation_id, assistant_text, follow_up_question))
                            save_cursor.execute("""
                                UPDATE conversations SET updated_at = NOW() WHERE id = %s
                            """, (conversation_id,))
                            save_conn.commit()
                            save_cursor.close()
                        except Exception as db_error:
                            print(f"❌ Error saving response to database: {str(db_error)}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            save_conn.close()
            except Exception as e:
                print(f"❌ Error in streaming generator: {str(e)}")
                import traceback
                traceback.print_exc()
                yield f'data: {{"error": "{str(e)}"}}\n\n'
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error streaming message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def process_message_background(conversation_id: int, user_message: str, assistant_message_id: int, image_data: str = None, job_id: int = None):
    """Background task to process Claude response (with vision support and job tracking)"""
    job_service = BackgroundJobService() if job_id else None
    
    try:
        print(f"🔄 [BACKGROUND] Processing message for conversation {conversation_id}, job_id={job_id}")
        
        # Update job status to processing
        if job_service and job_id:
            job_service.update_job_status(job_id, 'processing')
        
        # Get message history
        conn = get_db_connection()
        if not conn:
            print(f"❌ [BACKGROUND] Database unavailable")
            return
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = %s AND status != 'processing'
            ORDER BY created_at ASC
        """, (conversation_id,))
        message_history = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Build Claude messages
        claude_messages = []
        for msg in message_history:
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message with image if present
        if image_data:
            # Extract base64 data (remove data:image/...;base64, prefix if present)
            if ',' in image_data:
                media_type_prefix = image_data.split(',')[0]
                base64_data = image_data.split(',')[1]
                # Extract media type (e.g., "image/jpeg")
                media_type = media_type_prefix.split(';')[0].split(':')[1] if ':' in media_type_prefix else "image/jpeg"
            else:
                base64_data = image_data
                media_type = "image/jpeg"
            
            # Claude vision format
            claude_messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_data
                        }
                    },
                    {
                        "type": "text",
                        "text": user_message or "Analyze this image for MBTI cognitive functions being used."
                    }
                ]
            })
        else:
            # Text-only message
            claude_messages.append({
                "role": "user",
                "content": user_message
            })
        
        # Get response from Claude
        print(f"🤖 [BACKGROUND] Calling Claude API...")
        assistant_response, tool_details, follow_up_question = chat_with_claude(claude_messages, conversation_id)
        print(f"✅ [BACKGROUND] Claude response received: {len(assistant_response)} chars")
        
        # Update assistant message with response
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE messages
                    SET content = %s, status = 'completed', updated_at = NOW(), follow_up_question = %s
                    WHERE id = %s
                """, (assistant_response, follow_up_question, assistant_message_id))
                
                # Mark conversation as having unread response
                cursor.execute("""
                    UPDATE conversations
                    SET has_unread_response = TRUE, updated_at = NOW()
                    WHERE id = %s
                """, (conversation_id,))
                
                conn.commit()
                cursor.close()
                print(f"✅ [BACKGROUND] Message {assistant_message_id} marked as completed")
                
                # Mark job as completed
                if job_service and job_id:
                    job_service.complete_job(job_id, assistant_response)
                    print(f"✅ [BACKGROUND] Job {job_id} marked as completed")
                    
            except Exception as db_error:
                print(f"❌ [BACKGROUND] Database error: {str(db_error)}")
                import traceback
                traceback.print_exc()
            finally:
                conn.close()
                
    except Exception as e:
        print(f"❌ [BACKGROUND] Error processing message: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Mark message as error
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE messages
                    SET status = 'error', content = %s, updated_at = NOW()
                    WHERE id = %s
                """, (f"Error: {str(e)}", assistant_message_id))
                conn.commit()
                cursor.close()
            except:
                pass
            finally:
                conn.close()
        
        # Mark job as failed
        if job_service and job_id:
            job_service.complete_job(job_id, f"Error: {str(e)}", error_message=str(e))
            print(f"❌ [BACKGROUND] Job {job_id} marked as failed")


@app.post("/claude/conversations/{conversation_id}/message/background")
async def send_message_background(conversation_id: int, request: Request, background_tasks: BackgroundTasks):
    """Send a message and process Claude's response in the background (with vision support)"""
    try:
        data = await request.json()
        user_message = data.get("message")
        image_data = data.get("image")  # base64 image data
        
        if not user_message and not image_data:
            raise HTTPException(status_code=400, detail="Message or image is required")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if there's already a processing message for this conversation
        cursor.execute("""
            SELECT id FROM messages
            WHERE conversation_id = %s AND status = 'processing' AND role = 'assistant'
            LIMIT 1
        """, (conversation_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=409, detail="A message is already being processed for this conversation")
        
        # Save user message
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, status)
            VALUES (%s, 'user', %s, 'completed')
            RETURNING id, role, content, created_at, status
        """, (conversation_id, user_message or "[Image uploaded]"))
        user_msg = cursor.fetchone()
        
        # Create placeholder assistant message with status='processing'
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, status)
            VALUES (%s, 'assistant', '', 'processing')
            RETURNING id, role, content, created_at, status
        """, (conversation_id,))
        assistant_msg = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Create background job record
        job_service = BackgroundJobService()
        job_id = job_service.create_job(
            job_type='main_chat',
            conversation_id=conversation_id,
            request_payload={
                'message': user_message,
                'image_data': image_data if image_data else None,
                'assistant_message_id': assistant_msg['id']
            }
        )
        
        # Enqueue background task (pass image data and job_id)
        background_tasks.add_task(
            process_message_background,
            conversation_id,
            user_message,
            assistant_msg['id'],
            image_data,
            job_id
        )
        
        print(f"✅ Background task enqueued for conversation {conversation_id}, message {assistant_msg['id']}, job {job_id}")
        
        return {
            "user_message": dict(user_msg),
            "assistant_message": dict(assistant_msg),
            "status": "processing",
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error sending background message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/claude/conversations/{conversation_id}/status")
async def get_conversation_status(conversation_id: int):
    """Get conversation status including pending messages and unread responses"""
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get conversation info
        cursor.execute("""
            SELECT id, project, name, has_unread_response, updated_at
            FROM conversations
            WHERE id = %s
        """, (conversation_id,))
        conversation = cursor.fetchone()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get pending/processing messages
        cursor.execute("""
            SELECT id, role, content, status, created_at, updated_at
            FROM messages
            WHERE conversation_id = %s AND status = 'processing'
            ORDER BY created_at DESC
        """, (conversation_id,))
        pending_messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "conversation": dict(conversation),
            "has_unread": conversation['has_unread_response'],
            "pending_messages": [dict(m) for m in pending_messages],
            "status": "processing" if pending_messages else "ready"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting conversation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/claude/conversations/{conversation_id}/mark-read")
async def mark_conversation_read(conversation_id: int):
    """Mark conversation as read (clear unread response flag)"""
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conversations
            SET has_unread_response = FALSE
            WHERE id = %s
        """, (conversation_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"success": True}
        
    except Exception as e:
        print(f"❌ Error marking conversation read: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/claude/conversations/{conversation_id}/rename")
async def rename_conversation(conversation_id: int, request: Request):
    """Rename a conversation"""
    try:
        data = await request.json()
        new_name = data.get("name")
        
        if not new_name:
            raise HTTPException(status_code=400, detail="Name is required")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            UPDATE conversations
            SET name = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, project, name, created_at, updated_at
        """, (new_name, conversation_id))
        
        conversation = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return dict(conversation)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error renaming conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/claude/conversations/{conversation_id}/move")
async def move_conversation_to_project(conversation_id: int, request: Request):
    """Move a conversation to a different project"""
    try:
        data = await request.json()
        new_project = data.get("project")
        
        if not new_project:
            raise HTTPException(status_code=400, detail="Project is required")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            UPDATE conversations
            SET project = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, project, name, created_at, updated_at
        """, (new_project, conversation_id))
        
        conversation = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return dict(conversation)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error moving conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/claude/messages/{message_id}")
async def delete_message(message_id: int):
    """Delete a single message from a conversation"""
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {"message": "Message deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/claude/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """Delete a conversation and all its messages"""
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        print(f"❌ Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/claude/conversations/{conversation_id}/move")
async def move_conversation(conversation_id: int, request: Request):
    """Move a conversation to a different project"""
    try:
        data = await request.json()
        new_project = data.get("project")
        
        if not new_project:
            raise HTTPException(status_code=400, detail="Project is required")
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database unavailable")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            UPDATE conversations
            SET project = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, project, name, created_at, updated_at
        """, (new_project, conversation_id))
        
        conversation = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return dict(conversation)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error moving conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/claude/search")
async def search_all_content(q: str = ""):
    """Search across all conversations and messages"""
    try:
        if not q:
            return {"results": []}
        
        conn = get_db_connection()
        if not conn:
            return {"results": []}
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT DISTINCT c.id, c.project, c.name, c.updated_at,
                   m.content as preview
            FROM conversations c
            JOIN messages m ON m.conversation_id = c.id
            WHERE c.name ILIKE %s OR m.content ILIKE %s
            ORDER BY c.updated_at DESC
            LIMIT 20
        """, (f"%{q}%", f"%{q}%"))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {"results": [dict(r) for r in results]}
    except Exception as e:
        print(f"❌ Error searching: {str(e)}")
        return {"results": []}


# === Migration API Endpoints ===
migration_status = {
    "running": False,
    "completed": 0,
    "failed": 0,
    "total_docs": 245,
    "total_new_chunks": 0,
    "start_time": None,
    "end_time": None,
    "current_file": ""
}

@app.get("/api/migration-status")
async def get_migration_status():
    """Get current migration status"""
    return migration_status

@app.post("/api/start-migration")
async def start_migration_api(background_tasks: BackgroundTasks):
    """Start the embedding migration process in background"""
    global migration_status
    
    if migration_status["running"]:
        return {"error": "Migration already running"}
    
    # Import migration functions
    import migrate_embeddings as mig
    
    async def run_migration():
        global migration_status
        migration_status["running"] = True
        migration_status["start_time"] = datetime.now().isoformat()
        migration_status["completed"] = 0
        migration_status["failed"] = 0
        migration_status["total_new_chunks"] = 0
        migration_status["error"] = None
        
        try:
            print("🚀 Starting migration process...")
            
            # Step 1: Fetch documents from old index
            try:
                documents = mig.fetch_all_documents_from_old_index()
                migration_status["total_docs"] = len(documents)
            except Exception as e:
                error_msg = f"Failed to fetch documents from old index: {str(e)}"
                print(f"❌ {error_msg}")
                migration_status["error"] = error_msg
                migration_status["running"] = False
                migration_status["end_time"] = datetime.now().isoformat()
                return
            
            # Step 2: Migrate documents
            for i, doc in enumerate(documents, 1):
                try:
                    migration_status["current_file"] = doc['filename']
                    
                    # Re-chunk
                    new_chunks = mig.chunk_text_improved(doc['text'])
                    
                    # Re-embed and upload
                    enriched_meta = mig.extract_enriched_metadata(doc['filename'], doc['text'][:2000])
                    
                    openai.api_key = OPENAI_API_KEY
                    pc = Pinecone(api_key=PINECONE_API_KEY)
                    new_index_name = os.getenv("NEW_PINECONE_INDEX", "mbti-knowledge-v2")
                    new_index = pc.Index(new_index_name)
                    
                    vectors_to_upsert = []
                    for chunk_idx, chunk in enumerate(new_chunks):
                        response = openai.embeddings.create(
                            input=chunk,
                            model="text-embedding-3-large"
                        )
                        vector = response.data[0].embedding
                        
                        chunk_metadata = {
                            "text": chunk,
                            "doc_id": doc['doc_id'],
                            "filename": doc['filename'],
                            "upload_timestamp": doc['upload_timestamp'],
                            "tags": doc['tags'],
                            "chunk_index": chunk_idx,
                            "source": doc.get('source', 'migration'),
                            "migration_date": datetime.now().isoformat()
                        }
                        chunk_metadata.update(enriched_meta)
                        
                        vectors_to_upsert.append((f"{doc['doc_id']}-{chunk_idx}", vector, chunk_metadata))
                    
                    # Upload in batches
                    batch_size = 50
                    for batch_start in range(0, len(vectors_to_upsert), batch_size):
                        batch = vectors_to_upsert[batch_start:batch_start + batch_size]
                        new_index.upsert(vectors=batch)
                    
                    migration_status["completed"] += 1
                    migration_status["total_new_chunks"] += len(new_chunks)
                    
                    print(f"✅ Migrated {i}/{len(documents)}: {doc['filename']}")
                    
                except Exception as e:
                    print(f"❌ Error migrating {doc['filename']}: {str(e)}")
                    migration_status["failed"] += 1
            
            migration_status["end_time"] = datetime.now().isoformat()
            migration_status["running"] = False
            print(f"🎉 Migration complete! {migration_status['completed']}/{migration_status['total_docs']}")
            
        except Exception as e:
            error_msg = f"Migration error: {str(e)}"
            print(f"❌ {error_msg}")
            migration_status["error"] = error_msg
            migration_status["running"] = False
            migration_status["end_time"] = datetime.now().isoformat()
    
    background_tasks.add_task(run_migration)
    return {"message": "Migration started", "status": migration_status}


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


# === Content Atlas API ===
@app.get("/api/content-atlas/filters")
async def get_content_atlas_filters():
    """
    Get all available filter values from Pinecone metadata.
    Used to populate filter sidebar options.
    """
    try:
        pinecone_index = get_pinecone_client()
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"}
            )
        
        print("\n🔍 Fetching available filters from Pinecone...")
        
        # Query all vectors to collect unique metadata values
        dummy_vector = [0.0] * 3072
        query_response = pinecone_index.query(
            vector=dummy_vector,
            top_k=10000,
            include_metadata=True
        )
        
        matches = query_response.matches if hasattr(query_response, 'matches') else query_response.get('matches', [])
        
        # Collect unique values for each filter field
        content_types = set()
        difficulties = set()
        primary_categories = set()
        types_discussed = set()
        functions_covered = set()
        relationship_types = set()
        quadras = set()
        temples = set()
        topics = set()
        use_cases = set()
        
        for match in matches:
            try:
                metadata = match.metadata if hasattr(match, 'metadata') else match.get('metadata', {})
                
                # Collect single-value fields
                if metadata.get("content_type") and metadata.get("content_type") != "unknown":
                    content_types.add(metadata.get("content_type"))
                if metadata.get("difficulty") and metadata.get("difficulty") != "unknown":
                    difficulties.add(metadata.get("difficulty"))
                if metadata.get("primary_category") and metadata.get("primary_category") != "unknown":
                    primary_categories.add(metadata.get("primary_category"))
                if metadata.get("relationship_type") and metadata.get("relationship_type") not in ["n/a", "unknown"]:
                    relationship_types.add(metadata.get("relationship_type"))
                if metadata.get("quadra") and metadata.get("quadra") != "unknown":
                    quadras.add(metadata.get("quadra"))
                if metadata.get("temple") and metadata.get("temple") != "unknown":
                    temples.add(metadata.get("temple"))
                
                # Collect array fields
                for t in metadata.get("types_discussed", []):
                    if t and t != "unknown":
                        types_discussed.add(t)
                for f in metadata.get("functions_covered", []):
                    if f and f != "unknown":
                        functions_covered.add(f)
                for topic in metadata.get("topics", []):
                    if topic and topic != "unknown":
                        topics.add(topic)
                for uc in metadata.get("use_case", []):
                    if uc and uc != "unknown":
                        use_cases.add(uc)
                        
            except Exception as e:
                continue
        
        # Convert to sorted lists
        filters = {
            "content_types": sorted(list(content_types)),
            "difficulties": sorted(list(difficulties)),
            "primary_categories": sorted(list(primary_categories)),
            "types_discussed": sorted(list(types_discussed)),
            "functions_covered": sorted(list(functions_covered)),
            "relationship_types": sorted(list(relationship_types)),
            "quadras": sorted(list(quadras)),
            "temples": sorted(list(temples)),
            "topics": sorted(list(topics))[:50],  # Limit topics to top 50
            "use_cases": sorted(list(use_cases))
        }
        
        print(f"✅ Filters collected: {sum(len(v) for v in filters.values())} total options")
        
        return filters
        
    except Exception as e:
        print(f"❌ Error fetching filters: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/content-atlas")
async def get_content_atlas(
    page: int = 1,
    limit: int = 12,
    search: str = None,
    filters: str = None
):
    """
    Get paginated documents with full structured metadata for Content Atlas visualization.
    
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 12, max: 100)
    - search: Optional search term (matches title, topics, types)
    - filters: Optional JSON filters object (e.g., {"content_type":["lecture"],"types_discussed":["ENFP"]})
    """
    try:
        # Validate parameters
        if page < 1:
            return JSONResponse(
                status_code=400,
                content={"error": "Page must be >= 1"}
            )
        
        if limit < 1 or limit > 100:
            return JSONResponse(
                status_code=400,
                content={"error": "Limit must be between 1 and 100"}
            )
        
        # Get Pinecone client
        pinecone_index = get_pinecone_client()
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"}
            )
        
        print(f"\n📊 Content Atlas query: page={page}, limit={limit}, search={search}, filters={filters}")
        
        # Query Pinecone for all vectors (use dummy vector to get all)
        # Note: Pinecone max top_k is 10,000
        dummy_vector = [0.0] * 3072  # text-embedding-3-large dimension
        
        try:
            query_response = pinecone_index.query(
                vector=dummy_vector,
                top_k=10000,  # Get as many as possible
                include_metadata=True
            )
        except Exception as pinecone_error:
            print(f"❌ Pinecone query error: {str(pinecone_error)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Pinecone query failed: {str(pinecone_error)}"}
            )
        
        # Extract matches
        try:
            matches = query_response.matches if hasattr(query_response, 'matches') else query_response.get('matches', [])
        except Exception:
            matches = []
        
        if not matches:
            return {
                "documents": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_documents": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False
                }
            }
        
        # Group by doc_id to get unique documents
        documents_map = {}
        
        for match in matches:
            try:
                metadata = match.metadata if hasattr(match, 'metadata') else match.get('metadata', {})
                doc_id = metadata.get('doc_id') or metadata.get('document_id')
                
                if not doc_id or doc_id in documents_map:
                    continue
                
                # Extract structured metadata (10 fields)
                structured_metadata = {
                    "content_type": metadata.get("content_type", "unknown"),
                    "difficulty": metadata.get("difficulty", "unknown"),
                    "primary_category": metadata.get("primary_category", "unknown"),
                    "types_discussed": metadata.get("types_discussed", []),
                    "functions_covered": metadata.get("functions_covered", []),
                    "relationship_type": metadata.get("relationship_type", "n/a"),
                    "quadra": metadata.get("quadra", "unknown"),
                    "temple": metadata.get("temple", "unknown"),
                    "topics": metadata.get("topics", []),
                    "use_case": metadata.get("use_case", [])
                }
                
                # Build document object
                doc = {
                    "id": doc_id,
                    "title": metadata.get("filename", "Untitled"),
                    "metadata": structured_metadata,
                    "upload_date": metadata.get("upload_date", "unknown")
                }
                
                documents_map[doc_id] = doc
                
            except Exception as e:
                print(f"⚠️ Error processing match: {str(e)}")
                continue
        
        # Convert to list
        all_documents = list(documents_map.values())
        
        # Apply search filter if provided
        if search and search.strip():
            search_term = search.lower().strip()
            filtered_docs = []
            
            for doc in all_documents:
                # Search in title
                if search_term in doc["title"].lower():
                    filtered_docs.append(doc)
                    continue
                
                # Search in topics
                topics = doc["metadata"].get("topics", [])
                if isinstance(topics, list) and any(search_term in str(topic).lower() for topic in topics):
                    filtered_docs.append(doc)
                    continue
                
                # Search in types_discussed
                types = doc["metadata"].get("types_discussed", [])
                if isinstance(types, list) and any(search_term in str(t).lower() for t in types):
                    filtered_docs.append(doc)
                    continue
            
            all_documents = filtered_docs
        
        # Apply filters if provided
        if filters and filters.strip():
            try:
                import json
                filters_dict = json.loads(filters)
                print(f"🔍 Applying filters: {filters_dict}")
                
                filtered_docs = []
                for doc in all_documents:
                    match = True
                    metadata = doc["metadata"]
                    
                    # Apply each filter (AND logic within same field, OR across fields)
                    # If a filter field has values, the document must match at least one value in that field
                    
                    # Content Type filter
                    if filters_dict.get("content_type") and len(filters_dict["content_type"]) > 0:
                        if metadata.get("content_type") not in filters_dict["content_type"]:
                            match = False
                    
                    # Difficulty filter
                    if match and filters_dict.get("difficulty") and len(filters_dict["difficulty"]) > 0:
                        if metadata.get("difficulty") not in filters_dict["difficulty"]:
                            match = False
                    
                    # Primary Category filter
                    if match and filters_dict.get("primary_category") and len(filters_dict["primary_category"]) > 0:
                        if metadata.get("primary_category") not in filters_dict["primary_category"]:
                            match = False
                    
                    # Relationship Type filter
                    if match and filters_dict.get("relationship_type") and len(filters_dict["relationship_type"]) > 0:
                        if metadata.get("relationship_type") not in filters_dict["relationship_type"]:
                            match = False
                    
                    # Quadra filter
                    if match and filters_dict.get("quadra") and len(filters_dict["quadra"]) > 0:
                        if metadata.get("quadra") not in filters_dict["quadra"]:
                            match = False
                    
                    # Temple filter
                    if match and filters_dict.get("temple") and len(filters_dict["temple"]) > 0:
                        if metadata.get("temple") not in filters_dict["temple"]:
                            match = False
                    
                    # Types Discussed filter (array field - check if ANY selected type is in document)
                    if match and filters_dict.get("types_discussed") and len(filters_dict["types_discussed"]) > 0:
                        doc_types = metadata.get("types_discussed", [])
                        if not any(t in filters_dict["types_discussed"] for t in doc_types):
                            match = False
                    
                    # Functions Covered filter (array field)
                    if match and filters_dict.get("functions_covered") and len(filters_dict["functions_covered"]) > 0:
                        doc_functions = metadata.get("functions_covered", [])
                        if not any(f in filters_dict["functions_covered"] for f in doc_functions):
                            match = False
                    
                    # Topics filter (array field)
                    if match and filters_dict.get("topics") and len(filters_dict["topics"]) > 0:
                        doc_topics = metadata.get("topics", [])
                        if not any(topic in filters_dict["topics"] for topic in doc_topics):
                            match = False
                    
                    # Use Case filter (array field)
                    if match and filters_dict.get("use_case") and len(filters_dict["use_case"]) > 0:
                        doc_use_cases = metadata.get("use_case", [])
                        if not any(uc in filters_dict["use_case"] for uc in doc_use_cases):
                            match = False
                    
                    if match:
                        filtered_docs.append(doc)
                
                all_documents = filtered_docs
                print(f"✅ Filters applied: {len(all_documents)} documents match")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Invalid filters JSON: {str(e)}")
                # Continue without filtering on invalid JSON
        
        # Sort by upload_date DESC (most recent first)
        # Handle unknown dates by putting them last
        def sort_key(doc):
            date_str = doc.get("upload_date", "unknown")
            if date_str == "unknown":
                return "0000-00-00"  # Sort to end
            return date_str
        
        all_documents.sort(key=sort_key, reverse=True)
        
        # Calculate pagination
        total_documents = len(all_documents)
        total_pages = (total_documents + limit - 1) // limit if total_documents > 0 else 0
        
        # Get page slice
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_documents = all_documents[start_idx:end_idx]
        
        # Build response
        response = {
            "documents": page_documents,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_documents": total_documents,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }
        
        print(f"✅ Returning {len(page_documents)} documents (page {page}/{total_pages})")
        
        return response
        
    except Exception as e:
        print(f"❌ Content Atlas API error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )


@app.get("/api/content-atlas/analytics")
async def get_content_atlas_analytics():
    """
    Get aggregated analytics from all documents in Content Atlas.
    
    Returns statistics on:
    - Total documents
    - Distribution by content type
    - Distribution by difficulty
    - Distribution by quadra
    - Top 10 MBTI types
    - Top 10 cognitive functions
    - Top 15 topics
    """
    try:
        # Get Pinecone client
        pinecone_index = get_pinecone_client()
        if not pinecone_index:
            return JSONResponse(
                status_code=500,
                content={"error": "Pinecone client not initialized"}
            )
        
        print("\n📊 Fetching Content Atlas analytics...")
        
        # Query Pinecone for all vectors
        dummy_vector = [0.0] * 3072  # text-embedding-3-large dimension
        
        try:
            query_response = pinecone_index.query(
                vector=dummy_vector,
                top_k=10000,
                include_metadata=True
            )
        except Exception as pinecone_error:
            print(f"❌ Pinecone query error: {str(pinecone_error)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Pinecone query failed: {str(pinecone_error)}"}
            )
        
        # Extract matches
        try:
            matches = query_response.matches if hasattr(query_response, 'matches') else query_response.get('matches', [])
        except Exception:
            matches = []
        
        if not matches:
            return {
                "total_documents": 0,
                "by_content_type": {},
                "by_difficulty": {},
                "by_quadra": {},
                "top_types": [],
                "top_functions": [],
                "top_topics": []
            }
        
        # Group by doc_id to get unique documents
        documents_map = {}
        
        for match in matches:
            try:
                metadata = match.metadata if hasattr(match, 'metadata') else match.get('metadata', {})
                doc_id = metadata.get('doc_id') or metadata.get('document_id')
                
                if not doc_id or doc_id in documents_map:
                    continue
                
                # Store full metadata for aggregation
                documents_map[doc_id] = metadata
            except Exception as match_error:
                continue
        
        # Initialize counters
        from collections import Counter
        
        content_type_counts = Counter()
        difficulty_counts = Counter()
        quadra_counts = Counter()
        type_counts = Counter()
        function_counts = Counter()
        topic_counts = Counter()
        
        # Aggregate data from unique documents
        for doc_id, metadata in documents_map.items():
            # Content type
            content_type = metadata.get("content_type", "unknown")
            content_type_counts[content_type] += 1
            
            # Difficulty
            difficulty = metadata.get("difficulty", "unknown")
            difficulty_counts[difficulty] += 1
            
            # Quadra
            quadra = metadata.get("quadra", "unknown")
            if quadra and quadra != "unknown" and quadra != "n/a":
                quadra_counts[quadra] += 1
            
            # Types discussed (can be list or string)
            types_discussed = metadata.get("types_discussed", [])
            if isinstance(types_discussed, str):
                types_discussed = [types_discussed]
            elif not isinstance(types_discussed, list):
                types_discussed = []
            
            for mbti_type in types_discussed:
                if mbti_type and mbti_type != "n/a":
                    type_counts[mbti_type] += 1
            
            # Functions covered (can be list or string)
            functions_covered = metadata.get("functions_covered", [])
            if isinstance(functions_covered, str):
                functions_covered = [functions_covered]
            elif not isinstance(functions_covered, list):
                functions_covered = []
            
            for func in functions_covered:
                if func and func != "n/a":
                    function_counts[func] += 1
            
            # Topics (can be list or string)
            topics = metadata.get("topics", [])
            if isinstance(topics, str):
                topics = [topics]
            elif not isinstance(topics, list):
                topics = []
            
            for topic in topics:
                if topic and topic != "n/a":
                    topic_counts[topic] += 1
        
        # Build response
        total_documents = len(documents_map)
        
        analytics = {
            "total_documents": total_documents,
            "by_content_type": dict(content_type_counts),
            "by_difficulty": dict(difficulty_counts),
            "by_quadra": dict(quadra_counts),
            "top_types": [
                {"type": mbti_type, "count": count}
                for mbti_type, count in type_counts.most_common(10)
            ],
            "top_functions": [
                {"function": func, "count": count}
                for func, count in function_counts.most_common(10)
            ],
            "top_topics": [
                {"topic": topic, "count": count}
                for topic, count in topic_counts.most_common(15)
            ]
        }
        
        print(f"✅ Analytics aggregated: {total_documents} total documents")
        print(f"   Content Types: {len(content_type_counts)}")
        print(f"   Difficulties: {len(difficulty_counts)}")
        print(f"   Quadras: {len(quadra_counts)}")
        print(f"   Top Types: {len(type_counts)}")
        print(f"   Top Functions: {len(function_counts)}")
        print(f"   Top Topics: {len(topic_counts)}")
        
        return analytics
        
    except Exception as e:
        print(f"❌ Analytics API error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )


# === Knowledge Graph API Endpoints ===

# Initialize Knowledge Graph Manager
from src.services.knowledge_graph_manager import KnowledgeGraphManager
kg_manager = KnowledgeGraphManager()

# Warm the cache at startup to avoid first-request penalty
print("🔥 Warming knowledge graph cache...")
kg_manager.load_graph()
print("✅ Knowledge graph cache warmed")

@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    """
    Get the full knowledge graph (nodes and edges).
    
    Returns:
        JSON object with nodes, edges, and stats
    """
    try:
        print("📊 Fetching knowledge graph...")
        graph = kg_manager.load_graph()
        stats = await kg_manager.get_graph_stats()
        
        response = {
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
            "stats": stats,
            "version": graph.get("version", "1.0"),
            "last_updated": graph.get("last_updated")
        }
        
        print(f"✅ Knowledge graph loaded: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
        return response
        
    except Exception as e:
        print(f"❌ Knowledge graph API error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to load knowledge graph: {str(e)}"}
        )


@app.get("/api/knowledge-graph/stats")
async def get_knowledge_graph_stats():
    """
    Get statistics about the knowledge graph (fast endpoint).
    
    Returns:
        JSON object with stats only
    """
    try:
        stats = await kg_manager.get_graph_stats()
        return stats
        
    except Exception as e:
        print(f"❌ Knowledge graph stats error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get stats: {str(e)}"}
        )


@app.get("/api/knowledge-graph/concept/{concept_id}")
async def get_concept_details(concept_id: str):
    """
    Get details about a specific concept/node including connections.
    
    Args:
        concept_id: The node ID to fetch
        
    Returns:
        JSON object with node data, connected nodes, and related documents
    """
    try:
        print(f"🔍 Fetching concept: {concept_id}")
        
        # Get the node
        node = await kg_manager.get_node_by_id(concept_id)
        
        if not node:
            return JSONResponse(
                status_code=404,
                content={"error": f"Concept '{concept_id}' not found"}
            )
        
        # Get connected nodes
        connected_nodes = await kg_manager.get_connected_nodes(concept_id)
        
        # Get source documents from node
        source_docs = node.get("sources", [])
        
        response = {
            "node": node,
            "connected_nodes": connected_nodes,
            "total_connections": len(connected_nodes),
            "source_documents": source_docs,
            "total_documents": len(source_docs)
        }
        
        print(f"✅ Concept '{concept_id}' retrieved: {len(connected_nodes)} connections")
        return response
        
    except Exception as e:
        print(f"❌ Concept details error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get concept details: {str(e)}"}
        )


@app.post("/api/knowledge-graph/node")
async def create_node(node_data: dict):
    """
    Create a new node in the knowledge graph.
    (For testing - will be called by document processing later)
    
    Request body:
        {
            "label": "Shadow Integration",
            "type": "process",
            "category": "foundational",
            "definition": "...",
            "source_documents": ["doc_1", "doc_2"]
        }
    """
    try:
        node = await kg_manager.add_node(node_data)
        return {
            "success": True,
            "node": node,
            "message": f"Node '{node['label']}' created/updated successfully"
        }
    except Exception as e:
        print(f"❌ Create node error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to create node: {str(e)}"}
        )


@app.post("/api/knowledge-graph/edge")
async def create_edge(edge_data: dict):
    """
    Create a new edge in the knowledge graph.
    (For testing - will be called by document processing later)
    
    Request body:
        {
            "source": "shadow_integration",
            "target": "inferior_function",
            "relationship_type": "requires_understanding",
            "evidence_samples": ["Evidence text from document"],
            "properties": {}
        }
    """
    try:
        edge = await kg_manager.add_edge(edge_data)
        return {
            "success": True,
            "edge": edge,
            "message": f"Edge '{edge['source']} -> {edge['target']}' created/updated successfully"
        }
    except Exception as e:
        print(f"❌ Create edge error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to create edge: {str(e)}"}
        )


# === Concept Extraction API Endpoints ===

from src.services.concept_extractor import extract_concepts, get_extraction_cost_summary

@app.get("/api/extraction-costs/summary")
async def get_extraction_costs():
    """
    Get summary of concept extraction costs and statistics.
    
    Returns:
        JSON with total costs, success rate, token usage
    """
    try:
        summary = await get_extraction_cost_summary()
        return summary
        
    except Exception as e:
        print(f"❌ Failed to get extraction cost summary: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get cost summary: {str(e)}"}
        )


@app.post("/api/extract-concepts")
async def extract_document_concepts(request: dict):
    """
    Extract concepts and relationships from a document using Claude API.
    
    Request body:
        {
            "document_text": "Full document text...",
            "document_id": "doc_123"
        }
        
    Returns:
        Extraction result with concepts, relationships, and metadata
    """
    try:
        document_text = request.get("document_text")
        document_id = request.get("document_id")
        
        if not document_text or not document_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields: document_text, document_id"}
            )
        
        print(f"🔍 Starting concept extraction for: {document_id}")
        
        # Extract concepts
        result = await extract_concepts(document_text, document_id)
        
        if result is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Concept extraction failed - check logs for details"}
            )
        
        return {
            "success": True,
            "document_id": document_id,
            "extraction": result
        }
        
    except Exception as e:
        print(f"❌ Extraction endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Extraction failed: {str(e)}"}
        )


@app.get("/api/batch-progress")
async def get_batch_progress():
    """
    Get current batch processing progress.
    
    Returns:
        Current progress status, documents processed, ETA
    """
    try:
        progress_file = "data/batch-progress.json"
        
        if not os.path.exists(progress_file):
            return {
                "status": "not_started",
                "message": "Batch processing has not been started yet"
            }
        
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        
        return progress
        
    except Exception as e:
        print(f"❌ Failed to get batch progress: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get progress: {str(e)}"}
        )


@app.get("/api/graph-quality-report")
async def get_graph_quality_report():
    """
    Get the knowledge graph quality report.
    
    Returns:
        Quality metrics, distribution stats, health status
    """
    try:
        report_file = "data/graph-quality-report.json"
        
        if not os.path.exists(report_file):
            return {
                "message": "Quality report not yet generated. Run batch processing first."
            }
        
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        return report
        
    except Exception as e:
        print(f"❌ Failed to get quality report: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get quality report: {str(e)}"}
        )


# === Serve Frontend ===
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/health", include_in_schema=False)
def health_check():
    """Health check endpoint for deployments"""
    return {"status": "healthy", "app": "InnerVerse"}

@app.get("/uploader", include_in_schema=False)
def serve_uploader(csrf_protect: CsrfProtect = Depends()):
    """Serve uploader page with CSRF token"""
    # Generate CSRF tokens (correct method name)
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    
    # Read HTML and inject CSRF token
    with open("uploader.html", "r") as f:
        html_content = f.read()
    
    # Inject CSRF token into a meta tag for JavaScript access
    csrf_meta = f'<meta name="csrf-token" content="{csrf_token}">'
    html_content = html_content.replace('</head>', f'{csrf_meta}\n</head>')
    
    # Create response with CSRF cookie
    response = HTMLResponse(
        content=html_content,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    
    return response

@app.get("/privacy", include_in_schema=False)
def serve_privacy():
    return FileResponse("privacy.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.js", include_in_schema=False)
def serve_claude_js():
    return FileResponse("claude-app.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v12.js", include_in_schema=False)
def serve_claude_js_v12():
    return FileResponse("claude-app.v12.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v13.js", include_in_schema=False)
def serve_claude_js_v13():
    return FileResponse("claude-app.v13.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v14.js", include_in_schema=False)
def serve_claude_js_v14():
    return FileResponse("claude-app.v14.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v15.js", include_in_schema=False)
def serve_claude_js_v15():
    return FileResponse("claude-app.v15.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v16.js", include_in_schema=False)
def serve_claude_js_v16():
    return FileResponse("claude-app.v16.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v17.js", include_in_schema=False)
def serve_claude_js_v17():
    return FileResponse("claude-app.v17.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v18.js", include_in_schema=False)
def serve_claude_js_v18():
    return FileResponse("claude-app.v18.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v19.js", include_in_schema=False)
def serve_claude_js_v19():
    return FileResponse("claude-app.v19.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v20.js", include_in_schema=False)
def serve_claude_js_v20():
    return FileResponse("claude-app.v20.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v21.js", include_in_schema=False)
def serve_claude_js_v21():
    return FileResponse("claude-app.v21.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v22.js", include_in_schema=False)
def serve_claude_js_v22():
    return FileResponse("claude-app.v22.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v23.js", include_in_schema=False)
def serve_claude_js_v23():
    return FileResponse("claude-app.v23.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v24.js", include_in_schema=False)
def serve_claude_js_v24():
    return FileResponse("claude-app.v24.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v25.js", include_in_schema=False)
def serve_claude_js_v25():
    return FileResponse("claude-app.v25.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/claude-app.v26.js", include_in_schema=False)
def serve_claude_js_v26():
    return FileResponse("claude-app.v26.js", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/migration", include_in_schema=False)
def serve_migration_dashboard():
    return FileResponse("migration.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/content-atlas", include_in_schema=False)
def serve_content_atlas():
    return FileResponse("content-atlas.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/knowledge-graph", include_in_schema=False)
def serve_knowledge_graph():
    return FileResponse("knowledge-graph.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/learning-paths", include_in_schema=False)
def serve_learning_paths():
    import time
    # Read file and add timestamp to force reload
    with open("static/learning_paths.html", "r") as f:
        html_content = f.read()
    
    return HTMLResponse(
        content=html_content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
            "X-Timestamp": str(int(time.time()))
        }
    )


@app.get("/brain-icon-192.png", include_in_schema=False)
def serve_icon_192():
    return FileResponse("brain-icon-192.png", media_type="image/png")

@app.get("/brain-icon-512.png", include_in_schema=False)
def serve_icon_512():
    return FileResponse("brain-icon-512.png", media_type="image/png")


# === OpenAI-Compatible API for LibreChat Integration ===

@app.get("/v1/models")
async def list_models():
    """
    OpenAI-compatible endpoint to list available models for LibreChat
    """
    return {
        "object": "list",
        "data": [
            {
                "id": "innerverse-claude-sonnet-4",
                "object": "model",
                "created": 1730000000,
                "owned_by": "innerverse",
                "permission": [],
                "root": "innerverse-claude-sonnet-4",
                "parent": None
            }
        ]
    }


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """
    OpenAI-compatible chat completions endpoint for LibreChat integration.
    This wraps the InnerVerse Claude functionality with OpenAI API format.
    """
    try:
        data = await request.json()
        messages = data.get("messages", [])
        stream = data.get("stream", True)
        model = data.get("model", "innerverse-claude-sonnet-4")
        
        if not messages:
            raise HTTPException(status_code=400, detail="Messages are required")
        
        # Convert OpenAI message format to Claude format
        claude_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            # Skip system messages - we have our own system prompt
            if role == "system":
                continue
                
            claude_messages.append({
                "role": "user" if role == "user" else "assistant",
                "content": content
            })
        
        if stream:
            # Streaming response in OpenAI SSE format
            def generate_openai_stream():
                import json  # Import at function scope to avoid scoping issues
                full_response = []
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                
                try:
                    # Use a temporary conversation ID for stateless LibreChat requests
                    temp_conversation_id = 0  # LibreChat doesn't need real conversation tracking
                    
                    for chunk in chat_with_claude_streaming(claude_messages, temp_conversation_id):
                        # Parse InnerVerse chunk format
                        if '"chunk"' in chunk:
                            try:
                                chunk_data = json.loads(chunk.replace("data: ", ""))
                                if "chunk" in chunk_data:
                                    text_chunk = chunk_data["chunk"]
                                    full_response.append(text_chunk)
                                    
                                    # Convert to OpenAI streaming format
                                    openai_chunk = {
                                        "id": chunk_id,
                                        "object": "chat.completion.chunk",
                                        "created": int(datetime.now(timezone.utc).timestamp()),
                                        "model": model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {"content": text_chunk},
                                            "finish_reason": None
                                        }]
                                    }
                                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                            except:
                                pass
                        
                        elif '"done": true' in chunk:
                            # Send final chunk
                            final_chunk = {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": int(datetime.now(timezone.utc).timestamp()),
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop"
                                }]
                            }
                            yield f"data: {json.dumps(final_chunk)}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                        
                        elif '"error"' in chunk:
                            # Pass through errors
                            yield chunk
                            return
                
                except Exception as e:
                    print(f"❌ Error in OpenAI stream generation: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    error_chunk = {
                        "id": chunk_id,
                        "object": "error",
                        "message": str(e)
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
            
            return StreamingResponse(
                generate_openai_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        else:
            # Non-streaming response (fallback)
            full_response = []
            temp_conversation_id = 0
            
            for chunk in chat_with_claude_streaming(claude_messages, temp_conversation_id):
                if '"chunk"' in chunk:
                    try:
                        chunk_data = json.loads(chunk.replace("data: ", ""))
                        if "chunk" in chunk_data:
                            full_response.append(chunk_data["chunk"])
                    except:
                        pass
            
            response_text = "".join(full_response)
            
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in OpenAI-compatible endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LEARNING PATHS API - Course & Lesson Management
# =============================================================================

from src.services.course_manager import CourseManager
from src.services.course_generator import CourseGenerator
from src.services.content_assigner import ContentAssigner

def get_course_manager():
    """Get CourseManager instance"""
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database not configured")
    return CourseManager(DATABASE_URL)

def get_course_generator():
    """Get CourseGenerator instance"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    return CourseGenerator(
        anthropic_api_key=ANTHROPIC_API_KEY,
        knowledge_graph_manager=kg_manager
    )

def get_content_assigner():
    """Get ContentAssigner instance"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database not configured")
    return ContentAssigner(
        anthropic_api_key=ANTHROPIC_API_KEY,
        knowledge_graph_manager=kg_manager,
        course_manager=CourseManager(DATABASE_URL)
    )


@app.post("/api/courses")
async def create_course(request: Request):
    """Create a new learning path course"""
    try:
        data = await request.json()
        manager = get_course_manager()
        
        course = manager.create_course(
            title=data.get("title"),
            category=data.get("category"),
            description=data.get("description"),
            estimated_hours=data.get("estimated_hours", 0),
            auto_generated=data.get("auto_generated", True),
            generation_prompt=data.get("generation_prompt"),
            source_type=data.get("source_type", "manual"),
            source_ids=data.get("source_ids", []),
            tags=data.get("tags", []),
            notes=data.get("notes")
        )
        
        return {"success": True, "course": course}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error creating course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/stats")
async def get_course_stats(user_id: str = "jeralyn"):
    """Get system-wide Learning Paths statistics"""
    try:
        manager = get_course_manager()
        stats = manager.get_stats(user_id=user_id)
        return {"success": True, "stats": stats}
    except Exception as e:
        print(f"❌ Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses")
async def list_courses(category: str = None, status: str = "active"):
    """List all courses, grouped by category"""
    try:
        manager = get_course_manager()
        courses = manager.list_courses(category=category, status=status)
        
        # Group courses by category for frontend tree visualization
        grouped = {}
        for course in courses:
            cat = course.get('category', 'uncategorized')
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(course)
        
        return {"success": True, "data": grouped}
    except Exception as e:
        print(f"❌ Error listing courses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/generation-stats")
async def get_generation_stats():
    """
    Get AI generation statistics for current session.
    
    Returns:
        {
            "success": true,
            "data": {
                "generation_cost": 0.15,
                "assignment_cost": 0.08,
                "total_cost": 0.23
            }
        }
    """
    try:
        generator = get_course_generator()
        assigner = get_content_assigner()
        
        gen_cost = generator.get_total_cost()
        assign_cost = assigner.get_total_cost()
        
        return {
            "success": True,
            "data": {
                "generation_cost": round(gen_cost, 4),
                "assignment_cost": round(assign_cost, 4),
                "total_cost": round(gen_cost + assign_cost, 4)
            }
        }
        
    except Exception as e:
        print(f"❌ Failed to get generation stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/{course_id}")
async def get_course(course_id: str):
    """Get a specific course by ID"""
    try:
        manager = get_course_manager()
        course = manager.get_course(course_id)
        
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        return {"success": True, "course": course}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/courses/{course_id}")
async def update_course(course_id: str, request: Request):
    """Update a course"""
    try:
        data = await request.json()
        manager = get_course_manager()
        
        course = manager.update_course(course_id, **data)
        
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        return {"success": True, "course": course}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: str):
    """Delete (archive) a course"""
    try:
        manager = get_course_manager()
        success = manager.delete_course(course_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Course not found")
        
        return {"success": True, "message": "Course archived successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/courses/{course_id}/lessons")
async def create_lesson(course_id: str, request: Request):
    """Create a new lesson in a course"""
    try:
        data = await request.json()
        manager = get_course_manager()
        
        lesson = manager.create_lesson(
            course_id=course_id,
            title=data.get("title"),
            concept_ids=data.get("concept_ids", []),
            description=data.get("description"),
            order_index=data.get("order_index"),
            prerequisite_lesson_ids=data.get("prerequisite_lesson_ids"),
            estimated_minutes=data.get("estimated_minutes", 30),
            difficulty=data.get("difficulty", "foundational"),
            video_references=data.get("video_references"),
            document_references=data.get("document_references"),
            learning_objectives=data.get("learning_objectives"),
            key_takeaways=data.get("key_takeaways")
        )
        
        return {"success": True, "lesson": lesson}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error creating lesson: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/{course_id}/lessons")
async def list_lessons(course_id: str):
    """List all lessons for a course"""
    try:
        manager = get_course_manager()
        lessons = manager.list_lessons(course_id)
        return {"success": True, "lessons": lessons}
    except Exception as e:
        print(f"❌ Error listing lessons: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lessons")
async def list_all_lessons():
    """List all lessons across all courses (for YouTube linking UI)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT l.id, l.title, l.course_id, l.order_index, c.title as course_title
            FROM lessons l
            LEFT JOIN courses c ON l.course_id = c.id
            ORDER BY c.title, l.order_index
        """)
        
        lessons = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return lessons
        
    except Exception as e:
        print(f"❌ Error listing all lessons: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lessons/{lesson_id}")
async def get_lesson(lesson_id: str):
    """Get a specific lesson by ID"""
    try:
        manager = get_course_manager()
        lesson = manager.get_lesson(lesson_id)
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        return {"success": True, "lesson": lesson}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting lesson: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/lessons/{lesson_id}")
async def update_lesson(lesson_id: str, request: Request):
    """Update a lesson"""
    try:
        data = await request.json()
        manager = get_course_manager()
        
        lesson = manager.update_lesson(lesson_id, **data)
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        return {"success": True, "lesson": lesson}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating lesson: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str):
    """Delete a lesson"""
    try:
        manager = get_course_manager()
        success = manager.delete_lesson(lesson_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        return {"success": True, "message": "Lesson deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting lesson: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lessons/{lesson_id}/concepts")
async def get_lesson_concepts(lesson_id: str, response: Response):
    """Get concepts assigned to a lesson, ordered by rank (Phase 6)"""
    try:
        # Set explicit headers to prevent browser caching/hanging issues
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get concepts with their assignment data
        cursor.execute("""
            SELECT 
                lc.concept_id as id,
                lc.confidence,
                lc.similarity_score,
                lc.metadata_overlap_score,
                lc.assignment_rank
            FROM lesson_concepts lc
            WHERE lc.lesson_id = %s
            ORDER BY lc.assignment_rank ASC
        """, (lesson_id,))
        
        assignments = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Load knowledge graph to get concept details (OPTIMIZED: load once, build lookup dict)
        graph = kg_manager.load_graph()
        
        # Build O(1) lookup dictionary for concepts
        concept_lookup = {node['id']: node for node in graph.get('nodes', [])}
        
        concepts = []
        for assignment in assignments:
            concept_id_raw = assignment['id']
            
            # BUGFIX: Strip "concept_" prefix for knowledge graph lookup
            # Pinecone uses "concept_octagram", but knowledge graph has "octagram"
            concept_id_for_lookup = concept_id_raw.replace('concept_', '', 1) if concept_id_raw.startswith('concept_') else concept_id_raw
            
            # O(1) lookup instead of O(N) nested loop
            concept_node = concept_lookup.get(concept_id_for_lookup)
            
            if concept_node:
                concepts.append({
                    'id': concept_id_raw,  # Keep original ID from database
                    'name': concept_node.get('label', concept_id_for_lookup),
                    'description': concept_node.get('definition', ''),
                    'category': concept_node.get('category', ''),
                    'confidence': assignment['confidence'],
                    'similarity_score': float(assignment['similarity_score']),
                    'metadata_overlap_score': float(assignment['metadata_overlap_score']),
                    'assignment_rank': assignment['assignment_rank']
                })
        
        return {"success": True, "concepts": concepts}
        
    except Exception as e:
        print(f"❌ Error getting lesson concepts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/{course_id}/progress")
async def get_progress(course_id: str, user_id: str = "jeralyn"):
    """Get user progress for a course"""
    try:
        manager = get_course_manager()
        progress = manager.get_or_create_progress(course_id, user_id)
        return {"success": True, "progress": progress}
    except Exception as e:
        print(f"❌ Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/courses/{course_id}/progress")
async def update_progress(course_id: str, request: Request):
    """Update user progress for a course"""
    try:
        data = await request.json()
        user_id = data.pop("user_id", "jeralyn")
        
        manager = get_course_manager()
        progress = manager.update_progress(course_id, user_id, **data)
        
        return {"success": True, "progress": progress}
    except Exception as e:
        print(f"❌ Error updating progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/courses/{course_id}/lessons/{lesson_id}/complete")
async def mark_lesson_complete(course_id: str, lesson_id: str):
    """Mark a lesson as completed"""
    try:
        manager = get_course_manager()
        progress = manager.mark_lesson_complete(course_id, lesson_id)
        return {"success": True, "progress": progress}
    except Exception as e:
        print(f"❌ Error marking lesson complete: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DELETE API - Content Management (Phase 6.5)
# =============================================================================

@app.delete("/api/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str):
    """Delete a single lesson and its concept assignments"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if lesson exists
        cursor.execute("SELECT id, title FROM lessons WHERE id = %s", (lesson_id,))
        lesson = cursor.fetchone()
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        lesson_title = lesson['title']
        
        # Delete lesson (CASCADE should handle lesson_concepts if configured)
        # If not, explicitly delete concept assignments first
        cursor.execute("DELETE FROM lesson_concepts WHERE lesson_id = %s", (lesson_id,))
        cursor.execute("DELETE FROM lessons WHERE id = %s", (lesson_id,))
        
        conn.commit()
        
        print(f"✅ [DELETE] Deleted lesson: {lesson_title} (ID: {lesson_id})")
        return {
            "success": True,
            "message": f"Deleted: {lesson_title}"
        }
        
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error deleting lesson {lesson_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: str):
    """Delete a course and all its lessons"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if course exists
        cursor.execute("SELECT id, title FROM courses WHERE id = %s", (course_id,))
        course = cursor.fetchone()
        
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course_title = course['title']
        
        # Count lessons to be deleted
        cursor.execute("SELECT COUNT(*) as count FROM lessons WHERE course_id = %s", (course_id,))
        lesson_count_result = cursor.fetchone()
        lesson_count = lesson_count_result['count'] if lesson_count_result else 0
        
        # Get all lesson IDs for this course
        cursor.execute("SELECT id FROM lessons WHERE course_id = %s", (course_id,))
        lesson_ids = [row['id'] for row in cursor.fetchall()]
        
        # Delete concept assignments for all lessons
        if lesson_ids:
            cursor.execute(
                "DELETE FROM lesson_concepts WHERE lesson_id = ANY(%s)",
                (lesson_ids,)
            )
        
        # Delete lessons (CASCADE handles this if configured, but we're being explicit)
        cursor.execute("DELETE FROM lessons WHERE course_id = %s", (course_id,))
        
        # Delete course
        cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))
        
        conn.commit()
        
        print(f"✅ [DELETE] Deleted course '{course_title}' (ID: {course_id}) with {lesson_count} lessons")
        return {
            "success": True,
            "message": f"Deleted \"{course_title}\" and {lesson_count} lessons"
        }
        
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error deleting course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.delete("/api/admin/reset-all")
async def reset_all_content():
    """Delete ALL courses, lessons, and assignments (admin only)"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Count everything first
        cursor.execute("SELECT COUNT(*) as count FROM courses")
        course_count_result = cursor.fetchone()
        course_count = course_count_result['count'] if course_count_result else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM lessons")
        lesson_count_result = cursor.fetchone()
        lesson_count = lesson_count_result['count'] if lesson_count_result else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM lesson_concepts")
        assignment_count_result = cursor.fetchone()
        assignment_count = assignment_count_result['count'] if assignment_count_result else 0
        
        # Delete everything (in order due to foreign keys)
        cursor.execute("DELETE FROM lesson_concepts")
        cursor.execute("DELETE FROM lessons")
        cursor.execute("DELETE FROM courses")
        
        conn.commit()
        
        print(f"🗑️ [NUCLEAR RESET] Deleted {course_count} courses, {lesson_count} lessons, {assignment_count} assignments")
        return {
            "success": True,
            "message": f"Deleted {course_count} courses, {lesson_count} lessons, {assignment_count} assignments"
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error in nuclear reset: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


# =============================================================================
# COURSE STRUCTURE GENERATION - Background Worker
# =============================================================================

def generate_course_structure_worker(job_id: int):
    """
    Background worker to generate course structure using Claude AI.
    Runs in FastAPI's thread pool automatically.
    
    Flow:
    1. Call Claude to generate course structure (5-25s)
    2. Create courses in database
    3. Launch lesson content generation job
    4. Update job status
    """
    # EMERGENCY DEBUG: Log immediately with flush to ensure it appears
    import sys
    print(f"🚨🚨🚨 [WORKER ENTRY] Worker function called with job_id={job_id}", flush=True)
    sys.stdout.flush()
    
    print(f"🏗️ [STRUCTURE GEN] Starting job {job_id}", flush=True)
    
    job_service = None
    
    try:
        print(f"🔍 [STRUCTURE GEN] Job {job_id}: Inside try block", flush=True)
        # Initialize services
        job_service = BackgroundJobService()
        generator = get_course_generator()
        manager = get_course_manager()
        
        # Get job details
        job = job_service.get_job_status(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")
        
        payload = job['request_payload']
        user_goal = payload['user_goal']
        request_data = payload['request_data']
        
        print(f"🤖 [STRUCTURE GEN] Job {job_id}: Calling Claude for goal: {user_goal}")
        
        # Update status to processing
        job_service.update_job_status(job_id, 'processing')
        
        # STEP 1: Generate learning path using AI (HEAVY - 5-25s)
        learning_path = generator.generate_curriculum(
            user_goal=user_goal,
            relevant_concept_ids=request_data.get("relevant_concept_ids"),
            max_lessons=request_data.get("max_lessons", 12),
            target_category=request_data.get("target_category")
        )
        
        print(f"✅ [STRUCTURE GEN] Job {job_id}: Claude returned course structure")
        
        # STEP 2: Create courses in database
        courses_data = learning_path.get('courses', [])
        result = manager.create_learning_path(
            courses_data=courses_data,
            user_goal=user_goal
        )
        
        created_courses = result['created_courses']
        total_lessons = result['total_lessons']
        generation_cost = learning_path.get('generation_metadata', {}).get('cost', 0.0)
        
        print(f"✅ [STRUCTURE GEN] Job {job_id}: Created {len(created_courses)} courses with {total_lessons} lessons")
        
        # STEP 2.5: Assign knowledge graph concepts to lessons
        from src.services.concept_assigner import ConceptAssigner
        concept_cost = 0.0
        concepts_assigned = 0
        
        try:
            print(f"🎯 [STRUCTURE GEN] Job {job_id}: Starting concept assignment for {len(created_courses)} courses")
            
            concept_assigner = ConceptAssigner(
                database_url=DATABASE_URL,
                pinecone_api_key=PINECONE_API_KEY,
                pinecone_index_name=PINECONE_INDEX,
                openai_api_key=OPENAI_API_KEY
            )
            
            for course in created_courses:
                course_id = course['id']
                print(f"🎯 [STRUCTURE GEN] Job {job_id}: Assigning concepts to course {course['title']}")
                
                assignment_result = concept_assigner.assign_concepts_to_course(course_id)
                
                if assignment_result['success']:
                    concepts_assigned += assignment_result['total_concepts_assigned']
                    concept_cost += assignment_result['cost']
                    print(f"✅ [STRUCTURE GEN] Job {job_id}: Assigned {assignment_result['total_concepts_assigned']} concepts to {assignment_result['lessons_processed']} lessons")
                else:
                    # Log warning but don't fail the entire job
                    print(f"⚠️ [STRUCTURE GEN] Job {job_id}: Concept assignment failed for course {course_id}: {assignment_result.get('error', 'Unknown error')}")
            
            print(f"✅ [STRUCTURE GEN] Job {job_id}: Concept assignment complete. Total: {concepts_assigned} concepts, cost: ${concept_cost:.4f}")
            
        except Exception as e:
            # Log error but continue with content generation
            print(f"⚠️ [STRUCTURE GEN] Job {job_id}: Concept assignment failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # STEP 3: Launch lesson content generation job
        course_ids = [course['id'] for course in created_courses]
        content_job_id = job_service.create_course_content_job(course_ids)
        
        print(f"📝 [STRUCTURE GEN] Job {job_id}: Launched content job {content_job_id}")
        
        # Prepare payload updates with results
        total_cost = generation_cost + concept_cost
        payload_updates = {
            'courses_created': created_courses,
            'content_job_id': content_job_id,
            'total_cost': total_cost,
            'concept_cost': concept_cost,
            'concepts_assigned': concepts_assigned,
            'path_type': learning_path.get('path_type', 'simple'),
            'path_summary': learning_path.get('path_summary', '')
        }
        
        # Mark job as complete with payload updates
        summary = f"Generated {len(created_courses)} courses with {total_lessons} lessons, {concepts_assigned} concepts. Cost: ${total_cost:.4f}"
        job_service.complete_job(job_id, summary, error_message=None, payload_updates=payload_updates)
        
        # Launch the content generation worker (this continues in background)
        from fastapi import BackgroundTasks
        # Note: We can't use BackgroundTasks here since we're already in a background task
        # Instead, we'll call the worker directly (it will run in the same thread)
        generate_lesson_content_worker(content_job_id, course_ids)
        
        print(f"🎉 [STRUCTURE GEN] Job {job_id} complete!")
        
    except Exception as e:
        # Fatal error - entire job failed
        print(f"❌ [STRUCTURE GEN] Job {job_id} FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Always try to mark job as failed
        try:
            if job_service is None:
                job_service = BackgroundJobService()
            job_service.update_job_status(job_id, 'failed')
            job_service.complete_job(job_id, "", error_message=str(e))
        except Exception as final_error:
            print(f"❌ [STRUCTURE GEN] Could not update job status: {str(final_error)}")


# =============================================================================
# LESSON CONTENT GENERATION - Background Worker
# =============================================================================

def generate_lesson_content_worker(job_id: int, course_ids: list[str]):
    """
    Background worker to generate lesson content for courses.
    Runs in FastAPI's thread pool automatically.
    
    IMPORTANT: This worker is resilient to per-lesson failures.
    One lesson failing does NOT fail the entire job.
    """
    print(f"📝 [CONTENT GEN] Starting job {job_id} for {len(course_ids)} courses")
    
    job_service = None
    content_generator = None
    
    try:
        job_service = BackgroundJobService()
        content_generator = LessonContentGenerator()
        
        # Update status to processing
        job_service.update_job_status(job_id, 'processing')
        
        all_results = []
        total_lessons = 0
        completed = 0
        failed = 0
        total_cost = 0.0
        
        # Process each course (continue even if one course fails)
        for course_id in course_ids:
            try:
                print(f"📚 [CONTENT GEN] Processing course {course_id}")
                
                result = content_generator.generate_for_course(course_id)
                
                if result['success']:
                    total_lessons += result['total_lessons']
                    completed += result['generated']
                    failed += result['skipped']
                    total_cost += result['total_cost']
                    all_results.extend(result['results'])
                    
                    print(f"✅ [CONTENT GEN] Course {course_id}: {result['generated']}/{result['total_lessons']} lessons")
                else:
                    print(f"⚠️ [CONTENT GEN] Course {course_id} failed: {result.get('error')}")
                    # Count as failed but continue processing other courses
                    failed += 1
                
                # Update progress after each course (resilient to DB errors)
                try:
                    job_service.update_content_generation_progress(
                        job_id=job_id,
                        total_lessons=total_lessons,
                        completed=completed,
                        failed=failed,
                        total_cost=total_cost,
                        per_lesson_results=all_results
                    )
                except Exception as progress_error:
                    print(f"⚠️ [CONTENT GEN] Failed to update progress: {str(progress_error)}")
                    # Continue anyway - progress update failure shouldn't kill the job
                    
            except Exception as course_error:
                print(f"❌ [CONTENT GEN] Course {course_id} exception: {str(course_error)}")
                import traceback
                traceback.print_exc()
                failed += 1
                # Continue to next course
        
        # Mark job as completed (always update final status)
        final_status = 'completed' if failed == 0 else 'completed_with_errors'
        job_service.update_job_status(job_id, final_status)
        
        # Store final results
        final_summary = f"Generated content for {completed} lessons, {failed} failed, cost: ${total_cost:.4f}"
        job_service.complete_job(job_id, final_summary, error_message=None)
        
        print(f"🎉 [CONTENT GEN] Job {job_id} complete: {completed} generated, {failed} failed, ${total_cost:.4f}")
        
    except Exception as e:
        # Fatal error - entire job failed
        print(f"❌ [CONTENT GEN] Job {job_id} FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Always try to mark job as failed (even if job_service is None)
        try:
            if job_service is None:
                job_service = BackgroundJobService()
            job_service.update_job_status(job_id, 'failed')
            job_service.complete_job(job_id, "", error_message=str(e))
        except Exception as final_error:
            print(f"❌ [CONTENT GEN] Could not update job status: {str(final_error)}")


# =============================================================================
# AI GENERATION API - Course Generation & Content Assignment
# =============================================================================

# EMERGENCY DEBUG: Test if BackgroundTasks work at all
def test_background_task(message: str):
    """Simple test function to verify BackgroundTasks execute"""
    import sys
    print(f"🧪🧪🧪 [TEST BACKGROUND TASK] {message}", flush=True)
    sys.stdout.flush()

@app.get("/api/test-background")
async def test_background(background_tasks: BackgroundTasks):
    """Test endpoint to verify BackgroundTasks work"""
    print("🧪 [TEST] Adding background task...", flush=True)
    background_tasks.add_task(test_background_task, "Hello from background!")
    return {"message": "Test task queued"}

@app.post("/api/courses/generate")
async def generate_course(request: Request):
    """
    Generate a complete LEARNING PATH (1-4 courses) from user goal using AI.
    
    IMPORTANT: This creates a learning progression, not just a single course.
    For comprehensive goals, expect 2-4 courses with prerequisites.
    
    Request body:
        {
            "user_goal": "Master ENFP cognitive functions and shadow integration",
            "relevant_concept_ids": ["concept-1", "concept-2"],  # optional
            "max_lessons": 12,  # optional, default 15 per course
            "target_category": "advanced"  # optional (ignored for multi-course paths)
        }
    
    Response:
        {
            "success": true,
            "message": "Generated learning path with 3 courses and 24 total lessons",
            "path_type": "comprehensive",
            "path_summary": "Three-course progression...",
            "courses": [
                {
                    "id": "uuid-1",
                    "title": "ENFP Foundations",
                    "category": "foundations",
                    "lesson_count": 8,
                    "prerequisite_course_id": null
                },
                ...
            ],
            "total_courses": 3,
            "total_lessons": 24,
            "cost": 0.0523
        }
    """
    try:
        print(f"🚀 [COURSE GEN] Received request - THREADING VERSION")
        data = await request.json()
        user_goal = data.get("user_goal")
        
        if not user_goal or not user_goal.strip():
            raise HTTPException(status_code=400, detail="user_goal is required")
        
        # Create background job for course structure generation
        job_service = BackgroundJobService()
        request_data = {
            "relevant_concept_ids": data.get("relevant_concept_ids"),
            "max_lessons": data.get("max_lessons", 12),
            "target_category": data.get("target_category")
        }
        
        job_id = job_service.create_course_structure_job(user_goal, request_data)
        
        # Launch background worker using threading.Thread (more reliable than BackgroundTasks)
        thread = threading.Thread(target=generate_course_structure_worker, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        print(f"✅ [COURSE GEN] Created job {job_id}, returning immediately")
        
        # Return immediately with job ID (response time: <100ms)
        return {
            "success": True,
            "message": "Course generation started. Poll the job status for progress.",
            "job_id": job_id,
            "user_goal": user_goal,
            # For frontend compatibility - it expects these fields
            "structure_job_id": job_id,
            "status": "processing"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Learning path generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Learning path generation failed: {str(e)}")


@app.get("/api/courses/structure-generation/{job_id}")
async def get_structure_generation_status(job_id: int):
    """
    Poll the status of a course structure generation job.
    
    Returns:
        {
            "success": true,
            "job_id": 123,
            "status": "processing",  # queued, processing, completed, failed
            "courses_created": [...],  # Available when completed
            "content_job_id": 456,  # Available when completed
            "cost": 0.05,
            "created_at": "2025-11-09T...",
            "completed_at": null,
            "error_message": null
        }
    """
    try:
        job_service = BackgroundJobService()
        job = job_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        payload = job['request_payload']
        
        return {
            "success": True,
            "job_id": job_id,
            "status": job['status'],
            "user_goal": payload.get('user_goal'),
            "courses_created": payload.get('courses_created', []),
            "content_job_id": payload.get('content_job_id'),
            "cost": payload.get('total_cost', 0.0),
            "created_at": job['created_at'].isoformat() if job['created_at'] else None,
            "completed_at": job['completed_at'].isoformat() if job['completed_at'] else None,
            "error_message": job['error_message']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Structure generation status error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/content-generation/{job_id}")
async def get_content_generation_status(job_id: int):
    """
    Poll the status of a course content generation job.
    
    Returns:
        {
            "success": true,
            "job_id": 123,
            "status": "processing",  # queued, processing, completed, completed_with_errors, failed
            "progress": {
                "total_lessons": 10,
                "completed": 7,
                "failed": 1,
                "percent": 70
            },
            "cost": 0.15,
            "created_at": "2025-11-09T...",
            "completed_at": null,  # null if not completed
            "error_message": null
        }
    """
    try:
        job_service = BackgroundJobService()
        job = job_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Extract progress from request_payload
        payload = job['request_payload']
        total_lessons = payload.get('total_lessons', 0)
        completed = payload.get('completed', 0)
        failed = payload.get('failed', 0)
        total_cost = payload.get('total_cost', 0.0)
        
        percent = int((completed + failed) / total_lessons * 100) if total_lessons > 0 else 0
        
        return {
            "success": True,
            "job_id": job_id,
            "status": job['status'],
            "progress": {
                "total_lessons": total_lessons,
                "completed": completed,
                "failed": failed,
                "percent": percent
            },
            "cost": total_cost,
            "created_at": job['created_at'].isoformat() if job['created_at'] else None,
            "completed_at": job['completed_at'].isoformat() if job['completed_at'] else None,
            "error_message": job['error_message']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/courses/assign-content")
async def assign_content(request: Request):
    """
    Assign new document content to existing tracks using AI analysis.
    
    Request body:
        {
            "document_id": "doc-uuid-123",
            "extracted_concept_ids": ["concept-1", "concept-2", "concept-3"],
            "document_metadata": {
                "title": "ENFP Ne Hero Function",
                "video_id": "S02E05",
                "duration_minutes": 45
            },
            "auto_create_lesson": true
        }
    
    Confidence tiers:
    - High (90%+): Auto-add silently
    - Medium (70-89%): Auto-add with reasoning shown
    - Low (<70%): Recommend creating new track
    """
    try:
        data = await request.json()
        document_id = data.get("document_id")
        extracted_concept_ids = data.get("extracted_concept_ids")
        
        if not document_id:
            raise HTTPException(status_code=400, detail="document_id is required")
        if not extracted_concept_ids:
            raise HTTPException(status_code=400, detail="extracted_concept_ids is required")
        
        assigner = get_content_assigner()
        manager = get_course_manager()
        
        # Get assignment recommendation
        assignment = assigner.assign_content(
            document_id=document_id,
            extracted_concept_ids=extracted_concept_ids,
            document_metadata=data.get("document_metadata")
        )
        
        # Auto-create lesson if requested and confidence is high/medium
        lesson_id = None
        auto_create = data.get("auto_create_lesson", False)
        
        if auto_create and assignment['action'] == 'add_to_existing':
            lesson_data = assignment['suggested_lesson']
            
            try:
                lesson = manager.create_lesson(
                    course_id=assignment['course_id'],
                    title=lesson_data['title'],
                    concept_ids=lesson_data['concept_ids'],
                    order_index=lesson_data.get('order_index'),
                    description=lesson_data.get('description'),
                    estimated_minutes=lesson_data.get('estimated_minutes', 30),
                    difficulty=lesson_data.get('difficulty', 'foundational'),
                    document_references=lesson_data.get('document_references', [])
                )
                lesson_id = lesson['id']
                
            except Exception as e:
                print(f"⚠️ Failed to auto-create lesson: {str(e)}")
        
        # Build response message
        if assignment['action'] == 'add_to_existing':
            message = f"Content assigned to '{assignment['course_title']}' ({assignment['confidence_tier']} confidence)"
            if lesson_id:
                message += f" - Lesson created: {assignment['suggested_lesson']['title']}"
        else:
            message = f"Recommend creating new track: '{assignment['course_title']}'"
        
        return {
            "success": True,
            "message": message,
            "assignment": assignment,
            "lesson_id": lesson_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Content assignment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Content assignment failed: {str(e)}")


# =============================================================================
# BACKGROUND JOBS API
# =============================================================================

@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: int):
    """
    Get the status of a background job.
    
    Returns:
        {
            "success": true,
            "job": {
                "id": 4,
                "conversation_id": 74,
                "lesson_id": null,
                "job_type": "main_chat",
                "status": "completed",  // queued, processing, completed, failed
                "response_content": "AI response here...",
                "created_at": "2025-11-07T...",
                "completed_at": "2025-11-07T...",
                "error_message": null
            }
        }
    """
    try:
        job_service = BackgroundJobService()
        job = job_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "success": True,
            "job": job
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Mount static files with custom handler for cache-busting
class NoCacheStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")
app.mount("/node_modules", StaticFiles(directory="node_modules"), name="node_modules")


# === Run the app ===
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Starting server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
