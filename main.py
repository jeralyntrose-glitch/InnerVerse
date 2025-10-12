from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import uuid
import PyPDF2
import io
import os

from pinecone import Pinecone
from openai import OpenAI, OpenAIError
from langchain.text_splitter import RecursiveCharacterTextSplitter

app = FastAPI()
pdf_store = {}

# === Helper: Pinecone client ===
def get_pinecone_client():
    api_key = os.getenv("PINECONE_API_KEY")
    if api_key:
        pc = Pinecone(api_key=api_key)
        return pc.Index("mbti-knowledge")
    return None

# === Helper: OpenAI client ===
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)
    return None

# === Health check ===
@app.get("/test-connection")
def test_connection():
    return {"status": "ok"}

def chunk_text(text, chunk_size=1000, chunk_overlap=200):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        chunks = splitter.split_text(text)
        return chunks

# === Upload PDF and store chunks ===
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
        text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
        chunks = chunk_text(text)
        
        print(f"Uploading {len(chunks)} chunks to Pinecone")
        doc_id = str(uuid.uuid4())

        openai_client = get_openai_client()
        pinecone_index = get_pinecone_client()

        if not openai_client or not pinecone_index:
            return JSONResponse(status_code=500, content={"error": "OpenAI or Pinecone client not initialized"})

        for i, chunk in enumerate(chunks):
            response = openai_client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            vector = response.data[0].embedding
            pinecone_index.upsert(vectors=[{
                "id": f"{doc_id}-{i}",
                "values": vector,
                "metadata": {"text": chunk, "doc_id": doc_id}
            }])

        return {"document_id": doc_id}

    except OpenAIError as e:
        return JSONResponse(status_code=500, content={"error": f"OpenAI error: {str(e)}"})
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
        contexts = [match["metadata"]["text"] for match in query_response["matches"]]

        if not contexts:
            return {"answer": "No relevant information found in the document."}

        context_text = "\n\n".join(contexts)
        prompt = f"Answer the question based on the context below.\n\nContext:\n{context_text}\n\nQuestion: {question}\nAnswer:"

        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        answer = completion.choices[0].message.content
        return {"answer": answer}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Run the app ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)