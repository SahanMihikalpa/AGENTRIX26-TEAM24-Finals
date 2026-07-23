"""``merge-services`` — fold thin duplicate catalog entries into curated ones.

The B-team acquires knowledge by crawling, and it creates **one catalog service per
page**. So a case a curated service already covers as a *variant* ("amendment",
"lost-duplicate", "certified-copy") reappears as a standalone service with almost
nothing behind it — and because its name repeats the citizen's wording, A2 picks it
over the parent. The citizen then gets the "we couldn't verify this" fallback even
though the facts exist one row away.

Two modes, deliberately separate:

* ``--suggest`` — read-only. Lists services with no documented requirements whose
  name overlaps a well-covered service, and names the variant they look like. It
  proposes; it never acts, because "is this a duplicate?" is a judgement call.
* ``--into P --duplicates A,B`` — explicit merge of exactly the ids you name.
  ``--dry-run`` first prints what would move and what would be discarded.

Merging keeps the duplicate's chunks (repointed to the parent, so retrieval still
benefits from the crawled text) and its offices/district notes; it drops the
duplicate's own auto-extracted variants, requirements and fees, because the parent
already covers those cases with curated, sourced facts.

    python -m app.cli merge-services --suggest
    python -m app.cli merge-services --into 2 --duplicates 5,6,7,9 --dry-run
    python -m app.cli merge-services --into 2 --duplicates 5,6,7,9
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.domain.entities import Service, ServiceCoverage
from app.infrastructure.config import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Words that say nothing about *which* service this is.
_NOISE = frozenset({
    "a", "an", "and", "application", "applications", "apply", "certificate", "de",
    "department", "document", "documents", "for", "form", "from", "get", "government",
    "in", "issuance", "issue", "issued", "lanka", "new", "obtain", "obtaining", "of",
    "office", "on", "online", "portal", "registration", "request", "service",
    "services", "sri", "the", "to", "your",
})


def add_arguments(parser: argparse.ArgumentParser) -> None:
    settings = get_settings()
    parser.add_argument("--sqlite", type=Path, default=settings.sqlite_path)
    parser.add_argument("--chroma", type=Path, default=settings.chroma_dir)
    parser.add_argument(
        "--suggest", action="store_true",
        help="list likely duplicates and exit (read-only; makes no changes)",
    )
    parser.add_argument(
        "--into", type=int, metavar="PARENT_ID",
        help="the curated service the duplicates should be folded into",
    )
    parser.add_argument(
        "--duplicates", type=str, metavar="IDS",
        help="comma-separated service ids to merge into --into",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="report what each merge would change, without writing",
    )


def run(args: argparse.Namespace) -> int:
    if not args.suggest and (args.into is None or not args.duplicates):
        print(
            "error: pass --suggest to see candidates, or --into ID --duplicates IDS "
            "to merge.",
            file=sys.stderr,
        )
        return 2

    store = ChromaSqliteStore(sqlite_path=args.sqlite, chroma_dir=args.chroma)

    if args.suggest:
        return _suggest(store, get_settings().confidence_threshold)
    return _merge(store, args.into, _parse_ids(args.duplicates), dry_run=args.dry_run)


# ── suggest ──────────────────────────────────────────────────────
def _suggest(store: ChromaSqliteStore, confidence_threshold: float) -> int:
    # An empty query has no usable keywords, which `find_services` documents as
    # "return the catalog head" — with a large limit that is the whole catalog.
    services = store.find_services("", limit=10_000)
    # Coverage is measured at the serving threshold, not by raw row counts: a
    # service whose only requirements come from a low-confidence crawl is gated by
    # A6 and answers nothing, which is exactly the kind of entry worth merging.
    coverage = store.get_service_coverage(
        [s.id for s in services if s.id is not None],
        min_source_confidence=confidence_threshold,
    )

    covered = [s for s in services if coverage[s.id or -1].is_answerable]
    thin = [s for s in services if not coverage[s.id or -1].is_answerable]

    findings: list[tuple[Service, Service, str, ServiceCoverage]] = []
    for candidate in thin:
        best = _best_parent(candidate, covered, store)
        if best is not None:
            parent, variant_label = best
            findings.append((candidate, parent, variant_label, coverage[parent.id or -1]))

    if not findings:
        print("No likely duplicates found — every thin service looks distinct.")
        return 0

    print(f"{len(findings)} service(s) look like duplicates of a curated one:\n")
    by_parent: dict[int, list[tuple[Service, str]]] = {}
    for candidate, parent, variant_label, _ in findings:
        by_parent.setdefault(parent.id or -1, []).append((candidate, variant_label))

    for parent_id, dupes in sorted(by_parent.items()):
        parent = next(p for _, p, _, _ in findings if p.id == parent_id)
        cov = next(c for _, p, _, c in findings if p.id == parent_id)
        print(
            f"  into id={parent_id}: {parent.name_en} "
            f"({cov.requirements} requirement(s), {cov.fees} fee(s))"
        )
        for candidate, variant_label in dupes:
            match = f" ~ variant {variant_label!r}" if variant_label else ""
            print(f"    - id={candidate.id}: {candidate.name_en}{match}")
        ids = ",".join(str(c.id) for c, _ in dupes)
        print(f"    review, then: python -m app.cli merge-services "
              f"--into {parent_id} --duplicates {ids} --dry-run\n")

    print("Nothing was changed. These are suggestions — check each one before merging.")
    return 0


def _best_parent(
    candidate: Service, covered: list[Service], store: ChromaSqliteStore
) -> tuple[Service, str] | None:
    """The covered service this thin entry most looks like, plus the variant it echoes.

    Two ways to qualify, because names vary in length:

    * the names share at least two meaningful words ("Obtaining new **National
      Identity card** for a lost..."), or
    * they share one *and* the candidate's name repeats one of the parent's variant
      labels ("**Amendment** of NIC" against the parent's ``amendment`` variant).

    The variant echo is the strongest evidence a crawled page describes a case the
    parent already covers — which is precisely what makes it a duplicate rather
    than a service in its own right.
    """
    candidate_words = _significant(candidate.name_en)
    if not candidate_words:
        return None

    best: tuple[int, Service, str] | None = None
    for parent in covered:
        if parent.id is None or parent.id == candidate.id:
            continue
        overlap = len(candidate_words & _significant(parent.name_en))
        if overlap < 1:
            continue
        variant_label = _matching_variant(candidate_words, store, parent.id)
        if overlap < 2 and not variant_label:
            continue
        score = overlap + (3 if variant_label else 0)
        if best is None or score > best[0]:
            best = (score, parent, variant_label)
    if best is None:
        return None
    return best[1], best[2]


def _matching_variant(candidate_words: set[str], store: ChromaSqliteStore, parent_id: int) -> str:
    """The parent variant whose label the candidate's name echoes, or ``""``."""
    for variant in store.list_variants(parent_id):
        label_words = {w for w in _TOKEN_RE.findall(variant.condition_label.lower()) if w}
        if label_words and label_words & candidate_words:
            return variant.condition_label
    return ""


def _significant(text: str) -> set[str]:
    return {w for w in _TOKEN_RE.findall(text.lower()) if w not in _NOISE and len(w) > 2}


# ── merge ────────────────────────────────────────────────────────
def _merge(
    store: ChromaSqliteStore, parent_id: int, duplicate_ids: list[int], *, dry_run: bool
) -> int:
    if not duplicate_ids:
        print("error: --duplicates listed no ids", file=sys.stderr)
        return 2
    if store.get_service(parent_id) is None:
        print(f"error: no service with id {parent_id}", file=sys.stderr)
        return 1

    label = "WOULD MERGE (dry run)" if dry_run else "MERGED"
    failures = 0
    for duplicate_id in duplicate_ids:
        outcome = store.merge_service(duplicate_id, parent_id, dry_run=dry_run)
        if outcome is None:
            print(f"  skipped id={duplicate_id}: unknown service, or same as --into",
                  file=sys.stderr)
            failures += 1
            continue
        print(
            f"{label}  id={outcome.duplicate_id} {outcome.duplicate_name!r}\n"
            f"           -> id={outcome.parent_id} {outcome.parent_name!r}\n"
            f"           keeps  : {outcome.chunks_moved} chunk(s), "
            f"{outcome.offices_relinked} office link(s), "
            f"{outcome.district_variations_relinked} district note(s)\n"
            f"           discards: {outcome.variants_dropped} variant(s), "
            f"{outcome.requirements_dropped} requirement(s), {outcome.fees_dropped} fee(s)"
        )

    if dry_run:
        print("\nDry run — nothing was written. Re-run without --dry-run to apply.")
    return 1 if failures else 0


def _parse_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.append(int(part))
            except ValueError:
                print(f"error: {part!r} is not a service id", file=sys.stderr)
                return []
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli merge-services", description=__doc__
    )
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
