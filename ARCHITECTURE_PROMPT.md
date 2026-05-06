# DocuMind — Architecture Primer for Claude Code Sessions

> Paste this at the start of any Claude Code session to save tokens and establish shared context fast.

## What This Project Is
Local-only RAG engine. No cloud APIs. Users upload PDFs/DOCX/TXT/MD, ask questions, get cited answers. Runs on a single Ubuntu server with a Tesla P40 GPU.

## Stack at a Glance
| Layer | Tech | Where |
|---|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind, Recharts | frontend/ |
| Backend API | FastAPI, Python 3.12, Pydantic v2 | backend/app/ |
| LLM + Embeddings | gemma4:26b + nomic-embed-text via Ollama | HOST (not Docker) |
| Vector DB | Qdrant (hybrid dense+sparse, RRF fusion) | Docker :6333 |
| Knowledge Graph | Neo4j 5 + APOC | Docker :7474/:7687 |
| RAG Pipeline | LangGraph (retrieve→rerank→graph_enrich→generate→evaluate) | backend/app/services/rag_pipeline.py |
| Reranker | BGE bge-reranker-base cross-encoder (CPU) | backend/app/utils/reranker.py |
| Evaluation | RAGAS-style LLM judge + SQLite fallback heuristics | backend/app/services/evaluator.py |
| Infra | Docker Compose, named volumes, documind-net | docker-compose.yml |

## File System Map
````
documind/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory + lifespan + /health
│   │   ├── config.py            # Pydantic Settings (reads .env)
│   │   ├── models/
│   │   │   ├── document.py      # Document, Chunk, ChunkMetadata, DocumentUploadResponse
│   │   │   └── query.py         # QueryRequest, QueryResponse, Citation, EvaluationMetrics, StreamChunk
│   │   ├── routers/
│   │   │   ├── documents.py     # POST /upload, GET /, GET /{id}, DELETE /{id}
│   │   │   ├── query.py         # POST /query, POST /query/stream (SSE)
│   │   │   └── analytics.py     # GET /analytics/usage, GET /analytics/quality
│   │   ├── services/
│   │   │   ├── ingestion.py     # PDF/DOCX/TXT/MD parser → List[Chunk]
│   │   │   ├── embeddings.py    # OllamaEmbeddings wrapper (nomic-embed-text, 768-dim)
│   │   │   ├── vector_store.py  # Qdrant: upsert_chunks, hybrid_search (dense+sparse→RRF), delete
│   │   │   ├── graph_store.py   # Neo4j: store_document_graph, get_related_chunks, extract_entities
│   │   │   ├── rag_pipeline.py  # LangGraph: PipelineState, 5-node graph, run() + stream()
│   │   │   └── evaluator.py     # RAGAS LLM judge + heuristic fallback + SQLite persistence
│   │   └── utils/
│   │       ├── chunker.py       # SemanticChunker: sentence-split + sliding window overlap
│   │       └── reranker.py      # CrossEncoderReranker (BGE) + reciprocal_rank_fusion()
│   ├── tests/
│   │   ├── test_evaluator.py
│   │   ├── test_ingestion.py
│   │   └── test_rag_pipeline.py
│   ├── Dockerfile               # python:3.12-slim, non-root appuser
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout, Inter+JetBrains fonts, Providers
│   │   ├── page.tsx             # Redirects / → /chat
│   │   ├── chat/page.tsx        # Chat page shell
│   │   ├── documents/page.tsx   # Document management page shell
│   │   └── analytics/page.tsx   # Analytics page shell
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx    # Main chat UI: input, message list, stop/clear
│   │   │   ├── MessageBubble.tsx    # User/assistant bubbles + citations accordion
│   │   │   ├── CitationCard.tsx     # Expandable source card with relevance bar
│   │   │   ├── QualityBadge.tsx     # Faithfulness score pill (green/amber/red)
│   │   │   └── StreamingMessage.tsx # SSE token stream with blinking cursor
│   │   ├── documents/
│   │   │   ├── UploadZone.tsx       # Drag-drop + click upload with progress states
│   │   │   ├── DocumentList.tsx     # Paginated document list
│   │   │   └── DocumentCard.tsx     # Per-doc card: status badge, delete with confirm
│   │   ├── analytics/
│   │   │   ├── MetricsGrid.tsx      # 4-card RAGAS metrics grid with color-coded bars
│   │   │   ├── QualityChart.tsx     # Recharts line chart: faithfulness/relevancy/recall over time
│   │   │   └── UsageStats.tsx       # Query counts, doc counts, avg latency
│   │   └── layout/
│   │       ├── Header.tsx           # Page title + Ollama live status indicator (polls /health)
│   │       └── Sidebar.tsx          # Collapsible desktop nav + BottomNav for mobile
│   ├── hooks/
│   │   ├── useChat.ts           # SSE streaming state machine + abort controller
│   │   ├── useDocuments.ts      # React Query: list, get, upload, delete mutations
│   │   └── useAnalytics.ts      # React Query: usage + quality metric polling
│   ├── lib/
│   │   ├── api.ts               # Typed fetch wrappers (documentsApi, queryApi, analyticsApi)
│   │   └── streaming.ts         # SSE parser: onToken / onDone / onError callbacks
│   ├── types/index.ts           # All shared TypeScript interfaces
│   └── Dockerfile               # node:20-alpine multi-stage, standalone output
├── docker-compose.yml           # qdrant, neo4j, backend, frontend + volumes + documind-net
├── .env.example                 # All env vars with defaults
└── .github/workflows/ci.yml     # pytest on push/PR

## Key Data Flows
1. Upload: POST /upload → IngestionService.process_file() → EmbeddingService.embed_texts() → VectorStoreService.upsert_chunks() + GraphStoreService.store_document_graph()
2. Query: POST /query → RAGPipeline.run() → [retrieve → rerank → graph_enrich → generate → evaluate] → QueryResponse with citations + metrics
3. Stream: POST /query/stream → RAGPipeline.stream() → SSE tokens → frontend StreamingMessage component
4. Analytics: GET /analytics/usage + /quality → EvaluatorService reads SQLite query_log table

## Critical Config
- EMBEDDING_DIM=768 (nomic-embed-text, hardcoded in VectorStoreService + EmbeddingService)
- Qdrant collection uses named vectors: "dense" (cosine) + "sparse" (BM25-like TF hash)
- _document_store: dict[str, Document] is IN-MEMORY in documents.py — no DB persistence for doc metadata (known limitation)
- Python 3.11+ required (ChromaDB wheel compat if ever switched; currently Qdrant so 3.12 is fine)
- LLM judge in evaluator falls back to heuristic token-overlap scoring on any Ollama error

## Known Limitations / Good Improvement Targets
- Document metadata lives only in memory (_document_store) — lost on restart
- No authentication layer
- No multi-user / multi-tenant isolation
- BM25 sparse vector is a simple TF hash, not true BM25 (could upgrade to rank-bm25)
- Entity extraction is regex proper-noun only (could add spaCy or GLiNER)
- Evaluation runs async fire-and-forget (evaluate_async) — metrics shown immediately are heuristic
- No document deduplication on upload
- Single Uvicorn worker (--workers 1) limits concurrency

## Ports (local dev / docker)
- 3000 → Frontend (Next.js)
- 8000 → Backend (FastAPI)
- 6333 → Qdrant REST + Dashboard
- 7474 → Neo4j Browser
- 7687 → Neo4j Bolt
- 11434 → Ollama (HOST only, not in Docker)

---

**How to use it:** When you start a new Claude Code session on DocuMind, just say:

> *"Read ARCHITECTURE_PROMPT.md first, then [your actual task]."*

Claude Code will load the graph in one shot instead of exploring the file tree manually — saves 3–5k tokens per session.
