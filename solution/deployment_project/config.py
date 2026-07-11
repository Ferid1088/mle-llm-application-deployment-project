"""Reference application configuration."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Environment-backed deployment settings."""

    provider: str = os.getenv("MODEL_PROVIDER", "dry")
    api_key: str = os.getenv("GROQ_API_KEY", "")
    model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    max_concurrency: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "4"))
    trace_sink: str = os.getenv("TRACE_SINK", "jsonl")
    trace_path: Path = Path(os.getenv("TRACE_PATH", "solution/generated/traces.jsonl"))
    environment: str = os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development")
    release: str = os.getenv("LANGFUSE_RELEASE", "local")


settings = Settings()
