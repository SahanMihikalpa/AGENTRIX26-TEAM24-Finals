"""The ``checklist`` table — the durable record of what was actually served.

Also covers the one-time migration off the pre-Stage-7 shape (an integer
``session_id`` foreign key into a ``session`` table that no longer exists).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore

_PACK = {
    "service_label": "NIC Issuance (first-time)",
    "district": "Colombo",
    "documents": [{"name": "Birth certificate", "mandatory": True, "notes": "", "source_id": 1}],
    "fees": [],
    "office": None,
    "steps": ["Visit the DS office"],
    "estimated_cost_lkr": "200",
    "verification": "verified",
    "citations": [],
    "fallback": False,
    "fallback_message": None,
}


def test_save_and_read_back(store: ChromaSqliteStore) -> None:
    row_id = store.save_checklist("thread-abc", _PACK, service_id=2, variant_id=7)

    assert row_id > 0
    assert store.get_checklist("thread-abc") == _PACK


def test_unknown_session_returns_none(store: ChromaSqliteStore) -> None:
    assert store.get_checklist("never-seen") is None


def test_the_latest_pack_wins(store: ChromaSqliteStore) -> None:
    store.save_checklist("thread-abc", _PACK)
    store.save_checklist("thread-abc", {**_PACK, "service_label": "Corrected"})

    fetched = store.get_checklist("thread-abc")

    assert fetched is not None
    assert fetched["service_label"] == "Corrected"


def test_sessions_are_isolated(store: ChromaSqliteStore) -> None:
    store.save_checklist("a", {**_PACK, "service_label": "A"})
    store.save_checklist("b", {**_PACK, "service_label": "B"})

    a, b = store.get_checklist("a"), store.get_checklist("b")

    assert a is not None and a["service_label"] == "A"
    assert b is not None and b["service_label"] == "B"


def test_non_ascii_survives_the_json_round_trip(store: ChromaSqliteStore) -> None:
    store.save_checklist("si", {**_PACK, "service_label": "ජාතික හැඳුනුම්පත"})

    fetched = store.get_checklist("si")

    assert fetched is not None
    assert fetched["service_label"] == "ජාතික හැඳුනුම්පත"


# ── migration off the legacy shape ────────────────────────────────
def _legacy_db(path: Path) -> None:
    """Write a database carrying the pre-Stage-7 conversation tables."""
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE session (
            id INTEGER PRIMARY KEY AUTOINCREMENT, district TEXT, created_at TEXT NOT NULL);
        CREATE TABLE session_message (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL,
            variant_id INTEGER NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL);
        """
    )
    conn.commit()
    conn.close()


def _tables(path: Path) -> set[str]:
    conn = sqlite3.connect(str(path))
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    return names


def test_legacy_tables_are_retired_and_checklist_is_reshaped(tmp_path: Path) -> None:
    db = tmp_path / "legacy.sqlite3"
    _legacy_db(db)

    store = ChromaSqliteStore(sqlite_path=db, chroma_dir=tmp_path / "chroma")

    assert "session" not in _tables(db)
    assert "session_message" not in _tables(db)
    # Reshaped, not just dropped: a TEXT thread id now round-trips.
    store.save_checklist("thread-xyz", _PACK)
    assert store.get_checklist("thread-xyz") == _PACK


def test_a_populated_legacy_table_is_left_alone(tmp_path: Path) -> None:
    """Safety rail: the migration must never silently destroy data."""
    db = tmp_path / "legacy.sqlite3"
    _legacy_db(db)
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO session (district, created_at) VALUES ('Kandy', '2026-01-01')")
    conn.commit()
    conn.close()

    ChromaSqliteStore(sqlite_path=db, chroma_dir=tmp_path / "chroma")

    assert "session" in _tables(db)
    conn = sqlite3.connect(str(db))
    assert conn.execute("SELECT COUNT(*) FROM session").fetchone()[0] == 1
    conn.close()


def test_migration_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "legacy.sqlite3"
    _legacy_db(db)

    ChromaSqliteStore(sqlite_path=db, chroma_dir=tmp_path / "chroma")
    store = ChromaSqliteStore(sqlite_path=db, chroma_dir=tmp_path / "chroma2")
    store.save_checklist("thread-xyz", _PACK)

    # A second construction must not wipe the reshaped table.
    again = ChromaSqliteStore(sqlite_path=db, chroma_dir=tmp_path / "chroma3")
    assert again.get_checklist("thread-xyz") == _PACK
