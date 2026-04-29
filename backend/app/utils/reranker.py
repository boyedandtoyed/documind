from __future__ import annotations

import asyncio
import logging
from typing import List, Optional, Tuple

from app.models.document import Chunk

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """BGE cross-encoder reranker with graceful fallback to score-based ranking."""

    _model: Optional[object] = None
    _available: bool = False

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self.model_name = model_name
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
            self._model = CrossEncoder(self.model_name)
            self._available = True
            logger.info("CrossEncoder reranker loaded: %s", self.model_name)
        except Exception as e:
            logger.warning("CrossEncoder not available (%s); using score fallback.", e)
            self._available = False

    async def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        scores: List[float],
        top_k: int = 5,
    ) -> List[Tuple[Chunk, float]]:
        """Rerank chunks by relevance to query. Returns (chunk, score) sorted descending."""
        if not chunks:
            return []

        if self._available and self._model is not None:
            return await self._rerank_with_model(query, chunks, scores, top_k)
        return self._rerank_by_score(chunks, scores, top_k)

    async def _rerank_with_model(
        self,
        query: str,
        chunks: List[Chunk],
        scores: List[float],
        top_k: int,
    ) -> List[Tuple[Chunk, float]]:
        pairs = [(query, chunk.text) for chunk in chunks]
        loop = asyncio.get_event_loop()
        try:
            cross_scores: List[float] = await loop.run_in_executor(
                None,
                lambda: self._model.predict(pairs).tolist(),  # type: ignore[union-attr]
            )
            # Combine cross-encoder score with original retrieval score
            combined = [
                (chunk, 0.7 * cs + 0.3 * rs)
                for chunk, cs, rs in zip(chunks, cross_scores, scores)
            ]
            combined.sort(key=lambda x: x[1], reverse=True)
            return combined[:top_k]
        except Exception as e:
            logger.warning("CrossEncoder prediction failed: %s", e)
            return self._rerank_by_score(chunks, scores, top_k)

    @staticmethod
    def _rerank_by_score(
        chunks: List[Chunk],
        scores: List[float],
        top_k: int,
    ) -> List[Tuple[Chunk, float]]:
        paired = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
        return paired[:top_k]


def reciprocal_rank_fusion(
    dense_results: List[Tuple[str, float]],
    sparse_results: List[Tuple[str, float]],
    k: int = 60,
    alpha: float = 0.7,
) -> List[Tuple[str, float]]:
    """Fuse dense and sparse rankings using RRF with configurable alpha weight."""
    scores: dict[str, float] = {}

    for rank, (doc_id, raw_score) in enumerate(dense_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + alpha * raw_score * (1.0 / (k + rank + 1))

    for rank, (doc_id, raw_score) in enumerate(sparse_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + (1 - alpha) * raw_score * (1.0 / (k + rank + 1))

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
