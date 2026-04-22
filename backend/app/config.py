from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama — runs on host, containers reach it via host.docker.internal
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", alias="OLLAMA_BASE_URL")
    llm_model: str = Field(default="gemma3:27b", alias="LLM_MODEL")
    embedding_model: str = Field(default="nomic-embed-text", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=768, alias="EMBEDDING_DIM")  # nomic-embed-text produces 768-dim

    # Qdrant
    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    collection_name: str = Field(default="documind", alias="COLLECTION_NAME")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="documind123", alias="NEO4J_PASSWORD")

    # Chunking
    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=64, alias="CHUNK_OVERLAP")

    # Search
    top_k: int = Field(default=10, alias="TOP_K")
    rerank_top_k: int = Field(default=5, alias="RERANK_TOP_K")
    hybrid_alpha: float = Field(default=0.7, alias="HYBRID_ALPHA")

    # Storage
    db_path: str = Field(default="/data/documind.db", alias="DB_PATH")
    upload_dir: str = Field(default="/data/uploads", alias="UPLOAD_DIR")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        alias="CORS_ORIGINS",
    )

    # App
    app_name: str = "DocuMind"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")

    @field_validator("hybrid_alpha")
    @classmethod
    def validate_alpha(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("hybrid_alpha must be between 0.0 and 1.0")
        return v

    model_config = {"env_file": ".env", "populate_by_name": True, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
