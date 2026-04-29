from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, TypedDict

from app.models.document import Chunk
from app.models.query import Citation, EvaluationMetrics, QueryRequest, QueryResponse, StreamChunk
from app.services.embeddings import EmbeddingService
from app.services.evaluator import EvaluatorService
from app.services.graph_store import GraphStoreService
from app.services.vector_store import VectorStoreService
from app.utils.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are DocuMind, an expert AI assistant. Answer the user's question "
    "using ONLY the provided source contexts. Be precise and cite source numbers "
    "like [Source 1] when referencing information. If the answer is not in the "
    "contexts, say so honestly."
)


class PipelineState(TypedDict, total=False):
    query: str
    query_id: str
    top_k: int
    hybrid_alpha: float
    use_graph: bool
    filters: Dict[str, Any]
    started_at: float
    latency_ms: float
    retrieved: List[tuple]
    query_embedding: List[float]
    reranked: List[tuple]
    graph_entities: List[str]
    graph_chunk_ids: List[str]
    answer: str
    citations: List[Citation]
    contexts: List[str]
    metrics: EvaluationMetrics


class RAGPipeline:
    """
    LangGraph-style pipeline:
    retrieve → rerank → graph_enrich → generate → evaluate
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
        graph_store: GraphStoreService,
        evaluator: EvaluatorService,
        ollama_base_url: str = "http://host.docker.internal:11434",
        llm_model: str = "gemma3:27b",
        rerank_top_k: int = 5,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.evaluator = evaluator
        self.llm_model = llm_model
        self.ollama_base_url = ollama_base_url
        self.reranker = CrossEncoderReranker()
        self.rerank_top_k = rerank_top_k
        self._llm = None
        self._graph = self._build_graph()

    def _build_graph(self) -> object:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(PipelineState)
        graph.add_node("retrieve", self.node_retrieve)
        graph.add_node("rerank", self.node_rerank)
        graph.add_node("graph_enrich", self.node_graph_enrich)
        graph.add_node("generate", self.node_generate)
        graph.add_node("evaluate", self.node_evaluate)
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "rerank")
        graph.add_edge("rerank", "graph_enrich")
        graph.add_edge("graph_enrich", "generate")
        graph.add_edge("generate", "evaluate")
        graph.add_edge("evaluate", END)
        return graph.compile()

    def _get_llm(self) -> object:
        if self._llm is None:
            from langchain_ollama import ChatOllama
            self._llm = ChatOllama(
                model=self.llm_model,
                base_url=self.ollama_base_url,
                temperature=0.1,
                num_ctx=8192,
            )
        return self._llm

    # ── Pipeline Nodes ──────────────────────────────────────────────────────────

    async def node_retrieve(self, state: PipelineState) -> PipelineState:
        query: str = state["query"]
        top_k: int = state.get("top_k", 10)
        alpha: float = state.get("hybrid_alpha", 0.7)
        filters: Dict[str, Any] = state.get("filters", {})

        query_embedding = await self.embedding_service.embed_query(query)
        raw_results = await self.vector_store.hybrid_search(
            query_embedding=query_embedding,
            query_text=query,
            top_k=top_k,
            alpha=alpha,
            filters=filters,
        )
        state["retrieved"] = raw_results
        state["query_embedding"] = query_embedding
        logger.debug("Retrieved %d chunks for query.", len(raw_results))
        return state

    async def node_rerank(self, state: PipelineState) -> PipelineState:
        query: str = state["query"]
        raw_results: List[tuple] = state.get("retrieved", [])

        if not raw_results:
            state["reranked"] = []
            return state

        chunks_proxy = [_PayloadChunk(payload=r[0]) for r in raw_results]
        scores = [r[1] for r in raw_results]

        reranked = await self.reranker.rerank(
            query=query,
            chunks=chunks_proxy,  # type: ignore[arg-type]
            scores=scores,
            top_k=self.rerank_top_k,
        )
        state["reranked"] = reranked
        return state

    async def node_graph_enrich(self, state: PipelineState) -> PipelineState:
        if not state.get("use_graph", True):
            return state

        query: str = state["query"]
        reranked: List[tuple] = state.get("reranked", [])

        query_entities = GraphStoreService.extract_entities(query)
        state["graph_entities"] = query_entities

        if query_entities:
            graph_chunk_ids = await self.graph_store.get_related_chunks(query_entities)
            state["graph_chunk_ids"] = graph_chunk_ids

            if graph_chunk_ids:
                id_set = set(graph_chunk_ids[:5])
                boosted = []
                for chunk, score in reranked:
                    payload_id = chunk.payload.get("id", "") if isinstance(chunk, _PayloadChunk) else ""
                    boost = 1.15 if payload_id in id_set else 1.0
                    boosted.append((chunk, score * boost))
                boosted.sort(key=lambda x: x[1], reverse=True)
                state["reranked"] = boosted

        return state

    async def node_generate(self, state: PipelineState) -> PipelineState:
        query: str = state["query"]
        reranked: List[tuple] = state.get("reranked", [])

        if not reranked:
            state["answer"] = "I couldn't find relevant information to answer your question."
            state["citations"] = []
            state["contexts"] = []
            return state

        context_parts: List[str] = []
        citations: List[Citation] = []

        for i, (chunk, score) in enumerate(reranked):
            payload = chunk.payload if isinstance(chunk, _PayloadChunk) else {}
            text = payload.get("text", "")
            context_parts.append(f"[Source {i+1}] {text}")
            citations.append(
                Citation(
                    chunk_id=payload.get("id", str(i)),
                    document_id=payload.get("document_id", ""),
                    document_name=payload.get("document_name", "Unknown"),
                    page_number=payload.get("page_number"),
                    text_excerpt=text[:300],
                    relevance_score=min(1.0, max(0.0, score)),
                    chunk_index=payload.get("chunk_index", i),
                )
            )

        context_text = "\n\n".join(context_parts)
        answer = await self._call_llm(query, context_text)
        state["answer"] = answer
        state["citations"] = citations
        state["contexts"] = [c.text_excerpt for c in citations]
        return state

    async def node_evaluate(self, state: PipelineState) -> PipelineState:
        query_id: str = state.get("query_id", "")
        query: str = state["query"]
        answer: str = state.get("answer", "")
        contexts: List[str] = state.get("contexts", [])
        latency_ms: float = state.get("latency_ms", 0.0)
        if not latency_ms and state.get("started_at"):
            latency_ms = (time.monotonic() - state["started_at"]) * 1000
            state["latency_ms"] = latency_ms

        asyncio.create_task(
            self.evaluator.evaluate_async(
                query_id=query_id,
                query=query,
                answer=answer,
                contexts=contexts,
                latency_ms=latency_ms,
            )
        )
        metrics = EvaluatorService._heuristic_evaluate(query, answer, contexts)
        state["metrics"] = metrics
        return state

    # ── Public Interface ────────────────────────────────────────────────────────

    async def run(self, request: QueryRequest, query_id: str) -> QueryResponse:
        start = time.monotonic()
        state = PipelineState(
            query=request.query,
            query_id=query_id,
            top_k=request.top_k,
            hybrid_alpha=request.hybrid_alpha,
            use_graph=request.use_graph,
            filters=request.filters,
            started_at=start,
        )

        state = await self._graph.ainvoke(state)  # type: ignore[attr-defined]

        latency_ms = state.get("latency_ms", (time.monotonic() - start) * 1000)

        return QueryResponse(
            query_id=query_id,
            query=request.query,
            answer=state.get("answer", ""),
            citations=state.get("citations", []),
            metrics=state.get("metrics", EvaluationMetrics()),
            model_used=self.llm_model,
            latency_ms=round(latency_ms, 1),
            graph_entities=state.get("graph_entities", []),
        )

    async def stream(
        self,
        request: QueryRequest,
        query_id: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        start = time.monotonic()
        state = PipelineState(
            query=request.query,
            query_id=query_id,
            top_k=request.top_k,
            hybrid_alpha=request.hybrid_alpha,
            use_graph=request.use_graph,
            filters=request.filters,
        )

        for node in [self.node_retrieve, self.node_rerank, self.node_graph_enrich]:
            state = await node(state)

        yield StreamChunk(type="start", content="", query_id=query_id)

        reranked: List[tuple] = state.get("reranked", [])
        citations: List[Citation] = []
        contexts: List[str] = []
        full_answer: List[str] = []

        if not reranked:
            yield StreamChunk(type="token", content="I couldn't find relevant information.")
        else:
            context_parts: List[str] = []
            for i, (chunk, score) in enumerate(reranked):
                payload = chunk.payload if isinstance(chunk, _PayloadChunk) else {}
                text = payload.get("text", "")
                context_parts.append(f"[Source {i+1}] {text}")
                citations.append(
                    Citation(
                        chunk_id=payload.get("id", str(i)),
                        document_id=payload.get("document_id", ""),
                        document_name=payload.get("document_name", "Unknown"),
                        page_number=payload.get("page_number"),
                        text_excerpt=text[:300],
                        relevance_score=min(1.0, max(0.0, score)),
                        chunk_index=payload.get("chunk_index", i),
                    )
                )
            contexts = [c.text_excerpt for c in citations]

            async for token in self._stream_llm(request.query, "\n\n".join(context_parts)):
                full_answer.append(token)
                yield StreamChunk(type="token", content=token)

        latency_ms = (time.monotonic() - start) * 1000
        answer = "".join(full_answer)
        metrics = EvaluatorService._heuristic_evaluate(request.query, answer, contexts)

        asyncio.create_task(
            self.evaluator.evaluate_async(
                query_id=query_id,
                query=request.query,
                answer=answer,
                contexts=contexts,
                latency_ms=latency_ms,
            )
        )

        yield StreamChunk(
            type="done",
            content="",
            query_id=query_id,
            citations=citations,
            metrics=metrics,
        )

    # ── LLM Helpers ────────────────────────────────────────────────────────────

    async def _call_llm(self, query: str, context: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = self._get_llm()
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
        ]
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(None, llm.invoke, messages)  # type: ignore[union-attr]
            return response.content  # type: ignore[return-value]
        except Exception as e:
            logger.error("LLM generation error: %s", e)
            raise

    async def _stream_llm(self, query: str, context: str) -> AsyncGenerator[str, None]:
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = self._get_llm()
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
        ]
        try:
            async for chunk in llm.astream(messages):  # type: ignore[union-attr]
                token = chunk.content
                if token:
                    yield token
        except Exception as e:
            logger.error("LLM streaming error: %s", e)
            raise


class _PayloadChunk:
    """Thin wrapper so cross-encoder can access .text on a Qdrant payload dict."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        self.text = payload.get("text", "")
        self.id = payload.get("id", "")
