from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    text_excerpt: str
    relevance_score: float
    chunk_index: int

    @field_validator("relevance_score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    hybrid_alpha: float = Field(default=0.7, ge=0.0, le=1.0)
    use_graph: bool = True
    stream: bool = False
    filters: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query must not be empty")
        if len(v) > 2000:
            raise ValueError("Query must not exceed 2000 characters")
        return v


class EvaluationMetrics(BaseModel):
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_recall: float = 0.0
    context_precision: float = 0.0

    @field_validator("faithfulness", "answer_relevancy", "context_recall", "context_precision")
    @classmethod
    def metric_in_range(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class QueryResponse(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    metrics: EvaluationMetrics = Field(default_factory=EvaluationMetrics)
    model_used: str = ""
    latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    graph_entities: List[str] = Field(default_factory=list)


class StreamChunk(BaseModel):
    type: str
    content: str
    query_id: Optional[str] = None
    citations: Optional[List[Citation]] = None
    metrics: Optional[EvaluationMetrics] = None


class UsageStats(BaseModel):
    total_queries: int = 0
    queries_today: int = 0
    total_documents: int = 0
    total_chunks: int = 0
    avg_latency_ms: float = 0.0
    queries_per_day: List[Dict[str, Any]] = Field(default_factory=list)


class QualityMetrics(BaseModel):
    avg_faithfulness: float = 0.0
    avg_answer_relevancy: float = 0.0
    avg_context_recall: float = 0.0
    avg_context_precision: float = 0.0
    metrics_over_time: List[Dict[str, Any]] = Field(default_factory=list)
    sample_size: int = 0
