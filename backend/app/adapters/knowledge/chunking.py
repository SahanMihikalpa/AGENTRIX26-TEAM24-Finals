"""Text chunking + a prose-quality filter for the knowledge base.

``chunk_text`` splits cleaned document text into overlapping, word-boundary
windows sized for the bge embedder. ``looks_like_prose`` is a cheap heuristic that
keeps English prose and rejects scanned-empty / form-field / legacy-font-garbled
text — which embeds as pure noise under an English-only model
(``bge-base-en-v1.5``, AD-4). Both are pure (stdlib only) and are used by the seed
``build`` CLI (and available to B3 if it later adopts shared chunking).
"""

from __future__ import annotations

import re
import string

# A "word" = at least two consecutive ASCII letters. Legacy-font Sinhala/Tamil
# extracted from form PDFs renders as punctuation-laced gibberish with almost no
# such runs, so the ratio of word-like tokens is the key garble discriminator.
_ALPHA_WORD = re.compile(r"[A-Za-z]{2,}")
# Printable ASCII + whitespace. English prose is ~all ASCII; scanned garble and
# legacy-font text carry many non-ASCII bytes, so the ASCII ratio is a cheap,
# unambiguous quality signal (it also correctly rejects non-English for bge-en).
_ASCII_PROSE = frozenset(string.ascii_letters + string.digits + string.punctuation + " \t\r\n")


def chunk_text(text: str, *, max_chars: int = 1000, overlap: int = 120) -> list[str]:
    """Split ``text`` into word-boundary chunks of ≤ ``max_chars`` with a char-budgeted
    ``overlap`` carried from the tail of each chunk into the next (continuity for
    retrieval). Deterministic and whitespace-normalising; returns ``[]`` for blank
    input.
    """
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        addition = len(word) + (1 if current else 0)
        if current and length + addition > max_chars:
            chunks.append(" ".join(current))
            current, length = _overlap_tail(current, overlap)
        current.append(word)
        length += len(word) + (1 if length else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks


def looks_like_prose(
    text: str,
    *,
    min_chars: int = 40,
    min_ascii_ratio: float = 0.80,
    min_word_ratio: float = 0.5,
) -> bool:
    """Return ``True`` if ``text`` reads like real (English) prose.

    Rejects too-short fragments, non-ASCII-dense junk (low ``min_ascii_ratio``), and
    garbled/form text whose tokens are mostly not word-like (low ``min_word_ratio``).
    """
    stripped = text.strip()
    if len(stripped) < min_chars:
        return False
    good = sum(1 for char in stripped if char in _ASCII_PROSE)
    if good / len(stripped) < min_ascii_ratio:
        return False
    tokens = stripped.split()
    if not tokens:
        return False
    wordlike = sum(1 for token in tokens if _ALPHA_WORD.search(token))
    return wordlike / len(tokens) >= min_word_ratio


def _overlap_tail(words: list[str], overlap_chars: int) -> tuple[list[str], int]:
    """Return the trailing words of ``words`` whose total length is ~``overlap_chars``."""
    if overlap_chars <= 0:
        return [], 0
    tail: list[str] = []
    length = 0
    for word in reversed(words):
        if tail and length + len(word) + 1 > overlap_chars:
            break
        tail.insert(0, word)
        length += len(word) + 1
    return tail, length
