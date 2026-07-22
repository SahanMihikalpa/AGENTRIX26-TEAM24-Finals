"""FastAPI application entry point (the delivery layer).

This module owns the ASGI app: it wires cross-cutting middleware, the startup
lifespan, and routers. It exposes the health probe plus the Stage-6 chat SSE +
Action-Pack routes. The agent runtime (adapters → gateway → LangGraph app) is
built **lazily** on first use by ``get_runtime`` and cached on ``app.state`` — so
tests override that dependency and never construct real stores or hit the network.

Run (from backend/):
    uvicorn app.api.main:app --reload --port 8000
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import CorrelationIdMiddleware
from app.api.routes.chat import router as chat_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.moderation import router as moderation_router
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.logging import configure_logging, configure_tracing, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks.

    Configuration is read once and stashed on ``app.state``; the heavy runtime
    (graph + bge model) is built lazily on the first ``/api/chat`` request rather
    than at boot, so the process starts instantly and tests never trigger a build.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    if configure_tracing(
        enabled=settings.langchain_tracing_v2, api_key=settings.langsmith_api_key
    ):
        logger.info("LangSmith tracing enabled")
    app.state.settings = settings
    logger.info("Starting GovGuide backend (env=%s)", settings.app_env)
    yield
    logger.info("Shutting down GovGuide backend")


def create_app() -> FastAPI:
    """Application factory.

    A factory (rather than a module-level singleton only) keeps the app testable:
    tests build a fresh instance without import-time side effects.
    """
    settings: Settings = get_settings()
    app = FastAPI(title="GovGuide API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings  # available before lifespan (e.g. under TestClient DI)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Added last → outermost: every request (and CORS preflight) gets a correlation id.
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness probe used by the frontend and orchestration."""
        return {"status": "ok", "service": "govguide-backend", "version": "0.1.0"}

    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(moderation_router)

    return app


app = create_app()
