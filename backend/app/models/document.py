from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"


class ChunkMetadata(BaseModel):
    document_id: str
    document_name: str
    chunk_index: int
    page_number: Optional[int] = None
    start_char: int = 0
    end_char: int = 0
    section_title: Optional[str] = None
    entities: List[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None
    sparse_vector: Optional[Dict[str, float]] = None

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Chunk text must not be empty")
        return v.strip()


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    file_type: DocumentType
    file_size: int
    status: DocumentStatus = DocumentStatus.PENDING
    chunk_count: int = 0
    page_count: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Document name must not be empty")
        return v.strip()

    @field_validator("file_size")
    @classmethod
    def file_size_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("File size must be non-negative")
        return v


class DocumentListResponse(BaseModel):
    documents: List[Document]
    total: int
    page: int = 1
    page_size: int = 20


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    message: str
    chunk_count: int = 0
