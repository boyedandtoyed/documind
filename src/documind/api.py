import tempfile
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from .models import DocumentUploadResponse, QueryRequest, QueryResponse, HealthResponse
from .chunker import chunk_pdf, chunk_text
from .vectorstore import index_chunks, document_count
from .rag import answer_query
from .config import settings

app = FastAPI(
    title="DocuMind",
    description="Production RAG engine — upload documents, query with Claude",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", documents_indexed=document_count())

@app.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(400, "Filename required")
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".txt", ".md"}:
        raise HTTPException(415, f"Unsupported file type: {ext}. Use .pdf, .txt, or .md")

    content = await file.read()
    document_id = str(uuid.uuid4())
    os.makedirs("./data", exist_ok=True)

    if ext == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            chunks = chunk_pdf(tmp_path, settings.max_chunk_size, settings.chunk_overlap)
        finally:
            os.unlink(tmp_path)
    else:
        text = content.decode("utf-8", errors="replace")
        chunks = chunk_text(text, settings.max_chunk_size, settings.chunk_overlap)

    if not chunks:
        raise HTTPException(422, "Could not extract text from document")

    n = index_chunks(document_id, file.filename, chunks)
    return DocumentUploadResponse(document_id=document_id, filename=file.filename, chunks=n)

@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    try:
        return answer_query(req.query, document_id=req.document_id, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(500, f"RAG query failed: {e}")
