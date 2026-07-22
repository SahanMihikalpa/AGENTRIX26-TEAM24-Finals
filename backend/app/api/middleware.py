"""ASGI middleware (delivery cross-cutting).

``CorrelationIdMiddleware`` assigns or propagates a per-request correlation id and
echoes it back on the response. It is **pure ASGI** (not Starlette's
``BaseHTTPMiddleware``) on purpose: ``BaseHTTPMiddleware`` buffers the response
body, which would break the ``POST /api/chat`` SSE stream — a pure ASGI wrapper
leaves the streaming send path untouched.
"""

from __future__ import annotations

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infrastructure.logging import correlation_id_var, new_correlation_id

_HEADER = "x-correlation-id"


class CorrelationIdMiddleware:
    """Bind a correlation id to each request (contextvar + response header)."""

    def __init__(self, app: ASGIApp, *, header_name: str = _HEADER) -> None:
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(self.header_name)
        correlation_id = incoming or new_correlation_id()
        token = correlation_id_var.set(correlation_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[self.header_name] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            correlation_id_var.reset(token)
