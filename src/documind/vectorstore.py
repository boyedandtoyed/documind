import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from .config import settings
from .chunker import Chunk
import uuid

_client: chromadb.ClientAPI | None = None
_embedder: SentenceTransformer | None = None

def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client

def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.embed_model)
    return _embedder

def get_collection(name: str = "documents") -> chromadb.Collection:
    client = get_client()
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})

def index_chunks(
    document_id: str,
    filename: str,
    chunks: list[Chunk],
) -> int:
    collection = get_collection()
    embedder = get_embedder()
    texts = [c.text for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()
    ids = [f"{document_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"document_id": document_id, "filename": filename, "page": c.page or 0, "index": c.index}
        for c in chunks
    ]
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(chunks)

def query_chunks(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict]:
    collection = get_collection()
    embedder = get_embedder()
    q_emb = embedder.encode([query], show_progress_bar=False).tolist()
    where = {"document_id": document_id} if document_id else None
    results = collection.query(
        query_embeddings=q_emb,
        n_results=min(top_k, collection.count() or 1),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "chunk_id": f"{meta['document_id']}_{meta['index']}",
            "document_id": meta["document_id"],
            "filename": meta["filename"],
            "text": doc,
            "score": float(1 - dist),
            "page": meta.get("page"),
        })
    return chunks

def document_count() -> int:
    try:
        return len({m["document_id"] for m in get_collection().get(include=["metadatas"])["metadatas"]})
    except Exception:
        return 0
