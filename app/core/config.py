from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    # --- Application ---
    app_name: str = "AI Combination Server"
    app_version: str = "0.1.0"
    debug: bool = False

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- External LLM Provider ---
    llm_provider: str = "openai"  # openai | anthropic | gemini
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # --- Local Models ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"

    # --- Retrieval ---
    retrieval_top_k: int = 10
    rerank_top_k: int = 5
    relevance_threshold: float = -10.0

    # --- Token / Cost ---
    max_context_tokens: int = 2000
    max_output_tokens: int = 1024

    # --- Rate Limiting ---
    rate_limit_max_requests: int = 20
    rate_limit_window_seconds: int = 60

    # --- Paths ---
    data_dir: Path = Path(__file__).resolve().parent.parent.parent / "data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
