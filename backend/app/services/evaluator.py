from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.query import EvaluationMetrics, QualityMetrics, UsageStats

logger = logging.getLogger(__name__)


class EvaluatorService:
    """RAGAS-inspired evaluation: faithfulness, answer relevancy, context recall.

    Runs async after each query and persists metrics to SQLite.
    Uses the local Ollama LLM as judge; falls back to heuristic scoring on error.
    """

    def __init__(
        self,
        db_path: str,
        ollama_base_url: str = "http://host.docker.internal:11434",
        llm_model: str = "gemma3:27b",
    ) -> None:
        self.db_path = db_path
        self.ollama_base_url = ollama_base_url
        self.llm_model = llm_model
        self._db_initialized = False
        self._llm = None

    def _get_llm(self) -> object:
        if self._llm is None:
            from langchain_ollama import ChatOllama
            self._llm = ChatOllama(
                model=self.llm_model,
                base_url=self.ollama_base_url,
                temperature=0,
                num_ctx=2048,
            )
        return self._llm

    async def initialize(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_db)
        self._db_initialized = True
        logger.info("Evaluator SQLite DB initialized: %s", self.db_path)

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    faithfulness REAL DEFAULT 0,
                    answer_relevancy REAL DEFAULT 0,
                    context_recall REAL DEFAULT 0,
                    context_precision REAL DEFAULT 0,
                    latency_ms REAL DEFAULT 0,
                    document_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_at ON query_log(created_at)"
            )
            conn.commit()

    async def evaluate_async(
        self,
        query_id: str,
        query: str,
        answer: str,
        contexts: List[str],
        latency_ms: float = 0.0,
    ) -> EvaluationMetrics:
        metrics = await self._compute_metrics(query, answer, contexts)
        await self._store_metrics(query_id, query, answer, metrics, latency_ms, len(contexts))
        return metrics

    async def _compute_metrics(
        self,
        query: str,
        answer: str,
        contexts: List[str],
    ) -> EvaluationMetrics:
        try:
            return await self._llm_evaluate(query, answer, contexts)
        except Exception as e:
            logger.warning("LLM evaluation failed (%s); using heuristics.", e)
            return self._heuristic_evaluate(query, answer, contexts)

    async def _llm_evaluate(
        self,
        query: str,
        answer: str,
        contexts: List[str],
    ) -> EvaluationMetrics:
        from langchain_core.messages import HumanMessage
        context_text = "\n---\n".join(contexts[:5])
        prompt = (
            "You are a RAG evaluation judge. Score the following on a scale of 0.0 to 1.0.\n\n"
            f"Query: {query}\n\n"
            f"Retrieved Contexts:\n{context_text}\n\n"
            f"Answer: {answer}\n\n"
            "Respond with a JSON object with these exact keys:\n"
            "- faithfulness: How factually consistent is the answer with the contexts? (0-1)\n"
            "- answer_relevancy: How relevant is the answer to the query? (0-1)\n"
            "- context_recall: How well do the contexts cover what's needed to answer? (0-1)\n"
            "- context_precision: What fraction of retrieved contexts were actually useful? (0-1)\n\n"
            "Return only valid JSON, nothing else."
        )
        llm = self._get_llm()
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, llm.invoke, [HumanMessage(content=prompt)]  # type: ignore[union-attr]
        )
        raw: str = response.content.strip()  # type: ignore[union-attr]
        # Strip markdown code fences if present
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        scores: Dict[str, Any] = json.loads(raw.strip())
        return EvaluationMetrics(
            faithfulness=float(scores.get("faithfulness", 0)),
            answer_relevancy=float(scores.get("answer_relevancy", 0)),
            context_recall=float(scores.get("context_recall", 0)),
            context_precision=float(scores.get("context_precision", 0)),
        )

    @staticmethod
    def _heuristic_evaluate(query: str, answer: str, contexts: List[str]) -> EvaluationMetrics:
        if not contexts or not answer:
            return EvaluationMetrics()

        query_tokens = set(query.lower().split())
        answer_tokens = set(answer.lower().split())
        context_tokens = set(" ".join(contexts).lower().split())

        faithfulness = (
            len(answer_tokens & context_tokens) / len(answer_tokens)
            if answer_tokens else 0.0
        )
        answer_relevancy = (
            min(1.0, len(query_tokens & answer_tokens) / len(query_tokens) * 2)
            if query_tokens else 0.0
        )
        context_recall = min(1.0, len(contexts) / 5.0)
        useful = sum(
            1 for ctx in contexts
            if any(t in answer.lower() for t in ctx.lower().split()[:20])
        )
        context_precision = useful / len(contexts) if contexts else 0.0

        return EvaluationMetrics(
            faithfulness=round(faithfulness, 3),
            answer_relevancy=round(answer_relevancy, 3),
            context_recall=round(context_recall, 3),
            context_precision=round(context_precision, 3),
        )

    async def _store_metrics(
        self,
        query_id: str,
        query: str,
        answer: str,
        metrics: EvaluationMetrics,
        latency_ms: float,
        context_count: int,
    ) -> None:
        if not self._db_initialized:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_metrics,
            query_id, query, answer, metrics, latency_ms, context_count,
        )

    def _write_metrics(
        self,
        query_id: str,
        query: str,
        answer: str,
        metrics: EvaluationMetrics,
        latency_ms: float,
        context_count: int,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO query_log
                   (query_id, query, answer, faithfulness, answer_relevancy,
                    context_recall, context_precision, latency_ms, document_count, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    query_id, query, answer,
                    metrics.faithfulness, metrics.answer_relevancy,
                    metrics.context_recall, metrics.context_precision,
                    latency_ms, context_count,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    async def get_usage_stats(self, total_documents: int = 0, total_chunks: int = 0) -> UsageStats:
        if not self._db_initialized:
            return UsageStats(total_documents=total_documents, total_chunks=total_chunks)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_usage, total_documents, total_chunks)

    def _read_usage(self, total_documents: int, total_chunks: int) -> UsageStats:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
            today = datetime.utcnow().date().isoformat()
            today_count = conn.execute(
                "SELECT COUNT(*) FROM query_log WHERE created_at >= ?", (today,)
            ).fetchone()[0]
            avg_latency = conn.execute("SELECT AVG(latency_ms) FROM query_log").fetchone()[0] or 0.0
            rows = conn.execute(
                """SELECT substr(created_at, 1, 10) as day, COUNT(*) as count
                   FROM query_log
                   WHERE created_at >= ?
                   GROUP BY day ORDER BY day""",
                ((datetime.utcnow() - timedelta(days=14)).isoformat(),),
            ).fetchall()

        return UsageStats(
            total_queries=total,
            queries_today=today_count,
            total_documents=total_documents,
            total_chunks=total_chunks,
            avg_latency_ms=round(avg_latency, 1),
            queries_per_day=[{"date": r[0], "count": r[1]} for r in rows],
        )

    async def get_quality_metrics(self) -> QualityMetrics:
        if not self._db_initialized:
            return QualityMetrics()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_quality)

    def _read_quality(self) -> QualityMetrics:
        with sqlite3.connect(self.db_path) as conn:
            avgs = conn.execute(
                """SELECT AVG(faithfulness), AVG(answer_relevancy),
                          AVG(context_recall), AVG(context_precision), COUNT(*)
                   FROM query_log"""
            ).fetchone()
            rows = conn.execute(
                """SELECT substr(created_at, 1, 10) as day,
                          AVG(faithfulness), AVG(answer_relevancy), AVG(context_recall)
                   FROM query_log
                   WHERE created_at >= ?
                   GROUP BY day ORDER BY day""",
                ((datetime.utcnow() - timedelta(days=30)).isoformat(),),
            ).fetchall()

        return QualityMetrics(
            avg_faithfulness=round(avgs[0] or 0, 3),
            avg_answer_relevancy=round(avgs[1] or 0, 3),
            avg_context_recall=round(avgs[2] or 0, 3),
            avg_context_precision=round(avgs[3] or 0, 3),
            sample_size=avgs[4] or 0,
            metrics_over_time=[
                {
                    "date": r[0],
                    "faithfulness": round(r[1] or 0, 3),
                    "answer_relevancy": round(r[2] or 0, 3),
                    "context_recall": round(r[3] or 0, 3),
                }
                for r in rows
            ],
        )
