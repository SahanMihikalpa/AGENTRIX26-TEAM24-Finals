# `application/agents/schemas.py` — LLM structured-output schemas

**Layer:** application · **Stage:** 4 · **Uses:** Pydantic

## 🎯 කාර්යය
LLM agents ගේ **structured output contracts** (Pydantic models). `LLMProvider.complete_structured(prompt,
schema)` එකට දෙන `schema` එක මේවා. **Application layer එකේ තියෙන්නේ ඇයි?** — port එක schema type එකට
generic නිසා **domain එක Pydantic import කරන්නේ නෑ**; concrete schemas මෙතන.

## 🔍 Schemas (එක agent එකකට එකක්)
- `IntentExtraction` (+`IntentEntities`) — **A1**: `normalized_query`, `service_guess`, `entities`, `ambiguous`.
- `ServiceDisambiguation` — **A2**: `service_id` (candidates වලින් එකක්/null), `confidence`, `reason`.
- `ClarificationQuestion` — **A3**: `question` + `options` (options catalog-grounded, LLM phrase විතරයි).
- `GradeDecision` — **A5**: `grade` (`SUFFICIENT`/`GAP` Literal), `confidence`, `reason`.
- `ActionSteps` — **A6**: `steps` list (narrative විතරයි LLM-generated).
- **Team 2:** `CuratedRequirement`/`CuratedFee`/`CuratedOffice` + `CuratedExtraction` — **B2** canonical
  records (money = string, no float; provenance mandatory).

## 💡 Design decision
Schema-constrained generation → prose parse කරනවා නෙවෙයි, **validated** output. හැම agent එකකටම එකම pattern:
LLM එකට schema එකක් දීලා, ආපහු එන object එක type-safe. Hard facts (fees, docs) LLM එකෙන් හදන්නේ නෑ —
narrative විතරයි.
