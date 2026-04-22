from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.query import QualityMetrics, UsageStats
from app.routers.documents import _document_store
from app.services.evaluator import EvaluatorService
from app.services.vector_store import VectorStoreService

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _get_evaluator(settings: Settings) -> EvaluatorService:
    svc = EvaluatorService(
        db_path=settings.db_path,
        ollama_base_url=settings.ollama_base_url,
        llm_model=settings.llm_model,
    )
    await svc.initialize()
    return svc


@router.get("/usage", response_model=UsageStats)
async def get_usage(
    settings: Annotated[Settings, Depends(get_settings)],
) -> UsageStats:
    total_documents = len(_document_store)

    try:
        vector_store = VectorStoreService(
            url=settings.qdrant_url,
            collection_name=settings.collection_name,
            embedding_dim=settings.embedding_dim,
        )
        await vector_store.initialize()
        total_chunks = await vector_store.count_chunks()
    except Exception:
        total_chunks = sum(d.chunk_count for d in _document_store.values())

    evaluator = await _get_evaluator(settings)
    return await evaluator.get_usage_stats(
        total_documents=total_documents,
        total_chunks=total_chunks,
    )


@router.get("/quality", response_model=QualityMetrics)
async def get_quality(
    settings: Annotated[Settings, Depends(get_settings)],
) -> QualityMetrics:
    evaluator = await _get_evaluator(settings)
    return await evaluator.get_quality_metrics()
