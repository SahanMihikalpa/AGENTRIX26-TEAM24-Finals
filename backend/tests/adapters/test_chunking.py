"""Tests for text chunking + the prose-quality filter."""

from __future__ import annotations

from app.adapters.knowledge.chunking import chunk_text, looks_like_prose

# Legacy-font garble, built from code points so the test source stays ASCII.
_GARBLE = (chr(0xA8) + chr(0xEF) + chr(0xA9) + chr(0xBE) + chr(0xA7) + " ") * 60


def test_chunk_text_splits_within_budget() -> None:
    chunks = chunk_text("word " * 400, max_chars=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_chunk_text_overlaps_consecutive_chunks() -> None:
    text = " ".join(f"token{i}" for i in range(200))
    chunks = chunk_text(text, max_chars=120, overlap=40)
    assert len(chunks) >= 2
    first_tail = chunks[0].split()[-1]
    assert first_tail in chunks[1].split()  # the tail is carried into the next chunk


def test_chunk_text_blank_returns_empty() -> None:
    assert chunk_text("   \n  ") == []


def test_looks_like_prose_accepts_english() -> None:
    assert looks_like_prose(
        "The applicant must submit a completed application form and a birth certificate."
    )


def test_looks_like_prose_rejects_non_ascii_garble() -> None:
    assert not looks_like_prose(_GARBLE)


def test_looks_like_prose_rejects_punctuation_noise() -> None:
    assert not looks_like_prose(";:,. 1 2 / ;: ,. 3 ;: " * 20)


def test_looks_like_prose_rejects_too_short() -> None:
    assert not looks_like_prose("Rs. 200")
