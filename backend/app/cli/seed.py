"""``seed`` — load a ``catalog.json`` into SQLite + Chroma via the knowledge ports.

Validates the catalog first (referential integrity, enums, category, Decimal
fees); ``--dry-run`` stops there so a hand-authored catalog can be checked without
loading torch or touching the stores. Paths default to the values in ``Settings``
(relative to ``backend/`` — run this from the ``backend`` directory).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.adapters.embeddings.bge import BgeEmbeddingProvider
from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder, validate_catalog
from app.infrastructure.config import get_settings


def add_arguments(parser: argparse.ArgumentParser) -> None:
    settings = get_settings()
    parser.add_argument("--catalog", type=Path, default=settings.data_dir / "seed" / "catalog.json",
                        help="catalog JSON to load (default: data/seed/catalog.json)")
    parser.add_argument("--sqlite", type=Path, default=settings.sqlite_path)
    parser.add_argument("--chroma", type=Path, default=settings.chroma_dir)
    parser.add_argument("--dry-run", action="store_true",
                        help="validate only — no embeddings, no DB writes")


def run(args: argparse.Namespace) -> int:
    catalog_path: Path = args.catalog
    if not catalog_path.is_file():
        print(f"error: catalog not found: {catalog_path}", file=sys.stderr)
        return 2

    data: dict[str, Any] = json.loads(catalog_path.read_text(encoding="utf-8"))
    problems = validate_catalog(data)
    if problems:
        print(f"catalog INVALID — {len(problems)} problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    sources = len(data.get("sources", []))
    services = len(data.get("services", []))
    if args.dry_run:
        print(f"valid: {sources} sources, {services} services. (dry-run — nothing written)")
        return 0

    sqlite_path: Path = args.sqlite
    chroma_dir: Path = args.chroma
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    store = ChromaSqliteStore(sqlite_path, chroma_dir)
    seeder = KnowledgeSeeder(store, BgeEmbeddingProvider(get_settings().embedding_model))

    print(f"Embedding + loading {catalog_path} (first run downloads the bge model)...")
    stats = seeder.load(data)
    print(
        "Seeded knowledge base:\n"
        f"  sources={stats.sources} services={stats.services} variants={stats.variants}\n"
        f"  requirements={stats.requirements} fees={stats.fees} offices={stats.offices}\n"
        f"  district_variations={stats.district_variations} chunks={stats.chunks}\n"
        f"  -> {sqlite_path}  +  {chroma_dir}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli seed", description=__doc__)
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
