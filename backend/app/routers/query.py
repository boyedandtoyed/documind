from __future__ import annotations

import json
import logging
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.models.query import QueryRequest, QueryResponse, StreamChunk
from app.services.embeddings import EmbeddingService
from app.services.evaluator import EvaluatorService
from app.services.graph_store import GraphStoreService
from app.services.rag_pipeline import RAGPipeline
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])


def _build_pipeline(settings: Settings) -> RAGPipeline:
    embedding_svc = EmbeddingService(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
    vector_store = VectorStoreService(
        url=settings.qdrant_url,
        collection_name=settings.collection_name,
        embedding_dim=settings.embedding_dim,
    )
    graph_store = GraphStoreService(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    evaluator = EvaluatorService(
        db_path=settings.db_path,
        ollama_base_url=settings.ollama_base_url,
        llm_model=settings.llm_model,
    )
    return RAGPipeline(
        embedding_service=embedding_svc,
        vector_store=vector_store,
        graph_store=graph_store,
        evaluator=evaluator,
        ollama_base_url=settings.ollama_base_url,
        llm_model=settings.llm_model,
        rerank_top_k=settings.rerank_top_k,
    )


@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> QueryResponse:
    query_id = str(uuid.uuid4())
    pipeline = _build_pipeline(settings)

    try:
        await pipeline.vector_store.initialize()
        await pipeline.graph_store.initialize()
        await pipeline.evaluator.initialize()
        response = await pipeline.run(request, query_id)
        await pipeline.graph_store.close()
        return response
    except Exception as e:
        logger.error("Query pipeline error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {e}",
        )


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    query_id = str(uuid.uuid4())
    pipeline = _build_pipeline(settings)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            await pipeline.vector_store.initialize()
            await pipeline.graph_store.initialize()
            await pipeline.evaluator.initialize()

            async for chunk in pipeline.stream(request, query_id):
                data = json.dumps(chunk.model_dump())
                yield f"data: {data}\n\n"

            await pipeline.graph_store.close()
        except Exception as e:
            logger.error("Streaming error: %s", e)
            error_chunk = StreamChunk(type="error", content=str(e))
            yield f"data: {json.dumps(error_chunk.model_dump())}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
