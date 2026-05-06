# DocuMind

**Fully local RAG engine. No cloud. No API keys. Runs on your own GPU.**

DocuMind is a production-grade RAG engine for private document intelligence. Upload PDFs, DOCX, TXT, or Markdown files, ask questions, and receive cited answers powered by `gemma4:26b` and `nomic-embed-text` through Ollama. Retrieval uses Qdrant hybrid search, a Neo4j knowledge graph, CPU reranking, and RAGAS-style quality metrics stored in SQLite.

## Architecture

```text
PDF/DOCX/TXT
    |
    v
+-------------+     +------------------+
|  Ingestion  |---->|  Semantic Chunks |
+-------------+     +--------+---------+
                             |
                  +----------v----------+
                  |  nomic-embed-text   |  (Ollama / P40)
                  +----------+----------+
                             |
            +----------------+----------------+
            v                v                v
        Qdrant            Neo4j           BM25 Index
      (dense vec)      (knowledge        (sparse vec)
                         graph)
            +----------------+----------------+
                             |  RRF Fusion
                             v
                  +------------------+
                  |  LangGraph RAG   |
                  |  Pipeline        |
                  |  gemma4:26b      |  (Ollama / P40)
                  +----------+-------+
                             |
                  +----------v-----------+
                  |  RAGAS Evaluation    |
                  |  faithfulness score  |
                  +----------+-----------+
                             |
                  +----------v-----------+
                  |  Answer + Citations  |
                  |  + Quality Badge     |
                  +----------------------+
```

## Stack

| Layer | Technology |
|---|---|
| LLM | `gemma4:26b` via Ollama |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector DB | Qdrant hybrid dense + sparse search |
| Knowledge Graph | Neo4j 5 + APOC |
| Pipeline | LangGraph |
| Reranker | BGE cross-encoder on CPU |
| Evaluation | RAGAS-compatible local Ollama judge + SQLite |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| Frontend | Next.js 14, TypeScript strict, Tailwind, Recharts |
| Runtime | Docker Compose, Ollama on host |

## Hardware

Tested target: Dell T5810, Ubuntu 22.04, 40 GB RAM, NVIDIA Tesla P40 24 GB VRAM.

Minimum: 16 GB VRAM. If `gemma4:26b` does not fit your GPU, set `LLM_MODEL=gemma3:12b` in `.env`.

## Quick Start

```bash
ollama pull gemma4:26b
ollama pull nomic-embed-text
cp .env.example .env && docker compose up --build
```

Open the app at `http://localhost:3000`. Backend docs are at `http://localhost:8000/docs`.

Ollama must run on the host at `http://localhost:11434`. Docker containers reach it through `host.docker.internal`, configured by `extra_hosts` in `docker-compose.yml`.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health plus Ollama reachability and model list |
| `POST` | `/api/v1/documents/upload` | Upload and ingest PDF, DOCX, TXT, or MD |
| `GET` | `/api/v1/documents` | List indexed documents |
| `GET` | `/api/v1/documents/{id}` | Get document metadata |
| `DELETE` | `/api/v1/documents/{id}` | Delete document, vectors, graph nodes, and upload file |
| `POST` | `/api/v1/query` | Run full RAG query and return JSON response |
| `POST` | `/api/v1/query/stream` | Stream answer tokens via SSE |
| `GET` | `/api/v1/analytics/usage` | Query counts, document counts, chunks, and latency |
| `GET` | `/api/v1/analytics/quality` | Faithfulness, relevancy, recall, and precision trends |

Example query:

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

## Deployment Notes

For `documind.binodtiwari.com`, point your reverse proxy to:

| Public path | Internal service |
|---|---|
| `/` | `http://127.0.0.1:3000` |
| `/api/` | `http://127.0.0.1:8000/api/` |
| `/health` | `http://127.0.0.1:8000/health` |
| `/docs` | `http://127.0.0.1:8000/docs` |

Set this before building for the subdomain:

```bash
NEXT_PUBLIC_API_URL=https://documind.binodtiwari.com/api/v1 docker compose up --build -d
```

## Project Structure

```text
documind/
  backend/
    app/
      main.py
      config.py
      routers/
      services/
      models/
      utils/
    tests/
    Dockerfile
    requirements.txt
  frontend/
    app/
    components/
    hooks/
    lib/
    types/
    Dockerfile
    package.json
    next.config.mjs
  docker-compose.yml
  .env.example
```

## License

MIT
