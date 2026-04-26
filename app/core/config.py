from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    # --- Application ---
    app_name: str = "Personal AI Representative"
    app_version: str = "0.2.0"
    debug: bool = False

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Persona ---
    persona_name: str = "Patrick Tran"
    persona_aliases: str = "Phuc, Nguyen, Bin"

    # --- External LLM Provider ---
    llm_provider: str = "openai"  # openai | anthropic | gemini
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # --- Local Models ---
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

    # --- Retrieval ---
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    relevance_threshold: float = 0.35
    relevance_gate_enabled: bool = True

    # --- Token / Cost ---
    max_context_tokens: int = 1800
    max_output_tokens: int = 450
    max_user_query_chars: int = 1200
    max_history_messages: int = 6
    max_history_chars: int = 900
    max_evidence_chunks: int = 4
    max_evidence_chars: int = 1600
    max_evidence_chunk_chars: int = 420
    generation_temperature: float = 0.2

    # --- Speech / Voice Output ---
    speech_provider: str = "openai"  # openai | elevenlabs | local
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "alloy"
    openai_tts_voice_id: str = ""
    openai_tts_instructions: str = (
        "Speak English slowly and clearly with a natural Vietnamese accent, "
        "like a Vietnamese speaker speaking English. Keep it warm, calm, and easy to understand."
    )
    openai_tts_response_format: str = "mp3"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "mp3_44100_128"
    elevenlabs_stability: float = 0.4
    elevenlabs_similarity_boost: float = 0.85
    elevenlabs_style: float = 0.0
    elevenlabs_use_speaker_boost: bool = True
    local_tts_url: str = "http://127.0.0.1:7861/v1/voice/synthesize"
    local_tts_api_key: str = ""
    local_tts_reference_audio_path: str = ""
    local_tts_reference_text: str = ""
    local_tts_model: str = ""
    local_tts_timeout_seconds: float = 300.0
    speech_default_speed: float | None = 0.7
    speech_default_instructions: str = (
        "Speak English slowly and clearly with a natural Vietnamese accent, "
        "like a Vietnamese speaker speaking English. Keep it warm, calm, and easy to understand."
    )
    speech_punctuation_pauses_enabled: bool = True
    speech_chunk_size: int = 4096
    max_speech_input_chars: int = 4096
    transcription_provider: str = "openai"  # openai
    openai_stt_model: str = "gpt-4o-mini-transcribe"
    openai_stt_prompt: str = "Names that may appear: Patrick Tran, Phuc, Nguyen, Bin."
    max_speech_upload_bytes: int = 25 * 1024 * 1024

    # --- Rate Limiting ---
    rate_limit_max_requests: int = 20
    rate_limit_window_seconds: int = 60

    # --- Chat sessions ---
    session_max_turns: int = 4

    # --- Database ---
    database_url: str = "postgresql://user:password@localhost:5432/ai_sources"
    rds_iam_auth: bool = False        # Set True to use AWS IAM token auth (RDS)
    aws_region: str = "us-east-1"     # AWS region for IAM token / Secrets Manager
    aws_secret_name: str = ""         # Secrets Manager secret name; if set, overrides DATABASE_URL + rds_iam_auth

    # --- Paths ---
    data_dir: Path = Path(__file__).resolve().parent.parent.parent / "data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
