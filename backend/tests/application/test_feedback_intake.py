"""``ExperienceReportIntake`` — persist always, ingest via B2→B3 best-effort.

Exercised against a real seeded ``ChromaSqliteStore`` (so the B3 write/dedup is
genuine) with a ``ScriptedLLM`` standing in for B2's extraction.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.agents.schemas import CuratedExtraction, CuratedRequirement
from app.application.feedback import ExperienceReportIntake
from app.domain.entities import ExperienceReport, ReportOutcome, ReportStatus
from tests.application.conftest import DeterministicEmbedder, ScriptedLLM, SeededKB


def _report(kb: SeededKB, *, text: str, outcome: ReportOutcome) -> ExperienceReport:
    return ExperienceReport(
        service_id=kb.deed_service_id,
        district="Galle",
        report_text=text,
        reported_outcome=outcome,
        status=ReportStatus.PENDING,
        created_at=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
    )


def test_submit_persists_and_grows_kb(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    llm = ScriptedLLM(
        structured={
            CuratedExtraction: CuratedExtraction(
                service_name="Land Deed Transfer",
                service_slug="land_deed_transfer",  # existing → B3 reuses it
                condition_label="inheritance",  # existing variant → reused
                requirements=[CuratedRequirement(document_name="Witness affidavit")],
                district="Galle",
                extraction_confidence=0.9,
            )
        }
    )
    intake = ExperienceReportIntake(kb.store, llm, embedder)

    saved = intake.submit(
        _report(
            kb,
            text="At DS Galle they also asked for a witness affidavit.",
            outcome=ReportOutcome.EXTRA_DOC,
        )
    )

    assert saved.id is not None
    assert saved.status is ReportStatus.PENDING
    # the curated doc was written against the existing inheritance variant ...
    docs = [r.document_name for r in kb.store.get_requirements(kb.inheritance_variant_id)]
    assert "Witness affidavit" in docs
    # ... and its source is auto_gathered + experience → it lands in the review queue
    queue = kb.store.list_sources_for_moderation()
    assert len(queue) == 1
    assert queue[0].source_type.value == "experience"
    assert queue[0].verification_status.value == "auto_gathered"


def test_vague_report_saved_without_kb_change(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    # B2 yields no identifiable service → the record is dropped (no KB write).
    llm = ScriptedLLM(structured={CuratedExtraction: CuratedExtraction()})
    intake = ExperienceReportIntake(kb.store, llm, embedder)
    before = len(kb.store.get_requirements(kb.inheritance_variant_id))

    saved = intake.submit(
        _report(kb, text="The info was correct, thanks!", outcome=ReportOutcome.MATCHED)
    )

    assert saved.id is not None  # the feedback is still recorded
    assert kb.store.list_sources_for_moderation() == []  # nothing ingested
    assert len(kb.store.get_requirements(kb.inheritance_variant_id)) == before


def test_ingestion_failure_never_loses_the_report(
    kb: SeededKB, embedder: DeterministicEmbedder
) -> None:
    # No scripted extraction → B2 raises; the intake must still persist the report.
    llm = ScriptedLLM(structured={})
    intake = ExperienceReportIntake(kb.store, llm, embedder)

    saved = intake.submit(
        _report(kb, text="They asked for an extra document.", outcome=ReportOutcome.OTHER)
    )

    assert saved.id is not None
    assert kb.store.list_sources_for_moderation() == []
