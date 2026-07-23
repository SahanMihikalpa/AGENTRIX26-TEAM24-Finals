"""``merge-services`` — duplicate detection and the guarded merge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder
from app.cli import merge_services
from tests.adapters.conftest import DeterministicEmbedder

_SEED: dict[str, Any] = {
    "sources": [
        {
            "key": "good",
            "title": "Circular",
            "url": "https://x.gov.lk",
            "source_type": "circular",
            "retrieved_date": "2026-06-20",
            "confidence": 0.95,
            "verification_status": "verified",
        },
        {
            "key": "weak",
            "title": "Scraped page",
            "url": "https://y.gov.lk",
            "source_type": "portal",
            "retrieved_date": "2026-07-01",
            "confidence": 0.45,
            "verification_status": "auto_gathered",
        },
    ],
    "services": [
        {
            "name_en": "National Identity Card (NIC) Issuance",
            "slug": "nic-issuance",
            "category": "identity",
            "description": "Apply for or amend a National Identity Card",
            "variants": [
                {
                    "condition_label": "amendment",
                    "description": "",
                    "requirements": [{"source_key": "good", "document_name": "Birth certificate"}],
                    "fees": [{"source_key": "good", "label": "Fee", "amount_lkr": "200"}],
                }
            ],
        },
        {
            # Echoes the parent's 'amendment' variant; its facts come from a
            # low-confidence crawl, so A6 would gate them and answer nothing.
            "name_en": "Amendment of NIC",
            "slug": "amendment_of_nic",
            "category": "",
            "description": "",
            "variants": [
                {
                    "condition_label": "standard",
                    "description": "",
                    "requirements": [{"source_key": "weak", "document_name": "Scraped doc"}],
                }
            ],
        },
        {
            # Unrelated: shares no meaningful words and echoes no variant.
            "name_en": "Business Name Registration",
            "slug": "business-name",
            "category": "business",
            "description": "Register a business name",
            "variants": [{"condition_label": "standard", "description": ""}],
        },
    ],
}


@pytest.fixture
def kb(tmp_path: Path) -> tuple[Path, Path, ChromaSqliteStore]:
    sqlite_path, chroma_dir = tmp_path / "kb.sqlite3", tmp_path / "chroma"
    store = ChromaSqliteStore(sqlite_path=sqlite_path, chroma_dir=chroma_dir)
    KnowledgeSeeder(store, DeterministicEmbedder()).load(_SEED)
    return sqlite_path, chroma_dir, store


def _run(sqlite_path: Path, chroma_dir: Path, *args: str) -> int:
    return merge_services.main(
        ["--sqlite", str(sqlite_path), "--chroma", str(chroma_dir), *args]
    )


def _ids(store: ChromaSqliteStore) -> dict[str, int]:
    return {
        s.slug: s.id
        for s in store.find_services("", limit=100)
        if s.id is not None
    }


def test_suggest_names_the_duplicate_and_the_variant_it_echoes(
    kb: tuple[Path, Path, ChromaSqliteStore], capsys: pytest.CaptureFixture[str]
) -> None:
    sqlite_path, chroma_dir, _ = kb

    assert _run(sqlite_path, chroma_dir, "--suggest") == 0

    out = capsys.readouterr().out
    assert "Amendment of NIC" in out
    assert "variant 'amendment'" in out
    assert "Business Name Registration" not in out, "unrelated services must not be proposed"
    assert "Nothing was changed" in out


def test_suggest_changes_nothing(
    kb: tuple[Path, Path, ChromaSqliteStore], capsys: pytest.CaptureFixture[str]
) -> None:
    sqlite_path, chroma_dir, store = kb
    before = set(_ids(store))

    _run(sqlite_path, chroma_dir, "--suggest")

    after = ChromaSqliteStore(sqlite_path=sqlite_path, chroma_dir=chroma_dir)
    assert set(_ids(after)) == before


def test_dry_run_reports_but_writes_nothing(
    kb: tuple[Path, Path, ChromaSqliteStore], capsys: pytest.CaptureFixture[str]
) -> None:
    sqlite_path, chroma_dir, store = kb
    ids = _ids(store)

    code = _run(
        sqlite_path, chroma_dir,
        "--into", str(ids["nic-issuance"]),
        "--duplicates", str(ids["amendment_of_nic"]),
        "--dry-run",
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "WOULD MERGE (dry run)" in out
    assert "discards:" in out
    assert "nothing was written" in out
    after = ChromaSqliteStore(sqlite_path=sqlite_path, chroma_dir=chroma_dir)
    assert "amendment_of_nic" in _ids(after)


def test_merge_applies_and_reports(
    kb: tuple[Path, Path, ChromaSqliteStore], capsys: pytest.CaptureFixture[str]
) -> None:
    sqlite_path, chroma_dir, store = kb
    ids = _ids(store)

    code = _run(
        sqlite_path, chroma_dir,
        "--into", str(ids["nic-issuance"]),
        "--duplicates", str(ids["amendment_of_nic"]),
    )

    assert code == 0
    assert "MERGED" in capsys.readouterr().out
    after = ChromaSqliteStore(sqlite_path=sqlite_path, chroma_dir=chroma_dir)
    assert "amendment_of_nic" not in _ids(after)
    assert "nic-issuance" in _ids(after)


def test_missing_arguments_are_rejected(
    kb: tuple[Path, Path, ChromaSqliteStore], capsys: pytest.CaptureFixture[str]
) -> None:
    sqlite_path, chroma_dir, _ = kb

    code = _run(sqlite_path, chroma_dir)

    assert code == 2
    assert "--suggest" in capsys.readouterr().err


def test_unknown_parent_is_rejected(
    kb: tuple[Path, Path, ChromaSqliteStore], capsys: pytest.CaptureFixture[str]
) -> None:
    sqlite_path, chroma_dir, store = kb
    ids = _ids(store)

    code = _run(
        sqlite_path, chroma_dir,
        "--into", "9999", "--duplicates", str(ids["amendment_of_nic"]),
    )

    assert code == 1
    assert "no service with id 9999" in capsys.readouterr().err


def test_an_unknown_duplicate_is_skipped_not_fatal(
    kb: tuple[Path, Path, ChromaSqliteStore], capsys: pytest.CaptureFixture[str]
) -> None:
    sqlite_path, chroma_dir, store = kb
    ids = _ids(store)

    code = _run(
        sqlite_path, chroma_dir,
        "--into", str(ids["nic-issuance"]),
        "--duplicates", f"9999,{ids['amendment_of_nic']}",
    )

    captured = capsys.readouterr()
    assert code == 1, "a skipped id is reported as a partial failure"
    assert "skipped id=9999" in captured.err
    assert "MERGED" in captured.out, "the valid id is still merged"
