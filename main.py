import os
import uuid
import io
import base64
import json
import httpx
import csv
import tempfile
import subprocess
from datetime import datetime
from fastapi import FastAPI, UploadFile, File
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")


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


# Create FastAPI app
app = FastAPI()

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

        # Batch embedding + upsert
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            response = openai_client.embeddings.create(
                input=chunk, model="text-embedding-ada-002", timeout=30)
            vector = response.data[0].embedding
            vectors_to_upsert.append((f"{doc_id}-{i}", vector, {
                "text": chunk,
                "doc_id": doc_id,
                "filename": data.filename
            }))

        if vectors_to_upsert:
            pinecone_index.upsert(vectors=vectors_to_upsert)
            print(f"✅ Successfully uploaded {len(vectors_to_upsert)} chunks")

        return {
            "message": "PDF uploaded and indexed",
            "document_id": doc_id,
            "chunks_count": len(chunks)
        }

    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Upload PDF (File for regular clients) ===
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # ✅ Debug log — confirms if file is even received
        print(f"🛬 Received file: {file.filename}")

        contents = await file.read()
        pdf_reader = PdfReader(io.BytesIO(contents))
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

        # Batch embedding + upsert
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            response = openai_client.embeddings.create(
                input=chunk, model="text-embedding-ada-002", timeout=30)
            vector = response.data[0].embedding
            vectors_to_upsert.append((f"{doc_id}-{i}", vector, {
                "text": chunk,
                "doc_id": doc_id,
                "filename": file.filename
            }))

        if vectors_to_upsert:
            pinecone_index.upsert(vectors=vectors_to_upsert)
            print(f"✅ Successfully uploaded {len(vectors_to_upsert)} chunks")

        return {
            "message": "PDF uploaded and indexed",
            "document_id": doc_id,
            "chunks_count": len(chunks)
        }

    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
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
        
        # Extract unique documents
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
                
                if doc_id and doc_id not in documents:
                    documents[doc_id] = filename
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["document_id", "title"])
        
        for doc_id, filename in sorted(documents.items()):
            writer.writerow([doc_id, filename])
        
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


# === Query PDF for an answer ===
class QueryRequest(BaseModel):
    document_id: str
    question: str

# === YouTube Transcription Request ===
class YouTubeTranscribeRequest(BaseModel):
    youtube_url: str

@app.post("/query")
async def query_pdf(request: QueryRequest):
    document_id = request.document_id
    question = request.question
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

        query_response = pinecone_index.query(vector=question_vector,
                                              top_k=5,
                                              include_metadata=True,
                                              filter={"doc_id": document_id})

        try:
            matches = query_response.matches  # type: ignore
        except AttributeError:
            matches = query_response.get("matches", [])  # type: ignore
        
        contexts = [
            m["metadata"]["text"] for m in matches
            if "metadata" in m and "text" in m["metadata"]
        ]

        if not contexts:
            return {"answer": "No relevant information found in the document."}

        context_text = "\n\n".join(contexts)
        print(f"\n🔍 Sending this context to GPT:\n{context_text}\n")

        prompt = f"Answer the question based on the context below.\n\nContext:\n{context_text}\n\nQuestion: {question}\nAnswer:"

        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "You are a helpful assistant."
            }, {
                "role": "user",
                "content": prompt
            }],
            timeout=15  # Prevents hanging
        )

        answer = completion.choices[0].message.content
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
                raise Exception("yt-dlp is not installed. Please contact support.")
            
            # Get video info first
            info_command = [
                "yt-dlp",
                "--print", "%(title)s|||%(duration)s",
                youtube_url
            ]
            info_result = subprocess.run(info_command, capture_output=True, text=True, timeout=30)
            
            if info_result.returncode != 0:
                raise Exception(f"Failed to get video info: {info_result.stderr}")
            
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
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000 -b:a 32k",  # Mono, 16kHz, 32kbps
                "-o", audio_path,
                youtube_url
            ]
            
            # Add ffmpeg location if found
            if ffmpeg_location and os.path.dirname(ffmpeg_location):
                download_command.insert(1, "--ffmpeg-location")
                download_command.insert(2, os.path.dirname(ffmpeg_location))
            
            result = subprocess.run(download_command, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                raise Exception(f"yt-dlp failed: {result.stderr}")
            
            # Check if file was created
            if not os.path.exists(audio_path):
                raise Exception("Audio file was not created")
                
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"✅ Audio downloaded: {file_size_mb:.1f}MB")
            
        except subprocess.TimeoutExpired:
            return JSONResponse(status_code=500, content={"error": "Download timed out. Video may be too long."})
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Download failed: {str(e)}"})
        
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
                with open(audio_path, "rb") as audio_file:
                    transcript_response = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                transcript = transcript_response if isinstance(transcript_response, str) else transcript_response.text
                
            else:
                # File is too large - split into chunks
                print(f"📝 File size {file_size_mb:.1f}MB - splitting into chunks for transcription")
                
                # Load audio with pydub
                audio = AudioSegment.from_file(audio_path)
                chunk_length_ms = 10 * 60 * 1000  # 10 minutes per chunk
                total_chunks = len(audio) // chunk_length_ms + (1 if len(audio) % chunk_length_ms else 0)
                
                transcriptions = []
                
                for i in range(0, len(audio), chunk_length_ms):
                    chunk = audio[i:i + chunk_length_ms]
                    chunk_path = os.path.join(temp_dir, f"chunk_{i//chunk_length_ms}.mp3")
                    
                    # Export chunk as compressed MP3
                    chunk.export(chunk_path, format="mp3", bitrate="32k", parameters=["-ac", "1", "-ar", "16000"])
                    
                    # Transcribe chunk
                    chunk_num = i // chunk_length_ms + 1
                    print(f"  📝 Transcribing chunk {chunk_num}/{total_chunks}...")
                    
                    with open(chunk_path, "rb") as chunk_file:
                        chunk_response = openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=chunk_file,
                            response_format="text"
                        )
                    
                    chunk_transcript = chunk_response if isinstance(chunk_response, str) else chunk_response.text
                    transcriptions.append(chunk_transcript)
                    
                    # Clean up chunk file
                    os.remove(chunk_path)
                
                # Combine all transcriptions
                transcript = " ".join(transcriptions)
                print(f"✅ Combined {len(transcriptions)} chunks")
            
            print(f"✅ Transcription complete: {len(transcript)} characters")
            
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Transcription failed: {str(e)}"})
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
                filename=f"{video_title[:50].replace('/', '-')}_transcript.pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{video_title[:50].replace('/', '-')}_transcript.pdf\""
                }
            )
            
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"PDF generation failed: {str(e)}"})
        
    except Exception as e:
        print(f"❌ YouTube transcription error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Serve Frontend ===
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="."), name="static")


# === Run the app ===
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
