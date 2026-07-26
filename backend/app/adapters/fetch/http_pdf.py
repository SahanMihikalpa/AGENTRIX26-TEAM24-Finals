"""HTTP PDF fetcher — download a linked PDF and extract its full text (B1).

The live-web tier returns links; for a PDF, the search snippet is a poor substitute
for the document. This adapter downloads the file and runs it through the shared
:class:`SourceParser` (PyMuPDF), so the gap loop ingests the real requirements text
rather than a preview.

Deliberately **PDF-only and defensive**, because it dereferences URLs that a web
search returned (including, on the unrestricted tier, non-government hosts):

* only ``http``/``https`` and only URLs whose path ends in ``.pdf``;
* a byte cap read during download (an oversized body is refused, not buffered);
* a ``%PDF`` magic-byte check, so an HTML error page served at a ``.pdf`` URL is
  rejected rather than parsed as garbage;
* a text cap, so a huge document cannot blow the downstream LLM prompt;
* every failure returns ``None`` — a gap-fill degrades to the snippet, never crashes.

The opener is injectable so the adapter is fully testable without a network.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.domain.ports.parser import ParsedDocument, SourceParser
from app.infrastructure.logging import get_logger

_log = get_logger(__name__)

_DEFAULT_MAX_BYTES = 15 * 1024 * 1024  # 15 MB — larger PDFs are refused
_DEFAULT_MAX_CHARS = 8_000  # cap handed downstream so B2's prompt stays bounded
_DEFAULT_TIMEOUT = 15.0
_USER_AGENT = "GovGuide/0.1 (+https://govguide.example) document-fetcher"

# An opener takes (Request, timeout) and returns an HTTP response context manager.
Opener = Callable[[Request, float], Any]


class HttpPdfFetcher:
    """A :class:`DocumentFetcher` that downloads and parses linked PDFs."""

    def __init__(
        self,
        parser: SourceParser,
        *,
        max_bytes: int = _DEFAULT_MAX_BYTES,
        max_chars: int = _DEFAULT_MAX_CHARS,
        timeout: float = _DEFAULT_TIMEOUT,
        opener: Opener | None = None,
    ) -> None:
        self._parser = parser
        self._max_bytes = max_bytes
        self._max_chars = max_chars
        self._timeout = timeout
        self._opener: Opener = opener or (lambda req, timeout: urlopen(req, timeout=timeout))

    def fetch(self, url: str) -> ParsedDocument | None:
        if not _is_pdf_url(url):
            return None

        data = self._download(url)
        if data is None:
            return None
        if not data.startswith(b"%PDF"):
            # A .pdf link that actually served HTML (login wall, 404 page, …).
            _log.info("Skipping %s: response is not a PDF", url)
            return None

        try:
            parsed = self._parser.parse_pdf(data, url=url)
        except Exception:
            _log.exception("Failed to parse PDF from %s", url)
            return None

        text = parsed.text.strip()
        if not text:
            return None
        if len(text) > self._max_chars:
            text = text[: self._max_chars]
        _log.info("Fetched PDF %s (%d chars extracted)", url, len(text))
        return replace(parsed, text=text)

    def _download(self, url: str) -> bytes | None:
        request = Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with self._opener(request, self._timeout) as response:
                # Read one byte past the cap so an oversized body is detectable
                # without holding the whole thing in memory.
                data = bytes(response.read(self._max_bytes + 1))
        except Exception:
            _log.warning("Could not download %s", url, exc_info=True)
            return None
        if len(data) > self._max_bytes:
            _log.info("Skipping %s: larger than %d bytes", url, self._max_bytes)
            return None
        return data


def _is_pdf_url(url: str) -> bool:
    """True for an ``http(s)`` URL whose path ends in ``.pdf``."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return parsed.path.lower().endswith(".pdf")
