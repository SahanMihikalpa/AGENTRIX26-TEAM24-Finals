"""The web PDF fetcher — download a linked PDF and hand back its full text.

A real (tiny) PDF is built with PyMuPDF and served through a fake opener, so the
whole download → magic-byte check → parse path runs without a network.
"""

from __future__ import annotations

from typing import Any
from urllib.error import URLError

import pytest

from app.adapters.fetch.http_pdf import HttpPdfFetcher
from app.adapters.parser.pymupdf import PyMuPdfSourceParser


def _pdf_bytes(text: str) -> bytes:
    import pymupdf

    doc: Any = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data: bytes = doc.tobytes()
    doc.close()
    return data


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self, n: int = -1) -> bytes:
        return self._data[:n] if n and n >= 0 else self._data

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> bool:
        return False


def _opener_returning(data: bytes):
    calls: list[str] = []

    def _open(request: Any, timeout: float) -> _FakeResponse:
        calls.append(request.full_url if hasattr(request, "full_url") else str(request))
        return _FakeResponse(data)

    _open.calls = calls  # type: ignore[attr-defined]
    return _open


@pytest.fixture
def parser() -> PyMuPdfSourceParser:
    return PyMuPdfSourceParser()


def test_a_linked_pdf_is_downloaded_and_its_text_extracted(parser: PyMuPdfSourceParser) -> None:
    body = _pdf_bytes("Bring your NIC and a medical certificate to the DMT office.")
    fetcher = HttpPdfFetcher(parser, opener=_opener_returning(body))

    parsed = fetcher.fetch("https://dmt.gov.lk/downloads/requirements.pdf")

    assert parsed is not None
    assert "medical certificate" in parsed.text
    assert parsed.url == "https://dmt.gov.lk/downloads/requirements.pdf"


def test_a_non_pdf_url_is_declined_without_a_request(parser: PyMuPdfSourceParser) -> None:
    opener = _opener_returning(b"whatever")
    fetcher = HttpPdfFetcher(parser, opener=opener)

    assert fetcher.fetch("https://dmt.gov.lk/page.html") is None
    assert opener.calls == [], "a non-PDF URL must not be dereferenced"  # type: ignore[attr-defined]


def test_a_non_http_scheme_is_declined(parser: PyMuPdfSourceParser) -> None:
    opener = _opener_returning(_pdf_bytes("x"))
    fetcher = HttpPdfFetcher(parser, opener=opener)

    assert fetcher.fetch("ftp://dmt.gov.lk/a.pdf") is None
    assert opener.calls == []  # type: ignore[attr-defined]


def test_html_served_at_a_pdf_url_is_rejected(parser: PyMuPdfSourceParser) -> None:
    """A .pdf link that returns a login wall / 404 page must not be parsed as a PDF."""
    fetcher = HttpPdfFetcher(parser, opener=_opener_returning(b"<!doctype html><html>...</html>"))

    assert fetcher.fetch("https://dmt.gov.lk/a.pdf") is None


def test_an_oversized_body_is_refused(parser: PyMuPdfSourceParser) -> None:
    big = b"%PDF" + b"0" * 5000
    fetcher = HttpPdfFetcher(parser, max_bytes=1000, opener=_opener_returning(big))

    assert fetcher.fetch("https://dmt.gov.lk/huge.pdf") is None


def test_a_network_error_degrades_to_none(parser: PyMuPdfSourceParser) -> None:
    def _boom(request: Any, timeout: float) -> Any:
        raise URLError("boom")

    fetcher = HttpPdfFetcher(parser, opener=_boom)

    assert fetcher.fetch("https://dmt.gov.lk/a.pdf") is None


def test_extracted_text_is_capped(parser: PyMuPdfSourceParser) -> None:
    body = _pdf_bytes("word " * 400)
    fetcher = HttpPdfFetcher(parser, max_chars=50, opener=_opener_returning(body))

    parsed = fetcher.fetch("https://dmt.gov.lk/long.pdf")

    assert parsed is not None
    assert len(parsed.text) <= 50


def test_a_corrupt_pdf_degrades_to_none(parser: PyMuPdfSourceParser) -> None:
    # Has the %PDF magic but is not a valid document.
    fetcher = HttpPdfFetcher(parser, opener=_opener_returning(b"%PDF-1.4 broken \x00\x01"))

    assert fetcher.fetch("https://dmt.gov.lk/bad.pdf") is None
