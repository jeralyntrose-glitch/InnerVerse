from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import uuid
import PyPDF2
import io

import os
from pinecone import Pinecone
from openai import OpenAI

app = FastAPI()
pdf_store = {}

def get_pinecone_client():
    api_key = os.getenv("PINECONE_API_KEY")
    if api_key:
        pc = Pinecone(api_key=api_key)
        return pc.Index("MBTI-knowledge")
    return None

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)
    return None
@app.get("/test-connection")
def test_connection():
    return {"status": "ok"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
    text = " ".join([page.extract_text() or "" for page in pdf_reader.pages])
    doc_id = str(uuid.uuid4())
    pdf_store[doc_id] = text
    return {"document_id": doc_id}

@app.post("/query")
async def query_pdf(document_id: str, question: str):
    if document_id not in pdf_store:
        return JSONResponse(status_code=404, content={"error": "Document not found"})
    content = pdf_store[document_id]
    if question.lower() in content.lower():
        return {"answer": "Yes, your question was found in the document."}
    else:
        return {"answer": "No direct match found, but GPT can interpret it."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)