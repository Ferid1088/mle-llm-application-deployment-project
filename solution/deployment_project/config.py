"""Reference application configuration."""

import math
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
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    trace_sink: str = os.getenv("TRACE_SINK", "jsonl")
    trace_path: Path = Path(os.getenv("TRACE_PATH", "solution/generated/traces.jsonl"))
    environment: str = os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development")
    release: str = os.getenv("LANGFUSE_RELEASE", "local")

    def __post_init__(self) -> None:
        if self.max_concurrency < 1 or self.cache_ttl_seconds < 0:
            raise ValueError("Concurrency must be positive and cache TTL nonnegative")
        if (
            not math.isfinite(self.request_timeout_seconds)
            or self.request_timeout_seconds <= 0
        ):
            raise ValueError("Request timeout must be finite and positive")


settings = Settings()
