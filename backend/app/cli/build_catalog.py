"""``build`` — turn raw seed documents into a ``catalog.json`` skeleton.

Each immediate sub-directory of ``--raw-dir`` is treated as one **service** (its
folder name becomes the slug); every readable document inside becomes a ``SOURCE``
and its cleaned text is chunked into ``chunks[]`` for embedding. Scanned/empty
files are skipped and garbled (non-prose) chunks are dropped, so the emitted
skeleton is clean English text ready for the bge-en embedder.

Structured facts (``variants`` / ``requirements`` / ``fees`` / ``offices``) are
left as **empty stubs** for human curation — this tool only mechanises provenance
and chunking; it never invents government facts. After running it, fill the stubs
(and the ``category`` + real source ``url``s) and load with ``python -m app.cli
seed``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from app.adapters.knowledge.chunking import chunk_text, looks_like_prose
from app.adapters.parser.pymupdf import PyMuPdfSourceParser
from app.domain.entities import SourceType
from app.domain.ports.parser import ParsedDocument, SourceParser

_PDF_EXT = {".pdf"}
_HTML_EXT = {".html", ".htm"}
_TXT_EXT = {".txt"}
_SUPPORTED = _PDF_EXT | _HTML_EXT | _TXT_EXT
_MIN_DOC_CHARS = 120  # below this a PDF is treated as scanned / empty


@dataclass(slots=True)
class FileOutcome:
    """What happened to one raw file during a build."""

    path: str
    status: str  # "ok" | "skipped-empty" | "skipped-nonprose" | "skipped-unsupported"
    chunks: int = 0
    dropped: int = 0


@dataclass(slots=True)
class BuildReport:
    """Totals + per-file outcomes from :func:`build_catalog_skeleton`."""

    services: int = 0
    sources: int = 0
    chunks: int = 0
    files: list[FileOutcome] = field(default_factory=list)


def build_catalog_skeleton(
    raw_dir: Path,
    parser: SourceParser,
    *,
    max_chunk_chars: int = 1000,
    overlap: int = 120,
) -> tuple[dict[str, Any], BuildReport]:
    """Parse + chunk every service folder under ``raw_dir`` into a catalog skeleton.

    Returns the catalog dict (``sources`` + ``services`` with chunks; structured
    facts stubbed) and a :class:`BuildReport`. Pure apart from filesystem reads —
    writing the JSON is the CLI wrapper's job.
    """
    report = BuildReport()
    sources: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    used_keys: set[str] = set()
    today = date.today().isoformat()

    for service_dir in sorted(d for d in raw_dir.iterdir() if d.is_dir()):
        svc_sources, svc_chunks, outcomes = _process_service(
            service_dir, parser, used_keys, today,
            max_chunk_chars=max_chunk_chars, overlap=overlap,
        )
        sources.extend(svc_sources)
        report.files.extend(outcomes)
        report.chunks += sum(o.chunks for o in outcomes)
        services.append(_service_stub(service_dir.name, svc_chunks))
        report.services += 1

    report.sources = len(sources)
    catalog = {
        "_comment": (
            "GENERATED skeleton — sources[] + chunks[] are auto-filled. Fill each "
            "service's category (see ServiceCategory), variants/requirements/fees/"
            "offices, and real source url/dates, then load with `python -m app.cli "
            "seed`. See data/seed/README.md."
        ),
        "sources": sources,
        "services": services,
    }
    return catalog, report


def _process_service(
    service_dir: Path,
    parser: SourceParser,
    used_keys: set[str],
    today: str,
    *,
    max_chunk_chars: int,
    overlap: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[FileOutcome]]:
    slug = _slugify(service_dir.name)
    sources: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    outcomes: list[FileOutcome] = []
    for file in sorted(f for f in service_dir.iterdir() if f.is_file()):
        outcome, source, file_chunks = _process_file(
            file, slug, used_keys, today, parser,
            max_chunk_chars=max_chunk_chars, overlap=overlap,
        )
        outcomes.append(outcome)
        if source is not None:
            sources.append(source)
            chunks.extend(file_chunks)
    return sources, chunks, outcomes


def _process_file(
    file: Path,
    slug: str,
    used_keys: set[str],
    today: str,
    parser: SourceParser,
    *,
    max_chunk_chars: int,
    overlap: int,
) -> tuple[FileOutcome, dict[str, Any] | None, list[dict[str, Any]]]:
    rel = f"{file.parent.name}/{file.name}"
    ext = file.suffix.lower()
    if ext not in _SUPPORTED:
        return FileOutcome(rel, "skipped-unsupported"), None, []

    parsed = _parse_file(file, ext, parser)
    text = parsed.text.strip()
    if len(text) < _MIN_DOC_CHARS:
        return FileOutcome(rel, "skipped-empty"), None, []

    pieces = chunk_text(text, max_chars=max_chunk_chars, overlap=overlap)
    kept = [piece for piece in pieces if looks_like_prose(piece)]
    dropped = len(pieces) - len(kept)
    if not kept:
        return FileOutcome(rel, "skipped-nonprose", dropped=dropped), None, []

    key = _unique_key(slug, file.stem, used_keys)
    source = {
        "key": key,
        "title": parsed.title or _humanize(file.stem),
        "url": parsed.url,  # usually None — fill the real *.gov.lk url before serving citations
        "source_type": parsed.source_type.value,
        "published_date": parsed.published_date.isoformat() if parsed.published_date else None,
        "retrieved_date": today,
        "confidence": 1.0,
        "verification_status": "verified",
    }
    chunks = [
        {"content": piece, "source_key": key, "chunk_index": index}
        for index, piece in enumerate(kept)
    ]
    return FileOutcome(rel, "ok", chunks=len(kept), dropped=dropped), source, chunks


def _parse_file(file: Path, ext: str, parser: SourceParser) -> ParsedDocument:
    if ext in _PDF_EXT:
        return parser.parse_pdf(file.read_bytes())
    if ext in _HTML_EXT:
        return parser.parse_html(file.read_text(encoding="utf-8", errors="replace"))
    return ParsedDocument(  # .txt — already clean text, no medium to infer from
        text=file.read_text(encoding="utf-8", errors="replace"),
        source_type=SourceType.PORTAL,
    )


def _service_stub(dir_name: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "slug": _slugify(dir_name),
        "name_en": _humanize(dir_name),
        "category": "",  # STUB — set to a ServiceCategory value
        "description": "",  # STUB
        "variants": [],  # STUB — add condition_label + requirements[] + fees[]
        "offices": [],  # STUB
        "district_variations": [],  # STUB
        "chunks": chunks,
    }


def _slugify(name: str) -> str:
    out = "".join(char if char.isalnum() else "-" for char in name.lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def _humanize(name: str) -> str:
    return " ".join(word.capitalize() for word in _slugify(name).split("-") if word)


def _unique_key(slug: str, stem: str, used: set[str]) -> str:
    base = f"{slug}__{_slugify(stem)}".strip("-_") or slug
    key = base
    suffix = 2
    while key in used:
        key = f"{base}-{suffix}"
        suffix += 1
    used.add(key)
    return key


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--raw-dir", type=Path, default=Path("data/seed/raw"),
                        help="root of per-service raw folders (default: data/seed/raw)")
    parser.add_argument("--out", type=Path, default=Path("data/seed/catalog.generated.json"),
                        help="skeleton output path (default: data/seed/catalog.generated.json)")
    parser.add_argument("--max-chunk-chars", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=120)
    parser.add_argument("--force", action="store_true", help="overwrite --out if it exists")


def run(args: argparse.Namespace) -> int:
    raw_dir: Path = args.raw_dir
    out: Path = args.out
    if not raw_dir.is_dir():
        print(f"error: raw dir not found: {raw_dir}", file=sys.stderr)
        return 2
    if out.exists() and not args.force:
        print(f"error: refusing to overwrite {out} (use --force)", file=sys.stderr)
        return 2

    catalog, report = build_catalog_skeleton(
        raw_dir, PyMuPdfSourceParser(),
        max_chunk_chars=args.max_chunk_chars, overlap=args.overlap,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    _print_report(report, out)
    return 0


def _print_report(report: BuildReport, out: Path) -> None:
    print(f"\nScanned {len(report.files)} files across {report.services} service(s):\n")
    current_dir = ""
    for outcome in report.files:
        folder = outcome.path.split("/", 1)[0]
        if folder != current_dir:
            print(f"  {folder}/")
            current_dir = folder
        name = outcome.path.split("/", 1)[-1]
        detail = f"{outcome.chunks} chunks" if outcome.status == "ok" else outcome.status
        if outcome.dropped:
            detail += f" ({outcome.dropped} non-prose dropped)"
        flag = "ok " if outcome.status == "ok" else "-- "
        print(f"    [{flag}] {name:<45} {detail}")
    print(
        f"\nWrote {out}\n"
        f"  {report.sources} sources, {report.chunks} chunks, {report.services} service stubs.\n"
        f"Next: fill category + variants/requirements/fees/offices, then "
        f"`python -m app.cli seed --catalog {out}` (add --dry-run to validate first)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli build", description=__doc__)
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
