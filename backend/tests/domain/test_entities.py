"""Unit tests for the pure domain entities."""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities import (
    ActionPack,
    ActionPackVerification,
    Citation,
    DocumentItem,
    Fee,
    FeeLine,
    Grade,
    Service,
    Source,
    SourceType,
    VerificationStatus,
)


def test_enums_serialize_as_strings() -> None:
    assert Grade.GAP == "GAP"
    assert VerificationStatus.AUTO_GATHERED == "auto_gathered"
    assert str(SourceType.GAZETTE) == "gazette"
    assert ActionPackVerification.NEWLY_GATHERED_PENDING_VERIFICATION.value == (
        "newly_gathered_pending_verification"
    )


def test_entities_are_frozen() -> None:
    svc = Service(
        name_en="NIC Renewal", slug="nic_renewal", category="identity", description="..."
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        svc.name_en = "changed"  # type: ignore[misc]


def test_fee_amount_is_decimal_not_float() -> None:
    fee = Fee(variant_id=1, source_id=2, label="Stamp duty", amount_lkr=Decimal("100.00"))
    assert isinstance(fee.amount_lkr, Decimal)


def test_source_is_hashable() -> None:
    # frozen + slots → usable as a dict key / set member.
    source = Source(
        title="Gazette 2024",
        source_type=SourceType.GAZETTE,
        retrieved_date=date(2026, 6, 20),
        confidence=0.9,
        verification_status=VerificationStatus.VERIFIED,
    )
    assert hash(source)
    assert source.url is None  # optional by default


def test_action_pack_composes_grounded_facts() -> None:
    pack = ActionPack(
        service_label="Land Deed Transfer (inheritance)",
        district="Galle",
        documents=(DocumentItem(name="Original deed", mandatory=True, source_id=12),),
        fees=(FeeLine(label="Stamp duty", amount_lkr=Decimal("0")),),
        office=None,
        steps=("Visit the DS office",),
        estimated_cost_lkr=Decimal("0"),
        verification=ActionPackVerification.VERIFIED,
        citations=(
            Citation(title="Gazette", url="https://x.gov.lk", last_verified=date(2026, 6, 20)),
        ),
    )
    assert pack.documents[0].mandatory is True
    assert pack.verification == "verified"
    assert pack.fallback is False
