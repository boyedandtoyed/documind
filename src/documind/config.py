from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = "sk-placeholder"
    chroma_persist_dir: str = "./data/chroma"
    embed_model: str = "all-MiniLM-L6-v2"
    claude_model: str = "claude-sonnet-4-6"
    max_chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5

settings = Settings()
