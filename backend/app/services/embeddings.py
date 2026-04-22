from __future__ import annotations

import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Ollama-backed embeddings using nomic-embed-text via langchain-ollama."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://host.docker.internal:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url
        self._embeddings = None
        self._init_embeddings()

    def _init_embeddings(self) -> None:
        from langchain_ollama import OllamaEmbeddings
        self._embeddings = OllamaEmbeddings(
            model=self.model,
            base_url=self.base_url,
        )
        logger.info("OllamaEmbeddings initialized (model=%s, base_url=%s)", self.model, self.base_url)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts or self._embeddings is None:
            return []
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embeddings.embed_documents, texts)

    async def embed_query(self, query: str) -> List[float]:
        if self._embeddings is None:
            return []
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embeddings.embed_query, query)

    def get_dimension(self) -> int:
        return 768  # nomic-embed-text output dimension
