from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks: int
    status: str = "indexed"

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    document_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)

class SourceChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    text: str
    score: float
    page: Optional[int] = None

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceChunk]
    model: str
    tokens_used: int

class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    documents_indexed: int
