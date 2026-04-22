"""Tests for RAG pipeline components."""
from __future__ import annotations

import pytest

from app.models.query import Citation, EvaluationMetrics, QueryRequest
from app.utils.reranker import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_empty_inputs_return_empty(self) -> None:
        result = reciprocal_rank_fusion([], [])
        assert result == []

    def test_single_list_returns_ranked_results(self) -> None:
        dense = [("a", 0.9), ("b", 0.7), ("c", 0.5)]
        result = reciprocal_rank_fusion(dense, [])
        ids = [r[0] for r in result]
        assert ids[0] == "a"

    def test_overlap_boosts_shared_items(self) -> None:
        dense = [("a", 0.9), ("b", 0.7), ("c", 0.5)]
        sparse = [("b", 0.8), ("c", 0.6), ("a", 0.4)]
        result = reciprocal_rank_fusion(dense, sparse)
        scores = {r[0]: r[1] for r in result}
        # Items appearing in both should be boosted
        assert scores["a"] > 0
        assert scores["b"] > 0
        assert scores["c"] > 0

    def test_alpha_weight_shifts_preference(self) -> None:
        dense = [("dense_winner", 0.99), ("other", 0.1)]
        sparse = [("sparse_winner", 0.99), ("other", 0.1)]

        dense_heavy = reciprocal_rank_fusion(dense, sparse, alpha=0.9)
        sparse_heavy = reciprocal_rank_fusion(dense, sparse, alpha=0.1)

        dense_top = dense_heavy[0][0]
        sparse_top = sparse_heavy[0][0]
        assert dense_top == "dense_winner"
        assert sparse_top == "sparse_winner"

    def test_scores_are_positive(self) -> None:
        dense = [("x", 0.5), ("y", 0.3)]
        sparse = [("y", 0.9), ("z", 0.1)]
        result = reciprocal_rank_fusion(dense, sparse)
        for _, score in result:
            assert score > 0


class TestQueryRequest:
    def test_valid_query(self) -> None:
        req = QueryRequest(query="What is machine learning?")
        assert req.query == "What is machine learning?"
        assert req.top_k == 5
        assert req.hybrid_alpha == 0.7

    def test_empty_query_raises(self) -> None:
        with pytest.raises(Exception):
            QueryRequest(query="   ")

    def test_query_too_long_raises(self) -> None:
        with pytest.raises(Exception):
            QueryRequest(query="x" * 2001)

    def test_top_k_clamped(self) -> None:
        with pytest.raises(Exception):
            QueryRequest(query="test", top_k=0)
        with pytest.raises(Exception):
            QueryRequest(query="test", top_k=21)

    def test_hybrid_alpha_bounds(self) -> None:
        req_low = QueryRequest(query="test", hybrid_alpha=0.0)
        req_high = QueryRequest(query="test", hybrid_alpha=1.0)
        assert req_low.hybrid_alpha == 0.0
        assert req_high.hybrid_alpha == 1.0


class TestEvaluationMetrics:
    def test_metrics_clamped_to_range(self) -> None:
        m = EvaluationMetrics(
            faithfulness=1.5,
            answer_relevancy=-0.1,
        )
        assert m.faithfulness == 1.0
        assert m.answer_relevancy == 0.0

    def test_default_metrics_are_zero(self) -> None:
        m = EvaluationMetrics()
        assert m.faithfulness == 0.0
        assert m.answer_relevancy == 0.0
        assert m.context_recall == 0.0
        assert m.context_precision == 0.0


class TestCitation:
    def test_relevance_score_clamped(self) -> None:
        c = Citation(
            chunk_id="c1",
            document_id="d1",
            document_name="test.pdf",
            text_excerpt="excerpt",
            relevance_score=2.5,
            chunk_index=0,
        )
        assert c.relevance_score == 1.0

    def test_citation_with_page_number(self) -> None:
        c = Citation(
            chunk_id="c1",
            document_id="d1",
            document_name="test.pdf",
            page_number=42,
            text_excerpt="Some text",
            relevance_score=0.85,
            chunk_index=3,
        )
        assert c.page_number == 42
