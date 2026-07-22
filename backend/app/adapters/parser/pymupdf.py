"""Source parser — raw bytes/HTML → clean text + provenance (``SourceParser``).

* **PDF** → PyMuPDF (``pymupdf``): concatenated page text + document metadata
  (gazette / circular / portal PDFs from the source pool or the live web).
* **HTML** → trafilatura: main-article extraction that strips nav/boilerplate,
  plus page metadata (title, date).

Both libraries are imported lazily so importing this module never pulls them.
The emitted ``source_type`` is a **provisional, medium-based hint** (PDF→circular,
HTML→portal); B2 sets the authoritative category during curation, so the parser
never guesses a government document class from bytes.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.entities import SourceType
from app.domain.ports.parser import ParsedDocument


class PyMuPdfSourceParser:
    """Concrete :class:`SourceParser` over PyMuPDF (PDF) + trafilatura (HTML)."""

    def parse_pdf(self, data: bytes, *, url: str | None = None) -> ParsedDocument:
        try:
            import pymupdf
        except ImportError as exc:  # pragma: no cover - requires the pymupdf extra
            raise RuntimeError(
                "pymupdf is not installed; install the backend dependencies "
                "(`pip install -e .[dev]`)."
            ) from exc
        text_parts: list[str] = []
        # PyMuPDF ships py.typed but its Document API is only partially typed, so the
        # handle is treated as untyped (it is iterable over pages at runtime).
        document: Any = pymupdf.open(stream=data, filetype="pdf")  # type: ignore[no-untyped-call]
        with document:
            for page in document:
                text_parts.append(page.get_text())
            raw_meta = dict(document.metadata or {})
        metadata: dict[str, str] = {}
        author = _clean(raw_meta.get("author"))
        if author:
            metadata["author"] = author
        return ParsedDocument(
            text="\n".join(text_parts).strip(),
            source_type=SourceType.CIRCULAR,
            title=_clean(raw_meta.get("title")),
            url=url,
            published_date=_parse_pdf_date(raw_meta.get("creationDate")),
            metadata=metadata,
        )

    def parse_html(self, html: str, *, url: str | None = None) -> ParsedDocument:
        try:
            import trafilatura
        except ImportError as exc:  # pragma: no cover - requires the trafilatura extra
            raise RuntimeError(
                "trafilatura is not installed; install the backend dependencies "
                "(`pip install -e .[dev]`)."
            ) from exc
        text = trafilatura.extract(html, url=url, favor_recall=True, include_comments=False) or ""
        title: str | None = None
        published: date | None = None
        meta_url: str | None = None
        metadata: dict[str, str] = {}
        try:
            meta = trafilatura.extract_metadata(html)
        except Exception:  # pragma: no cover - metadata is best-effort
            meta = None
        if meta is not None:
            title = _clean(getattr(meta, "title", None))
            published = _parse_iso_date(getattr(meta, "date", None))
            meta_url = _clean(getattr(meta, "url", None))
            author = _clean(getattr(meta, "author", None))
            if author:
                metadata["author"] = author
        return ParsedDocument(
            text=text.strip(),
            source_type=SourceType.PORTAL,
            title=title,
            url=url or meta_url,
            published_date=published,
            metadata=metadata,
        )


def _clean(value: str | None) -> str | None:
    """Trim a metadata string to a non-empty value, or ``None``."""
    if not value:
        return None
    return value.strip() or None


def _parse_pdf_date(value: str | None) -> date | None:
    """Parse a PDF date string (``D:YYYYMMDD...``) to a :class:`date`."""
    if not value:
        return None
    digits = value[2:] if value.startswith("D:") else value
    if len(digits) < 8 or not digits[:8].isdigit():
        return None
    try:
        return date(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:  # pragma: no cover - defensive against malformed PDF dates
        return None


def _parse_iso_date(value: str | None) -> date | None:
    """Parse an ISO-ish date string; fall back to the bare year if needed."""
    if not value:
        return None
    candidate = value.strip()[:10]
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        head = candidate[:4]
        return date(int(head), 1, 1) if head.isdigit() else None
