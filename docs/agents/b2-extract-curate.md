# B2 · Extract & Curate

**Team:** Knowledge Acquisition · **Type:** LLM (structured output)

## Issue it solves
Raw gazette/circular/portal text (and citizen experience reports) is unstructured and noisy. To be
usable and trustworthy, it must become **clean, schema-shaped records with provenance**.

## Single responsibility
Transform raw evidence into validated canonical records (`SERVICE`, `SERVICE_VARIANT`,
`REQUIREMENT`, `FEE`, `OFFICE`, `DISTRICT_VARIATION`) + a `SOURCE` row.

## Inputs → Outputs
- **Input:** raw documents from B1 (or an experience report), the canonical schema.
- **Output:** validated records + a `SOURCE` (`url`, `type`, `published_date`, `retrieved_date`,
  `confidence`, `verification_status = auto_gathered`).

## Step logic
1. Extract candidate facts (documents, fees, office, district notes) from the text.
2. Map them to the Pydantic schema; attach `source_id` to every fact.
3. Assign a `confidence` (source authority × extraction certainty).
4. Validate; drop anything unmapped or low-confidence-without-source.

## Decisions & technologies
- **Decision:** **schema-constrained extraction** with mandatory provenance on every fact.
- **Tech:** Gemini Flash structured output + Pydantic v2 validation.

## Alternatives
| Alternative | Why not |
|---|---|
| Store raw text only (no structuring) | Can't produce exact fees/office or a deterministic Action Pack. |
| Regex extraction | Too brittle for varied government document formats. |

## Why optimal
Structured + provenanced records make self-gathered knowledge **as usable as seeded data** while
staying clearly labelled and auditable — essential for trust.

## Guardrails
No fact without a `source_id`; low-confidence items flagged for B4; never overwrite `verified` data
with `auto_gathered` data (B3 handles the merge policy).

## State touched
Produces curated records for B3.
