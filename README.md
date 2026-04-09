# DocuMind

Production RAG (Retrieval-Augmented Generation) engine. Upload PDF, TXT, or Markdown documents; query them in natural language via Claude.

## Architecture

```
Upload → Chunk → Embed (MiniLM) → ChromaDB
Query  → Embed → Retrieve top-K → Claude → Answer + Sources
```

## Installation & Running

### Prerequisites
- Python 3.11+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### Quick Start
```bash
git clone https://github.com/boyedandtoyed/documind.git
cd documind

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_key_here

# Run
uvicorn documind.api:app --reload --port 8000
# API docs at http://localhost:8000/docs
```

### Docker
```bash
ANTHROPIC_API_KEY=your_key docker compose up --build
```

### Running Tests
```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + document count |
| `/documents/upload` | POST | Upload PDF/TXT/MD file |
| `/query` | POST | RAG query with sources |

### Example
```bash
# Upload a document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@paper.pdf"

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main findings?"}'
```

## Tech Stack
FastAPI · Pydantic v2 · ChromaDB · Sentence Transformers · Anthropic Claude · PyPDF · Tenacity
