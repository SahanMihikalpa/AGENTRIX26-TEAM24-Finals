"""A corrupt checkpoint database must not wedge the whole service.

SQLite in WAL mode can be left torn when the process dies mid-write (a container
restart does it), and the saver is read *before* the graph runs — so without
recovery every chat request fails permanently with "file is not a database".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.api.runtime import _build_checkpointer, _is_readable_sqlite
from app.infrastructure.config import Settings


def _settings(data_dir: Path) -> Settings:
    return Settings(data_dir=data_dir)


def test_healthy_checkpoint_file_is_left_alone(tmp_path: Path) -> None:
    saver = _build_checkpointer(_settings(tmp_path))
    saver.setup()
    del saver

    before = (tmp_path / "checkpoints.sqlite3").read_bytes()
    _build_checkpointer(_settings(tmp_path))

    assert (tmp_path / "checkpoints.sqlite3").read_bytes() == before
    assert not list(tmp_path.glob("*.corrupt-*.sqlite3"))


def test_corrupt_checkpoint_file_is_quarantined_not_deleted(tmp_path: Path) -> None:
    corrupt = tmp_path / "checkpoints.sqlite3"
    corrupt.write_bytes(b"this is definitely not a sqlite database")
    (tmp_path / "checkpoints.sqlite3-wal").write_bytes(b"stale wal")

    saver = _build_checkpointer(_settings(tmp_path))

    # Checked before setup(): the saver switches the fresh database to WAL mode,
    # which legitimately recreates a -wal sidecar of its own.
    assert not (tmp_path / "checkpoints.sqlite3-wal").exists(), "stale sidecar removed"

    saver.setup()  # proves the replacement file is usable

    quarantined = list(tmp_path.glob("*.corrupt-*.sqlite3"))
    assert len(quarantined) == 1, "the bad file must be kept for a post-mortem"
    assert quarantined[0].read_bytes() == b"this is definitely not a sqlite database"
    assert _is_readable_sqlite(corrupt), "a fresh, usable database took its place"


def test_missing_checkpoint_file_is_simply_created(tmp_path: Path) -> None:
    saver = _build_checkpointer(_settings(tmp_path))
    saver.setup()

    assert (tmp_path / "checkpoints.sqlite3").exists()
    assert not list(tmp_path.glob("*.corrupt-*.sqlite3"))


@pytest.mark.parametrize(
    ("content", "readable"),
    [(b"", True), (b"not sqlite at all", False)],
)
def test_readability_probe(tmp_path: Path, content: bytes, readable: bool) -> None:
    # An empty file is a valid, empty SQLite database — it must not be quarantined.
    probe = tmp_path / "probe.sqlite3"
    probe.write_bytes(content)

    assert _is_readable_sqlite(probe) is readable
