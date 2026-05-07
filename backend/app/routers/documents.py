from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response,  UploadFile, status

from app.config import Settings, get_settings
from app.models.document import (
    Document,
    DocumentListResponse,
    DocumentStatus,
    DocumentType,
    DocumentUploadResponse,
)
from app.services.embeddings import EmbeddingService
from app.services.graph_store import GraphStoreService
from app.services.ingestion import IngestionService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

_document_store: dict[str, Document] = {}


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF, DOCX, TXT, or MD file")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentUploadResponse:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    ext_to_type = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX,
        ".txt": DocumentType.TXT,
        ".md": DocumentType.MD,
    }
    file_type = ext_to_type[ext]

    doc_id = str(uuid.uuid4())
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / f"{doc_id}{ext}"

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB.",
        )
    save_path.write_bytes(content)

    document = Document(
        id=doc_id,
        name=file.filename or f"document_{doc_id}",
        file_type=file_type,
        file_size=len(content),
        status=DocumentStatus.PROCESSING,
    )
    _document_store[doc_id] = document

    try:
        ingestion = IngestionService(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks = await ingestion.process_file(str(save_path), document)

        embedding_svc = EmbeddingService(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
        texts = [c.text for c in chunks]
        embeddings = await embedding_svc.embed_texts(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        vector_store = VectorStoreService(
            url=settings.qdrant_url,
            collection_name=settings.collection_name,
            embedding_dim=settings.embedding_dim,
        )
        await vector_store.initialize()
        await vector_store.upsert_chunks(chunks)

        graph_store = GraphStoreService(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        await graph_store.initialize()
        chunks_with_entities = [
            (c.id, GraphStoreService.extract_entities(c.text)) for c in chunks
        ]
        await graph_store.store_document_graph(doc_id, document.name, chunks_with_entities)
        await graph_store.close()

        document.status = DocumentStatus.READY
        document.chunk_count = len(chunks)

        return DocumentUploadResponse(
            document_id=doc_id,
            status=DocumentStatus.READY,
            message=f"Successfully processed '{document.name}' into {len(chunks)} chunks.",
            chunk_count=len(chunks),
        )

    except Exception as e:
        logger.error("Ingestion failed for document %s: %s", doc_id, e)
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {e}",
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(page: int = 1, page_size: int = 20) -> DocumentListResponse:
    docs = list(_document_store.values())
    docs.sort(key=lambda d: d.created_at, reverse=True)
    start = (page - 1) * page_size
    return DocumentListResponse(
        documents=docs[start : start + page_size],
        total=len(docs),
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=Document)
async def get_document(document_id: str) -> Document:
    doc = _document_store.get(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    doc = _document_store.get(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    try:
        vector_store = VectorStoreService(
            url=settings.qdrant_url,
            collection_name=settings.collection_name,
        )
        await vector_store.initialize()
        await vector_store.delete_by_document(document_id)

        graph_store = GraphStoreService(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        await graph_store.initialize()
        await graph_store.delete_document(document_id)
        await graph_store.close()
    except Exception as e:
        logger.warning("Cleanup error during document deletion: %s", e)

    ext_map = {
        DocumentType.PDF: ".pdf",
        DocumentType.DOCX: ".docx",
        DocumentType.TXT: ".txt",
        DocumentType.MD: ".md",
    }
    save_path = Path(settings.upload_dir) / f"{document_id}{ext_map.get(doc.file_type, '.txt')}"
    if save_path.exists():
        save_path.unlink()

    del _document_store[document_id]
    return Reponse(status_code=status.HTTP_204_NO_CONTENT)
