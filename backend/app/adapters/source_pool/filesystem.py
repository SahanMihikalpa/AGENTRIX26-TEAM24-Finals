"""Filesystem implementation of the ``SourcePool`` port (B1, AD-7).

The local source pool is a directory (``data/source_pool/``) of pre-collected,
not-yet-ingested government documents that B1 searches **before** the live web.
This adapter reads those files, extracts clean text via the shared
:class:`SourceParser` (PyMuPDF for PDFs, trafilatura for HTML; plain read for
text), and returns the best keyword/filename matches as :class:`PooledDocument`s.

Delta vs. docs (logged in docs/10): matching is **lexical** (query terms vs.
filename + content) for the MVP — fast, dependency-light, and enough for the
pre-staged demo sources; the doc's "ChromaDB over the pool" vector index remains a
noted enhancement. Parsing is delegated to the ``SourceParser`` adapter, so this
adapter stays a thin file→``PooledDocument`` mapper.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.entities import SourceType
from app.domain.ports.parser import SourceParser
from app.domain.ports.source_pool import PooledDocument

_TEXT_SUFFIXES = {".txt", ".md"}
_HTML_SUFFIXES = {".html", ".htm"}
_NAME_WEIGHT = 2  # a filename hit is worth more than a body hit


class FilesystemSourcePool:
    """A ``SourcePool`` over a local directory of pooled documents."""

    def __init__(self, root: Path, *, parser: SourceParser | None = None) -> None:
        self._root = Path(root)
        self._parser = parser

    def search(self, query: str, *, limit: int = 5) -> list[PooledDocument]:
        if not self._root.is_dir():
            return []
        query_terms = _terms(query)
        if not query_terms:
            return []

        scored: list[tuple[int, str, PooledDocument]] = []
        for path in sorted(self._root.iterdir()):
            if not path.is_file():
                continue
            doc = self._load(path)
            if doc is None:
                continue
            score = self._score(query_terms, path, doc.text)
            if score > 0:
                scored.append((score, path.name, doc))

        scored.sort(key=lambda item: (-item[0], item[1]))  # score desc, then stable by name
        return [doc for _, _, doc in scored[:limit]]

    # ── loading ──────────────────────────────────────────────────
    def _load(self, path: Path) -> PooledDocument | None:
        suffix = path.suffix.lower()
        if suffix in _TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore")
            return PooledDocument(text=text, title=path.stem, source_type=SourceType.PORTAL)
        if suffix == ".pdf" and self._parser is not None:
            parsed = self._parser.parse_pdf(path.read_bytes())
            return PooledDocument(
                text=parsed.text,
                title=parsed.title or path.stem,
                source_type=SourceType.CIRCULAR,
                published_date=parsed.published_date,
            )
        if suffix in _HTML_SUFFIXES and self._parser is not None:
            parsed = self._parser.parse_html(path.read_text(encoding="utf-8", errors="ignore"))
            return PooledDocument(
                text=parsed.text,
                title=parsed.title or path.stem,
                source_type=SourceType.PORTAL,
                published_date=parsed.published_date,
            )
        return None

    @staticmethod
    def _score(query_terms: set[str], path: Path, text: str) -> int:
        name_terms = _terms(path.stem.replace("_", " ").replace("-", " "))
        body_terms = _terms(text)
        return len(query_terms & body_terms) + _NAME_WEIGHT * len(query_terms & name_terms)


def _terms(value: str) -> set[str]:
    return {token for token in value.lower().split() if token}
