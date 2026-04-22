from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GraphStoreService:
    """Neo4j-backed knowledge graph for entity extraction and graph-augmented retrieval."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self._driver: Optional[object] = None
        self._available = False

    async def initialize(self) -> None:
        try:
            from neo4j import AsyncGraphDatabase  # type: ignore
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            await self._verify_connectivity()
            await self._create_indexes()
            self._available = True
            logger.info("Neo4j graph store initialized.")
        except Exception as e:
            logger.warning("Neo4j not available (%s); graph enrichment disabled.", e)
            self._available = False

    async def _verify_connectivity(self) -> None:
        async with self._driver.session() as session:  # type: ignore[union-attr]
            await session.run("RETURN 1")

    async def _create_indexes(self) -> None:
        async with self._driver.session() as session:  # type: ignore[union-attr]
            await session.run(
                "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)"
            )
            await session.run(
                "CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.id)"
            )

    async def store_document_graph(
        self,
        document_id: str,
        document_name: str,
        chunks_with_entities: List[Tuple[str, List[str]]],
    ) -> None:
        """Store document node and its entity relationships in Neo4j."""
        if not self._available or self._driver is None:
            return
        async with self._driver.session() as session:  # type: ignore[union-attr]
            await session.execute_write(
                self._create_document_and_entities,
                document_id,
                document_name,
                chunks_with_entities,
            )

    @staticmethod
    async def _create_document_and_entities(
        tx: Any,
        document_id: str,
        document_name: str,
        chunks_with_entities: List[Tuple[str, List[str]]],
    ) -> None:
        await tx.run(
            "MERGE (d:Document {id: $id}) SET d.name = $name",
            id=document_id,
            name=document_name,
        )
        for chunk_id, entities in chunks_with_entities:
            await tx.run(
                "MERGE (c:Chunk {id: $id}) SET c.document_id = $doc_id",
                id=chunk_id,
                doc_id=document_id,
            )
            await tx.run(
                "MATCH (d:Document {id: $doc_id}), (c:Chunk {id: $chunk_id}) "
                "MERGE (d)-[:HAS_CHUNK]->(c)",
                doc_id=document_id,
                chunk_id=chunk_id,
            )
            for entity in entities:
                await tx.run(
                    "MERGE (e:Entity {name: $name})",
                    name=entity.lower(),
                )
                await tx.run(
                    "MATCH (c:Chunk {id: $chunk_id}), (e:Entity {name: $name}) "
                    "MERGE (c)-[:MENTIONS]->(e)",
                    chunk_id=chunk_id,
                    name=entity.lower(),
                )

    async def get_related_chunks(self, query_entities: List[str]) -> List[str]:
        """Return chunk IDs related to the given entities via the knowledge graph."""
        if not self._available or self._driver is None or not query_entities:
            return []
        async with self._driver.session() as session:  # type: ignore[union-attr]
            result = await session.run(
                """
                MATCH (e:Entity)-[:MENTIONS]-(c:Chunk)-[:HAS_CHUNK]-(d:Document)
                WHERE e.name IN $entities
                RETURN DISTINCT c.id AS chunk_id, count(e) AS relevance
                ORDER BY relevance DESC
                LIMIT 20
                """,
                entities=[e.lower() for e in query_entities],
            )
            records = await result.data()
            return [r["chunk_id"] for r in records]

    async def delete_document(self, document_id: str) -> None:
        if not self._available or self._driver is None:
            return
        async with self._driver.session() as session:  # type: ignore[union-attr]
            await session.run(
                "MATCH (d:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk) "
                "DETACH DELETE c, d",
                id=document_id,
            )

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()  # type: ignore[union-attr]

    @staticmethod
    def extract_entities(text: str) -> List[str]:
        """Lightweight rule-based entity extraction (proper nouns, capitalized phrases)."""
        # Match sequences of capitalized words (≥2 chars), excluding sentence starters
        pattern = re.compile(r"\b([A-Z][a-z]{1,}(?:\s+[A-Z][a-z]{1,})*)\b")
        candidates = pattern.findall(text)

        # Filter common English starters / stop words
        stop_starters = {
            "The", "This", "These", "That", "Those", "A", "An", "In", "On",
            "At", "By", "For", "Of", "To", "And", "Or", "But", "If", "When",
            "Where", "Which", "Who", "What", "How", "Why", "With", "From",
        }
        entities = [
            e for e in candidates
            if e not in stop_starters and len(e) > 2
        ]
        # Deduplicate preserving order
        seen: set[str] = set()
        unique: List[str] = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique.append(e)
        return unique[:30]
