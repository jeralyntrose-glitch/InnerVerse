import os
import uuid
import io
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
from pinecone import Pinecone

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
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_text(text)
    return chunks

# Create FastAPI app
app = FastAPI()

# === Upload PDF and store chunks ===
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pdf_reader = PdfReader(io.BytesIO(contents))
        text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
        chunks = chunk_text(text)
        print(f"📄 Uploading {len(chunks)} chunks to Pinecone")

        doc_id = str(uuid.uuid4())
        openai_client = get_openai_client()
        pinecone_index = get_pinecone_client()

        if not openai_client or not pinecone_index:
            return JSONResponse(status_code=500, content={"error": "OpenAI or Pinecone client not initialized"})

        # Batch process embeddings and upserts for better performance
        vectors_to_upsert = []
        
        for i, chunk in enumerate(chunks):
            response = openai_client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002",
                timeout=30
            )
            vector = response.data[0].embedding
            vectors_to_upsert.append((f"{doc_id}-{i}", vector, {"text": chunk, "doc_id": doc_id}))
        
        # Batch upsert all vectors at once
        if vectors_to_upsert:
            pinecone_index.upsert(vectors=vectors_to_upsert)
            print(f"✅ Successfully uploaded {len(vectors_to_upsert)} chunks")

        return {"message": "PDF uploaded and indexed", "document_id": doc_id, "chunks_count": len(chunks)}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Query PDF for an answer ===
@app.post("/query")
async def query_pdf(document_id: str, question: str):
    openai_client = get_openai_client()
    pinecone_index = get_pinecone_client()

    if not openai_client or not pinecone_index:
        return JSONResponse(status_code=500, content={"error": "OpenAI or Pinecone client not initialized"})

    try:
        embed_response = openai_client.embeddings.create(
            input=question,
            model="text-embedding-ada-002"
        )
        question_vector = embed_response.data[0].embedding

        query_response = pinecone_index.query(
            vector=question_vector,
            top_k=5,
            include_metadata=True,
            filter={"doc_id": document_id}
        )

        matches = query_response.get("matches", [])
        contexts = [m["metadata"]["text"] for m in matches if "metadata" in m and "text" in m["metadata"]]

        if not contexts:
            return {"answer": "No relevant information found in the document."}

        context_text = "\n\n".join(contexts)
        print(f"\n🔍 Sending this context to GPT:\n{context_text}\n")

        prompt = f"Answer the question based on the context below.\n\nContext:\n{context_text}\n\nQuestion: {question}\nAnswer:"

        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            timeout=15  # Prevents hanging
        )

        answer = completion.choices[0].message.content
        return {"answer": answer}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Run the app ===
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)