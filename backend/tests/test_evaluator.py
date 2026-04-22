"""Tests for RAGAS evaluator service."""
from __future__ import annotations

import os
import tempfile

import pytest

from app.services.evaluator import EvaluatorService


class TestHeuristicEvaluator:
    def test_empty_contexts_returns_zero_metrics(self) -> None:
        metrics = EvaluatorService._heuristic_evaluate("query", "answer", [])
        assert metrics.faithfulness == 0.0
        assert metrics.answer_relevancy == 0.0

    def test_empty_answer_returns_zero_faithfulness(self) -> None:
        metrics = EvaluatorService._heuristic_evaluate("query", "", ["some context"])
        assert metrics.faithfulness == 0.0

    def test_perfect_overlap_scores_high(self) -> None:
        context = "machine learning is a subset of artificial intelligence"
        answer = "machine learning is a subset of artificial intelligence"
        query = "what is machine learning"
        metrics = EvaluatorService._heuristic_evaluate(query, answer, [context])
        assert metrics.faithfulness > 0.5

    def test_query_terms_in_answer_boost_relevancy(self) -> None:
        query = "what is neural network"
        answer = "a neural network is a computational model inspired by the brain"
        context = "neural networks are used in deep learning"
        metrics = EvaluatorService._heuristic_evaluate(query, answer, [context])
        assert metrics.answer_relevancy > 0.0

    def test_more_contexts_increase_recall(self) -> None:
        query = "q"
        answer = "a"
        few = EvaluatorService._heuristic_evaluate(query, answer, ["c1"])
        many = EvaluatorService._heuristic_evaluate(query, answer, ["c1", "c2", "c3", "c4", "c5"])
        assert many.context_recall >= few.context_recall

    def test_metrics_bounded_between_zero_and_one(self) -> None:
        metrics = EvaluatorService._heuristic_evaluate(
            query="test query here",
            answer="test answer here with some content",
            contexts=["test context document with test answer content here"],
        )
        for field in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
            value = getattr(metrics, field)
            assert 0.0 <= value <= 1.0, f"{field}={value} out of range"


@pytest.mark.asyncio
class TestEvaluatorService:
    async def test_initialize_creates_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            svc = EvaluatorService(db_path=db_path)
            await svc.initialize()
            assert os.path.exists(db_path)

    async def test_usage_stats_empty_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            svc = EvaluatorService(db_path=db_path)
            await svc.initialize()
            stats = await svc.get_usage_stats(total_documents=3, total_chunks=42)
            assert stats.total_queries == 0
            assert stats.total_documents == 3
            assert stats.total_chunks == 42

    async def test_quality_metrics_empty_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            svc = EvaluatorService(db_path=db_path)
            await svc.initialize()
            quality = await svc.get_quality_metrics()
            assert quality.avg_faithfulness == 0.0
            assert quality.sample_size == 0

    async def test_store_and_retrieve_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            svc = EvaluatorService(db_path=db_path)
            await svc.initialize()

            await svc._store_metrics(
                query_id="q1",
                query="What is RAG?",
                answer="RAG stands for Retrieval-Augmented Generation.",
                metrics=svc._heuristic_evaluate(
                    "What is RAG?",
                    "RAG stands for Retrieval-Augmented Generation.",
                    ["Retrieval-Augmented Generation is a technique."],
                ),
                latency_ms=123.4,
                context_count=1,
            )

            stats = await svc.get_usage_stats()
            assert stats.total_queries == 1
            assert stats.avg_latency_ms > 0
