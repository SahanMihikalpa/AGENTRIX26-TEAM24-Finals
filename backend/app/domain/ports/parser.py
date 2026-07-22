"""``SourceParser`` port — raw bytes/HTML → clean text + metadata (B1).

Implemented by ``adapters/parser/pymupdf.py`` (PDF via PyMuPDF, HTML via
trafilatura). Produces a :class:`ParsedDocument` that B2 turns into curated,
provenanced records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.entities import SourceType


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Cleaned text extracted from a source, with what provenance we could find."""

    text: str
    source_type: SourceType
    title: str | None = None
    url: str | None = None
    published_date: date | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class SourceParser(Protocol):
    """A swappable document parser."""

    def parse_pdf(self, data: bytes, *, url: str | None = None) -> ParsedDocument:
        """Extract clean text + metadata from PDF bytes."""
        ...

    def parse_html(self, html: str, *, url: str | None = None) -> ParsedDocument:
        """Extract the main article text + metadata from an HTML page."""
        ...
