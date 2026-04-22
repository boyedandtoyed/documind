# DocuMind

**Fully local RAG engine. No cloud. No API keys. Runs on your own GPU.**

Upload documents, ask questions, get cited answers — powered by `gemma3:27b` and `nomic-embed-text` running on Ollama, with hybrid search (Qdrant), a knowledge graph (Neo4j), and automatic quality evaluation (RAGAS). One command to start everything.

---

## Architecture

```
PDF / DOCX / TXT
       │
       ▼
┌─────────────┐     ┌──────────────────┐
│  Ingestion  │────▶│  Semantic Chunks │
└─────────────┘     └────────┬─────────┘
                             │
                  ┌──────────▼──────────┐
                  │  nomic-embed-text   │  (Ollama / P40)
                  └──────────┬──────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
        Qdrant            Neo4j           BM25 Index
      (dense vec)      (knowledge       (sparse vec)
                         graph)
            └────────────────┼────────────────┘
                             │  RRF Fusion
                             ▼
                  ┌──────────────────┐
                  │  LangGraph RAG   │
                  │  Pipeline        │
                  │  gemma3:27b      │  (Ollama / P40)
                  └──────────┬───────┘
                             │
                  ┌──────────▼───────────┐
                  │  RAGAS Evaluation    │
                  │  faithfulness score  │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │  Answer + Citations  │
                  │  + Quality Badge     │
                  └──────────────────────┘
```

---

## Stack

| Layer | Technology |
|---|---|
| LLM | `gemma3:27b` via Ollama |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector DB | Qdrant (hybrid: dense + BM25 sparse, RRF fusion) |
| Knowledge Graph | Neo4j 5 + APOC |
| Reranker | BGE-reranker-base (CPU cross-encoder) |
| Evaluation | RAGAS metrics stored in SQLite |
| Backend | FastAPI · Python 3.12 · Pydantic v2 |
| Frontend | Next.js 15 · TypeScript strict · Tailwind CSS · Recharts |
| Orchestration | Docker Compose |

---

## Hardware Requirements

| Component | Minimum | Tested On |
|---|---|---|
| GPU VRAM | 16 GB | NVIDIA Tesla P40 (24 GB) |
| System RAM | 16 GB | 40 GB |
| Storage | 20 GB free | — |
| OS | Ubuntu 22.04 | Dell T5810 |

> **Note**: `gemma3:27b` requires ~18 GB VRAM. On 16 GB cards use `gemma3:12b` instead (set `LLM_MODEL=gemma3:12b` in `.env`).

---

## Quick Start

**1. Pull models into Ollama (runs on host, outside Docker):**
```bash
ollama pull gemma3:27b
ollama pull nomic-embed-text
```

**2. Copy environment file and start all services:**
```bash
cp .env.example .env
docker compose up --build
```

**3. Open the UI:**
```
http://localhost:3000
```

The backend API + docs are at `http://localhost:8000/docs`.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Ollama reachability + model status |
| `POST` | `/api/v1/documents/upload` | Ingest PDF / DOCX / TXT |
| `GET` | `/api/v1/documents` | List indexed documents |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + vectors |
| `POST` | `/api/v1/query` | Full RAG query (JSON response) |
| `POST` | `/api/v1/query/stream` | Streaming RAG via SSE |
| `GET` | `/api/v1/analytics/usage` | Query counts, latency stats |
| `GET` | `/api/v1/analytics/quality` | RAGAS metrics over time |

### Query request body
```json
{
  "query": "What are the main findings?",
  "top_k": 10,
  "hybrid_alpha": 0.7,
  "use_graph": true,
  "stream": false,
  "filters": {}
}
```

### Query response
```json
{
  "query_id": "uuid",
  "answer": "Based on [Source 1]...",
  "citations": [
    {
      "document_name": "report.pdf",
      "page_number": 3,
      "text_excerpt": "...",
      "relevance_score": 0.92
    }
  ],
  "metrics": {
    "faithfulness": 0.87,
    "answer_relevancy": 0.91,
    "context_recall": 0.80,
    "context_precision": 0.75
  },
  "model_used": "gemma3:27b",
  "latency_ms": 4320.5
}
```

---

## Configuration

All settings live in `.env` (copy from `.env.example`). Key variables:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434  # Ollama on host
LLM_MODEL=gemma3:27b
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
HYBRID_ALPHA=0.7    # 1.0 = pure dense, 0.0 = pure sparse
TOP_K=10
RERANK_TOP_K=5
```

---

## How It Works

**Ingestion**: Files are parsed (pdfplumber for PDFs, python-docx for DOCX), split by a semantic chunker (sentence-boundary aware with sliding-window overlap), embedded with `nomic-embed-text`, and stored in Qdrant with both dense and BM25 sparse vectors. Entity relationships are extracted and stored in Neo4j.

**Retrieval**: At query time, dense similarity search and BM25 sparse search run in parallel in Qdrant, fused with Reciprocal Rank Fusion (RRF). The top results are reranked by a BGE cross-encoder (CPU). Neo4j entity lookup boosts chunks related to named entities in the query.

**Generation**: `gemma3:27b` generates the answer with strict source-grounding instructions. Responses stream token-by-token via SSE.

**Evaluation**: After each query, the Ollama LLM judges faithfulness, relevancy, recall, and precision, persisting scores to SQLite. The analytics dashboard shows trends over time.

---

## Project Structure

```
documind/
├── backend/
│   ├── app/
│   │   ├── config.py           # Pydantic settings with Ollama defaults
│   │   ├── main.py             # FastAPI app + /health (pings Ollama)
│   │   ├── routers/            # documents · query · analytics
│   │   ├── services/
│   │   │   ├── embeddings.py   # OllamaEmbeddings (nomic-embed-text)
│   │   │   ├── rag_pipeline.py # LangGraph pipeline + ChatOllama
│   │   │   ├── vector_store.py # Qdrant hybrid search + RRF
│   │   │   ├── graph_store.py  # Neo4j entity extraction
│   │   │   └── evaluator.py    # RAGAS metrics → SQLite
│   │   └── utils/
│   │       ├── chunker.py      # Semantic chunking
│   │       └── reranker.py     # BGE cross-encoder
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                    # Next.js 15 App Router
│   ├── components/
│   │   ├── chat/               # ChatInterface, MessageBubble, CitationCard
│   │   ├── documents/          # UploadZone, DocumentCard, DocumentList
│   │   └── analytics/          # MetricsGrid, QualityChart, UsageStats
│   ├── hooks/                  # useChat, useDocuments, useAnalytics
│   ├── lib/                    # api.ts, streaming.ts (SSE)
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## License

MIT
