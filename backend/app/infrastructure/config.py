"""Application configuration.

A single, validated `Settings` object loaded from environment variables (and a
local `.env`). This is the only place that reads the environment, so the rest of
the codebase depends on typed settings rather than scattered `os.getenv` calls.

Lives in `infrastructure` because configuration is a cross-cutting concern; the
`domain` and `application` layers never import it directly — concrete values are
injected at the edges (`api`) instead.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, environment-driven configuration for the backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Server ─────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"  # comma-separated

    # ── Local data stores (relative to backend/) ───────────────────
    data_dir: Path = Path("data")
    sqlite_path: Path = Path("data/govguide.sqlite3")
    chroma_dir: Path = Path("data/chroma")
    source_pool_dir: Path = Path("data/source_pool")

    # ── LLM (free tier) ────────────────────────────────────────────
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash"
    llm_fallback_model: str = "llama-3.1-8b-instant"

    # ── Web research ───────────────────────────────────────────────
    tavily_api_key: str | None = None
    web_allowlist: str = "gov.lk"  # comma-separated

    # ── Embeddings (local) ─────────────────────────────────────────
    embedding_model: str = "BAAI/bge-base-en-v1.5"

    # ── RAG guardrails ─────────────────────────────────────────────
    confidence_threshold: float = 0.6
    max_acquisition_loops: int = 2

    # ── LLM gateway (outbound provider pacing) ─────────────────────
    llm_rate_limit_rpm: int = 15

    # ── HTTP rate limiting (inbound, per client) ───────────────────
    # The LLM gateway paces outbound calls but never refuses them, so an
    # unbounded flood of /api/chat requests would still drain the day's free-tier
    # quota. These caps reject the excess at the edge instead (see api/rate_limit).
    chat_rate_limit_rpm: int = 10  # POST /api/chat — the quota spender
    api_rate_limit_rpm: int = 60  # every other /api route

    # ── Observability ──────────────────────────────────────────────
    langsmith_api_key: str | None = None
    langchain_tracing_v2: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a clean list (parsed from the comma-separated value)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def web_allowlist_domains(self) -> list[str]:
        """Allowed web-search domains as a clean list."""
        return [d.strip().lower() for d in self.web_allowlist.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance (read the environment once)."""
    return Settings()
