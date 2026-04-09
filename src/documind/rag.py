import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import settings
from .models import QueryResponse, SourceChunk
from .vectorstore import query_chunks

_client: anthropic.Anthropic | None = None

def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client

def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        source = f"[Source {i} — {c['filename']}"
        if c.get("page"):
            source += f", page {c['page']}"
        source += "]"
        parts.append(f"{source}\n{c['text']}")
    return "\n\n".join(parts)

SYSTEM_PROMPT = """You are DocuMind, a precise document Q&A assistant.
Answer questions using ONLY the provided context chunks.
If the context does not contain enough information, say so clearly.
Cite source numbers [1], [2], etc. when referencing specific passages.
Be concise and accurate."""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def answer_query(
    query: str,
    document_id: str | None = None,
    top_k: int | None = None,
) -> QueryResponse:
    k = top_k or settings.top_k
    raw_chunks = query_chunks(query, top_k=k, document_id=document_id)

    if not raw_chunks:
        return QueryResponse(
            query=query,
            answer="No relevant documents found. Please upload documents before querying.",
            sources=[],
            model=settings.claude_model,
            tokens_used=0,
        )

    context = build_context(raw_chunks)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    client = get_client()
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    answer = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens

    sources = [SourceChunk(**c) for c in raw_chunks]
    return QueryResponse(
        query=query,
        answer=answer,
        sources=sources,
        model=settings.claude_model,
        tokens_used=tokens,
    )
