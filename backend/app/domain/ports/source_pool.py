"""``SourcePool`` port — read access to the local, pre-collected source pool (B1).

The **local source pool** is the pile of pre-collected gazettes / circulars /
portal PDFs that B1 Research searches **before** the live web (AD-7,
local-source-pool-first). The architecture models it as a store distinct from the
Knowledge Base ([docs/02 C4-L3](../../../docs/02-architecture.md)): pool documents
are *not yet ingested* — B1 surfaces them, B2 curates them, and only then does B3
write them into the KB.

Implemented (Stage 3) by an adapter over ``data/source_pool/`` that handles the
file reading + parsing (PyMuPDF / trafilatura), so this port hands B1 already-clean
text + whatever provenance could be recovered. Synchronous, like the other ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.entities import SourceType


@dataclass(frozen=True, slots=True)
class PooledDocument:
    """A pre-collected, not-yet-ingested document from the local source pool."""

    text: str
    title: str
    source_type: SourceType
    url: str | None = None
    published_date: date | None = None


@runtime_checkable
class SourcePool(Protocol):
    """Searchable access to the local document pool (queried before the web)."""

    def search(self, query: str, *, limit: int = 5) -> list[PooledDocument]:
        """Return pooled documents matching ``query`` (local-first per AD-7)."""
        ...
