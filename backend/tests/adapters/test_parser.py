"""Parser tests — exercise PyMuPDF (PDF) + trafilatura (HTML) when installed.

Skipped automatically if either library is absent, mirroring the bge test.
"""

from __future__ import annotations

import pytest

from app.domain.entities import SourceType

pytest.importorskip("pymupdf")
pytest.importorskip("trafilatura")

from app.adapters.parser.pymupdf import PyMuPdfSourceParser


def _make_pdf(text: str) -> bytes:
    import pymupdf

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data: bytes = document.tobytes()
    document.close()
    return data


def test_parse_pdf_extracts_text_and_provenance() -> None:
    parser = PyMuPdfSourceParser()
    parsed = parser.parse_pdf(_make_pdf("Gazette Extraordinary 2026"), url="https://x.gov.lk/g.pdf")

    assert "Gazette Extraordinary 2026" in parsed.text
    assert parsed.source_type is SourceType.CIRCULAR  # provisional medium-based hint
    assert parsed.url == "https://x.gov.lk/g.pdf"


def test_parse_html_extracts_main_content_and_strips_boilerplate() -> None:
    parser = PyMuPdfSourceParser()
    html = (
        "<html><head><title>NIC Renewal</title></head><body>"
        "<nav>site menu home about contact</nav>"
        "<article><h1>NIC Renewal</h1>"
        "<p>To renew your National Identity Card, bring your birth certificate and a "
        "completed application form to the divisional secretariat office in your "
        "district. The officer will verify your documents and issue a receipt.</p>"
        "</article><footer>copyright boilerplate notice</footer></body></html>"
    )

    parsed = parser.parse_html(html, url="https://rgd.gov.lk/nic")

    assert "birth certificate" in parsed.text
    assert "site menu" not in parsed.text
    assert parsed.source_type is SourceType.PORTAL
    assert parsed.url == "https://rgd.gov.lk/nic"
