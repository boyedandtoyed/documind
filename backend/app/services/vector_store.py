from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.models.document import Chunk
from app.utils.reranker import reciprocal_rank_fusion

logger = logging.getLogger(__name__)

SPARSE_VECTOR_NAME = "sparse"
DENSE_VECTOR_NAME = "dense"


class VectorStoreService:
    """Qdrant-backed hybrid search: dense embeddings + sparse BM25, fused with RRF."""

    def __init__(
        self,
        url: str,
        collection_name: str,
        embedding_dim: int = 1536,
        api_key: str = "",
    ) -> None:
        self.url = url
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.api_key = api_key
        self._client: Optional[object] = None

    async def initialize(self) -> None:
        try:
            from qdrant_client import AsyncQdrantClient  # type: ignore
            from qdrant_client.models import (  # type: ignore
                Distance,
                SparseVectorParams,
                VectorParams,
                VectorsConfig,
            )
            kwargs: Dict[str, Any] = {"url": self.url}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = AsyncQdrantClient(**kwargs)
            await self._ensure_collection()
            logger.info("VectorStore initialized (collection=%s)", self.collection_name)
        except ImportError:
            logger.error("qdrant-client not installed.")
            raise

    async def _ensure_collection(self) -> None:
        from qdrant_client.models import (  # type: ignore
            Distance,
            SparseVectorParams,
            VectorParams,
            VectorsConfig,
        )
        client = self._client  # type: ignore[assignment]
        collections = await client.get_collections()
        names = [c.name for c in collections.collections]
        if self.collection_name not in names:
            await client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    DENSE_VECTOR_NAME: VectorParams(
                        size=self.embedding_dim, distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    SPARSE_VECTOR_NAME: SparseVectorParams()
                },
            )
            logger.info("Created Qdrant collection: %s", self.collection_name)

    async def upsert_chunks(self, chunks: List[Chunk]) -> None:
        """Upsert chunks with both dense and sparse vectors."""
        if not chunks or self._client is None:
            return
        from qdrant_client.models import PointStruct, SparseVector  # type: ignore

        points = []
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            sparse_vec = self._build_sparse_vector(chunk.text)
            payload: Dict[str, Any] = {
                "text": chunk.text,
                "document_id": chunk.metadata.document_id,
                "document_name": chunk.metadata.document_name,
                "chunk_index": chunk.metadata.chunk_index,
                "page_number": chunk.metadata.page_number,
                "start_char": chunk.metadata.start_char,
                "end_char": chunk.metadata.end_char,
            }
            points.append(
                PointStruct(
                    id=chunk.id,
                    vector={
                        DENSE_VECTOR_NAME: chunk.embedding,
                        SPARSE_VECTOR_NAME: SparseVector(
                            indices=sparse_vec["indices"],
                            values=sparse_vec["values"],
                        ),
                    },
                    payload=payload,
                )
            )
        await self._client.upsert(collection_name=self.collection_name, points=points)  # type: ignore[union-attr]

    async def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 10,
        alpha: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Dense + sparse search fused with RRF."""
        if self._client is None:
            return []
        from qdrant_client.models import Filter, FieldCondition, MatchValue, SparseVector, NamedVector  # type: ignore

        qdrant_filter = self._build_filter(filters) if filters else None
        sparse_query = self._build_sparse_vector(query_text)

        # Dense search
        dense_results = await self._client.query_points(  # type: ignore[union-attr]
            collection_name=self.collection_name,
            query=query_embedding,
            using=DENSE_VECTOR_NAME,
            limit=top_k * 2,
            with_payload=True,
            query_filter=qdrant_filter,
        )

        # Sparse search
        sparse_results = await self._client.query_points(  # type: ignore[union-attr]
            collection_name=self.collection_name,
            query=SparseVector(
                indices=sparse_query["indices"],
                values=sparse_query["values"],
            ),
            using=SPARSE_VECTOR_NAME,
            limit=top_k * 2,
            with_payload=True,
            query_filter=qdrant_filter,
        )

        dense_pairs = [(str(p.id), p.score) for p in dense_results.points]
        sparse_pairs = [(str(p.id), p.score) for p in sparse_results.points]

        fused = reciprocal_rank_fusion(dense_pairs, sparse_pairs, alpha=alpha)

        # Collect payloads
        id_to_payload: Dict[str, Any] = {}
        for p in dense_results.points:
            id_to_payload[str(p.id)] = p.payload
        for p in sparse_results.points:
            id_to_payload.setdefault(str(p.id), p.payload)

        output: List[Tuple[Dict[str, Any], float]] = []
        for doc_id, score in fused[:top_k]:
            if doc_id in id_to_payload:
                output.append(({"id": doc_id, **id_to_payload[doc_id]}, score))
        return output

    async def delete_by_document(self, document_id: str) -> None:
        if self._client is None:
            return
        from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore
        await self._client.delete(  # type: ignore[union-attr]
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
        )

    async def count_chunks(self) -> int:
        if self._client is None:
            return 0
        result = await self._client.count(collection_name=self.collection_name)  # type: ignore[union-attr]
        return result.count

    @staticmethod
    def _build_sparse_vector(text: str) -> Dict[str, Any]:
        """Simple TF-based sparse vector (BM25-like term weights)."""
        import hashlib

        tokens = text.lower().split()
        term_freq: Dict[int, float] = {}
        total = len(tokens) or 1
        for token in tokens:
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16) % (2**24)
            term_freq[h] = term_freq.get(h, 0) + 1
        # TF normalization
        indices = list(term_freq.keys())
        values = [math.log(1 + freq / total) for freq in term_freq.values()]
        return {"indices": indices, "values": values}

    @staticmethod
    def _build_filter(filters: Dict[str, Any]) -> Optional[object]:
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore
            conditions = []
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            return Filter(must=conditions) if conditions else None
        except Exception:
            return None
