# `application/agents/b2_curate.py` — B2 · Extract & Curate

**Layer:** application/agents · **Team 2** · **Stage:** 4b · [doc](../../../agents/b2-extract-curate.md)

## 🎯 කාර්යය
Raw evidence → **validated, provenanced records**. `acquisition_buffer` එකේ හැම document එකක්ම එක
schema-constrained `CuratedExtraction` එකක් වෙනවා (service + variant + requirements + fees + offices),
`auto_gathered` SOURCE එකක් සමඟ pair වෙනවා.

## 🔍 Code Walkthrough
`ExtractCurateAgent(llm, *, pool/web/experience_authority, today)` — `__call__`:
- හැම buffer entry එකකටම **LLM structured extract** (`CuratedExtraction`). System prompt: "Use ONLY what
  the text supports — never invent."
- **Guardrail:** `service_name`/`service_slug` හිස් නම් **drop** (mappable fact එකක් නෑ).
- **Confidence formula:** `confidence = source_authority × extraction_certainty`. Authority: pool **0.8** >
  web **0.5** > experience **0.4** (local pool වඩා trusted). `[0,1]` clamp + round.
- Record එකේ: `source` (auto_gathered), `extraction` (model_dump), `text`.

## 🔗 සම්බන්ධතා
- **Uses:** [`LLMProvider`](../../domain/ports/llm.md), [`CuratedExtraction`](schemas.md).
- **Feeds:** B3 (via `curated`), B4 (moderation queue).

## 💡 Design decision
Provenance mandatory — හැම fact එකකටම source එකක්. Web snippet එකකට වඩා pool document එකකට වැඩි confidence.
Extraction certainty LLM එකෙන්ම report කරනවා → gate (AD-8) එකට feed වෙනවා.
