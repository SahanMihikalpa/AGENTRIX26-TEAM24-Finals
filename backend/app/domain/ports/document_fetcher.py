"""``DocumentFetcher`` port — download a URL and extract its text (B1).

When the live-web tier returns a link to a document (a PDF gazette, circular, or
form), the search snippet alone is thin. This port fetches the document itself and
returns its full extracted text, so B2 curates from the real content rather than a
one-line preview.

Implemented by ``adapters/fetch/http_pdf.py`` (urllib download + the shared
``SourceParser``). Returns ``None`` whenever the URL is not a fetchable document —
wrong type, too large, or a network error — so the caller cleanly falls back to
the snippet. Provenance (title, date, medium) rides along on the ``ParsedDocument``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.ports.parser import ParsedDocument


@runtime_checkable
class DocumentFetcher(Protocol):
    """Fetches and extracts a linked document, or declines."""

    def fetch(self, url: str) -> ParsedDocument | None:
        """Download ``url`` and return its extracted text + provenance.

        Returns ``None`` if the URL is not a document this fetcher handles, or if
        the download/parse fails for any reason. Never raises for an ordinary
        fetch failure — a gap-fill must degrade to the snippet, not crash.
        """
        ...
