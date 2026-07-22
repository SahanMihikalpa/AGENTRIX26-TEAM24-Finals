"""Seed the knowledge base from a catalog JSON file.

Depends only on the ports (:class:`KnowledgeStore`, :class:`EmbeddingProvider`),
so it runs against the real store or a fake. The JSON contract is documented in
``data/seed/catalog.example.json`` and ``data/seed/README.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from app.domain.entities import (
    DistrictVariation,
    Fee,
    KBChunk,
    Office,
    OfficeType,
    Requirement,
    Service,
    ServiceCategory,
    ServiceVariant,
    Source,
    SourceType,
    VerificationStatus,
)
from app.domain.ports.embeddings import EmbeddingProvider
from app.domain.ports.knowledge import KnowledgeStore


@dataclass(frozen=True, slots=True)
class SeedStats:
    """Counts of what a seed run inserted."""

    sources: int = 0
    services: int = 0
    variants: int = 0
    requirements: int = 0
    fees: int = 0
    offices: int = 0
    district_variations: int = 0
    chunks: int = 0


_E = TypeVar("_E", bound=StrEnum)
_VALID_CATEGORIES = frozenset(category.value for category in ServiceCategory)


def validate_catalog(data: dict[str, Any], *, check_category: bool = True) -> list[str]:
    """Return human-readable problems with a catalog dict (empty list == valid).

    Always checks data integrity: referential integrity (every ``source_key``
    resolves to a declared source), enum membership (``source_type`` /
    ``verification_status`` / ``office_type``), Decimal-parseable fees, and
    required fields. When ``check_category`` is set, also enforces the
    :class:`ServiceCategory` vocabulary — the CLI does this (curation policy for
    authored seed data); :meth:`KnowledgeSeeder.load` does not, so programmatic /
    auto-gathered data may carry a free-form category (mirroring B3).
    """
    errors: list[str] = []
    source_keys = _validate_sources(data.get("sources", []), errors)
    slugs: set[str] = set()
    for index, service in enumerate(data.get("services", [])):
        _validate_service(index, service, source_keys, slugs, errors, check_category)
    return errors


def _validate_sources(raw: list[dict[str, Any]], errors: list[str]) -> set[str]:
    keys: set[str] = set()
    for index, src in enumerate(raw):
        loc = f"sources[{index}]"
        key = src.get("key")
        if not key:
            errors.append(f"{loc}: missing 'key'")
        elif key in keys:
            errors.append(f"{loc}: duplicate source key '{key}'")
        else:
            keys.add(str(key))
        if not src.get("title"):
            errors.append(f"{loc}: missing 'title'")
        _check_enum(errors, loc, "source_type", src.get("source_type", "portal"), SourceType)
        _check_enum(
            errors,
            loc,
            "verification_status",
            src.get("verification_status", "verified"),
            VerificationStatus,
        )
    return keys


def _validate_service(
    index: int,
    service: dict[str, Any],
    source_keys: set[str],
    slugs: set[str],
    errors: list[str],
    check_category: bool,
) -> None:
    loc = f"services[{index}]"
    slug = service.get("slug")
    if not slug:
        errors.append(f"{loc}: missing 'slug'")
    elif slug in slugs:
        errors.append(f"{loc}: duplicate slug '{slug}'")
    else:
        slugs.add(str(slug))
    if not service.get("name_en"):
        errors.append(f"{loc}: missing 'name_en'")
    if check_category:
        category = service.get("category", "")
        if not category:
            errors.append(f"{loc}: missing 'category' (one of {sorted(_VALID_CATEGORIES)})")
        elif category not in _VALID_CATEGORIES:
            errors.append(
                f"{loc}: unknown category '{category}' (one of {sorted(_VALID_CATEGORIES)})"
            )

    for j, variant in enumerate(service.get("variants", [])):
        vloc = f"{loc}.variants[{j}]"
        if not variant.get("condition_label"):
            errors.append(f"{vloc}: missing 'condition_label'")
        for k, req in enumerate(variant.get("requirements", [])):
            rloc = f"{vloc}.requirements[{k}]"
            if not req.get("document_name"):
                errors.append(f"{rloc}: missing 'document_name'")
            _check_source_ref(errors, rloc, req.get("source_key"), source_keys)
        for k, fee in enumerate(variant.get("fees", [])):
            floc = f"{vloc}.fees[{k}]"
            if not fee.get("label"):
                errors.append(f"{floc}: missing 'label'")
            _check_decimal(errors, floc, fee.get("amount_lkr"))
            _check_source_ref(errors, floc, fee.get("source_key"), source_keys)

    for j, office in enumerate(service.get("offices", [])):
        oloc = f"{loc}.offices[{j}]"
        if not office.get("name"):
            errors.append(f"{oloc}: missing 'name'")
        if not office.get("district"):
            errors.append(f"{oloc}: missing 'district'")
        _check_enum(errors, oloc, "office_type", office.get("office_type", "other"), OfficeType)

    for j, variation in enumerate(service.get("district_variations", [])):
        dloc = f"{loc}.district_variations[{j}]"
        if not variation.get("district"):
            errors.append(f"{dloc}: missing 'district'")
        _check_source_ref(errors, dloc, variation.get("source_key"), source_keys)

    for j, chunk in enumerate(service.get("chunks", [])):
        cloc = f"{loc}.chunks[{j}]"
        if not chunk.get("content"):
            errors.append(f"{cloc}: missing 'content'")
        _check_source_ref(errors, cloc, chunk.get("source_key"), source_keys)


def _check_enum(errors: list[str], loc: str, field: str, value: Any, enum_cls: type[_E]) -> None:
    try:
        enum_cls(value)
    except ValueError:
        valid = [member.value for member in enum_cls]
        errors.append(f"{loc}: invalid {field} '{value}' (one of {valid})")


def _check_source_ref(errors: list[str], loc: str, key: Any, source_keys: set[str]) -> None:
    if not key:
        errors.append(f"{loc}: missing 'source_key'")
    elif key not in source_keys:
        errors.append(f"{loc}: unknown source_key '{key}'")


def _check_decimal(errors: list[str], loc: str, value: Any) -> None:
    try:
        Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        errors.append(f"{loc}: amount_lkr '{value}' is not a valid decimal")


class KnowledgeSeeder:
    """Loads a catalog JSON into the knowledge base (structured rows + vectors)."""

    def __init__(self, store: KnowledgeStore, embedder: EmbeddingProvider) -> None:
        self._store = store
        self._embedder = embedder

    def load_from_json(self, path: Path) -> SeedStats:
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.load(data)

    def load(self, data: dict[str, Any]) -> SeedStats:
        problems = validate_catalog(data, check_category=False)
        if problems:
            raise ValueError("catalog failed validation:\n  - " + "\n  - ".join(problems))
        sources = self._load_sources(data.get("sources", []))
        counts = {"services": 0, "variants": 0, "requirements": 0, "fees": 0,
                  "offices": 0, "district_variations": 0, "chunks": 0}
        pending_chunks: list[KBChunk] = []
        pending_texts: list[str] = []

        for service_raw in data.get("services", []):
            service = self._store.add_service(
                Service(
                    name_en=service_raw["name_en"],
                    slug=service_raw["slug"],
                    category=service_raw.get("category", ""),
                    description=service_raw.get("description", ""),
                )
            )
            service_id = _require_id(service.id)
            counts["services"] += 1

            for variant_raw in service_raw.get("variants", []):
                variant = self._store.add_variant(
                    ServiceVariant(
                        service_id=service_id,
                        condition_label=variant_raw["condition_label"],
                        description=variant_raw.get("description", ""),
                    )
                )
                variant_id = _require_id(variant.id)
                counts["variants"] += 1

                for req in variant_raw.get("requirements", []):
                    self._store.add_requirement(
                        Requirement(
                            variant_id=variant_id,
                            source_id=_require_id(sources[req["source_key"]].id),
                            document_name=req["document_name"],
                            is_mandatory=bool(req.get("is_mandatory", True)),
                            notes=req.get("notes", ""),
                        )
                    )
                    counts["requirements"] += 1

                for fee in variant_raw.get("fees", []):
                    self._store.add_fee(
                        Fee(
                            variant_id=variant_id,
                            source_id=_require_id(sources[fee["source_key"]].id),
                            label=fee["label"],
                            amount_lkr=Decimal(str(fee["amount_lkr"])),
                            notes=fee.get("notes", ""),
                        )
                    )
                    counts["fees"] += 1

            for office_raw in service_raw.get("offices", []):
                office = self._store.add_office(
                    Office(
                        name=office_raw["name"],
                        office_type=OfficeType(office_raw.get("office_type", "other")),
                        district=office_raw["district"],
                        address=office_raw.get("address", ""),
                        hours=office_raw.get("hours", ""),
                        contact=office_raw.get("contact", ""),
                    )
                )
                self._store.link_service_office(service_id, _require_id(office.id))
                counts["offices"] += 1

            for variation_raw in service_raw.get("district_variations", []):
                self._store.add_district_variation(
                    DistrictVariation(
                        service_id=service_id,
                        source_id=_require_id(sources[variation_raw["source_key"]].id),
                        district=variation_raw["district"],
                        notes=variation_raw.get("notes", ""),
                    )
                )
                counts["district_variations"] += 1

            for index, chunk_raw in enumerate(service_raw.get("chunks", [])):
                pending_chunks.append(
                    KBChunk(
                        source_id=_require_id(sources[chunk_raw["source_key"]].id),
                        service_id=service_id,
                        content=chunk_raw["content"],
                        chunk_index=chunk_raw.get("chunk_index", index),
                    )
                )
                pending_texts.append(chunk_raw["content"])
                counts["chunks"] += 1

        if pending_chunks:
            self._store.upsert_chunks(pending_chunks, self._embedder.embed_documents(pending_texts))

        return SeedStats(sources=len(sources), **counts)

    def _load_sources(self, raw_sources: list[dict[str, Any]]) -> dict[str, Source]:
        stored: dict[str, Source] = {}
        for entry in raw_sources:
            source = Source(
                title=entry["title"],
                url=entry.get("url"),
                source_type=SourceType(entry.get("source_type", "portal")),
                published_date=_parse_date(entry.get("published_date")),
                retrieved_date=_parse_date(entry.get("retrieved_date")) or date.today(),
                confidence=float(entry.get("confidence", 1.0)),
                verification_status=VerificationStatus(
                    entry.get("verification_status", "verified")
                ),
            )
            stored[entry["key"]] = self._store.upsert_source(
                source, content_hash=entry.get("content_hash")
            )
        return stored


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _require_id(value: int | None) -> int:
    if value is None:
        raise RuntimeError("knowledge store did not assign an id on insert")
    return value
