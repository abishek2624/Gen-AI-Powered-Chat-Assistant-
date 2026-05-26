from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    app_name: str = "Production RAG Chat Assistant"
    environment: str = "development"
    docs_path: Path = Path("docs.json")
    chroma_path: Path = Path("app/vectorstore/chroma_db")
    collection_name: str = "knowledge_base"
    retrieval_top_k: int = 3
    similarity_threshold: float = 0.35
    conversation_pairs: int = 5
    request_timeout_seconds: float = 30.0
    llm_max_tokens: int = 450
    enable_auth: bool = False
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
