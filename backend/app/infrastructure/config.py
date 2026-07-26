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
    # Official domains B1 searches (comma-separated). `gov.lk` covers every
    # *.gov.lk subdomain — including the gazette/acts portal `documents.gov.lk`;
    # `parliament.lk` is the (non-gov.lk) official Parliament site.
    web_allowlist: str = "gov.lk,parliament.lk"
    # A subset searched *first* so authoritative legal sources (the gazette, acts)
    # surface ahead of general portal pages. Must be within the allow-list.
    web_priority_domains: str = "documents.gov.lk"
    # When the allow-listed search finds nothing, search the wider web anyway.
    # Those results are recorded as unofficial and capped below the serving
    # threshold, so they reach a moderator rather than a citizen (docs/05).
    web_fallback_unrestricted: bool = True
    unofficial_max_confidence: float = 0.5
    # Download + parse a PDF that a web result links to, so B1 ingests the full
    # document instead of its one-line search snippet.
    web_pdf_fetch: bool = True
    # Source authority for B2 (confidence = authority * extraction certainty). An
    # official (allow-listed) web result is authoritative enough to be served once
    # extracted well — labelled "pending verification" — while an unofficial find
    # stays below the serving gate and reaches a moderator instead.
    web_official_authority: float = 0.75
    web_unofficial_authority: float = 0.5

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
    # POST /api/chat — the quota spender. Sized for a real conversation (a turn
    # is one request, and the A3 interview costs several), while the LLM gateway's
    # own 15 rpm bucket remains the hard ceiling on provider spend.
    chat_rate_limit_rpm: int = 30
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

    @property
    def web_priority_domain_list(self) -> list[str]:
        """Priority (gazette/legal) domains searched first, as a clean list."""
        return [d.strip().lower() for d in self.web_priority_domains.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance (read the environment once)."""
    return Settings()
