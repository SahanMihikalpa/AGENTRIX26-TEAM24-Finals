"""Tests for the build-catalog skeleton builder."""

from __future__ import annotations

from pathlib import Path

from app.cli.build_catalog import build_catalog_skeleton
from app.domain.entities import SourceType
from app.domain.ports.parser import ParsedDocument


class _FakeParser:
    """A torch/PyMuPDF-free SourceParser: bytes/html in, text out."""

    def parse_pdf(self, data: bytes, *, url: str | None = None) -> ParsedDocument:
        return ParsedDocument(text=data.decode("utf-8", "replace"), source_type=SourceType.CIRCULAR)

    def parse_html(self, html: str, *, url: str | None = None) -> ParsedDocument:
        return ParsedDocument(text=html, source_type=SourceType.PORTAL)


def _service_dir(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir(parents=True)
    return path


def test_build_skeleton_auto_fills_sources_and_stubs_facts(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    svc = _service_dir(raw, "nic-issuance")
    (svc / "good.txt").write_text(
        "The applicant must bring a birth certificate and a completed form. " * 20,
        encoding="utf-8",
    )
    (svc / "scanned.pdf").write_bytes(b"")  # no extractable text -> skipped

    catalog, report = build_catalog_skeleton(raw, _FakeParser(), max_chunk_chars=200)

    assert [s["slug"] for s in catalog["services"]] == ["nic-issuance"]
    service = catalog["services"][0]
    assert service["category"] == ""  # stub left for curation
    assert service["variants"] == []  # stub
    assert service["chunks"]  # real chunks from good.txt
    assert all(c["source_key"].startswith("nic-issuance__") for c in service["chunks"])
    assert len(catalog["sources"]) == 1  # only good.txt became a source

    status = {outcome.path: outcome.status for outcome in report.files}
    assert status["nic-issuance/good.txt"] == "ok"
    assert status["nic-issuance/scanned.pdf"] == "skipped-empty"


def test_build_skeleton_drops_nonprose_file(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    svc = _service_dir(raw, "svc")
    garble = (chr(0xA8) + chr(0xEF) + chr(0xA9) + " ") * 80
    (svc / "garble.txt").write_text(garble, encoding="utf-8")

    catalog, report = build_catalog_skeleton(raw, _FakeParser())

    assert catalog["sources"] == []  # nothing kept
    assert catalog["services"][0]["chunks"] == []
    assert report.files[0].status == "skipped-nonprose"
