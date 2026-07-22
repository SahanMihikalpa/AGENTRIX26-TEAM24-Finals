"""FilesystemSourcePool — keyword/filename matching over the local pool."""

from __future__ import annotations

from pathlib import Path

from app.adapters.source_pool.filesystem import FilesystemSourcePool


def test_ranks_matches_by_keyword_overlap(tmp_path: Path) -> None:
    (tmp_path / "business_name_registration.txt").write_text(
        "register a business name; bring an nic copy", encoding="utf-8"
    )
    (tmp_path / "land_transfer.txt").write_text(
        "transfer a land deed by inheritance", encoding="utf-8"
    )
    pool = FilesystemSourcePool(tmp_path)

    docs = pool.search("business name registration")

    assert docs
    assert docs[0].title == "business_name_registration"
    assert "register a business" in docs[0].text


def test_missing_or_empty_dir_returns_nothing(tmp_path: Path) -> None:
    assert FilesystemSourcePool(tmp_path / "nope").search("anything") == []
    assert FilesystemSourcePool(tmp_path).search("anything") == []  # empty dir


def test_non_matching_query_returns_nothing(tmp_path: Path) -> None:
    (tmp_path / "land_transfer.txt").write_text("transfer a land deed", encoding="utf-8")
    assert FilesystemSourcePool(tmp_path).search("passport visa immigration") == []


def test_pdf_skipped_without_a_parser(tmp_path: Path) -> None:
    (tmp_path / "circular.pdf").write_bytes(b"%PDF-1.4 fake")
    # no parser injected → PDFs can't be read, so they're skipped (not an error)
    assert FilesystemSourcePool(tmp_path).search("circular") == []
