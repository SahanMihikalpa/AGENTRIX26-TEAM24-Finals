# A2 · Service Identifier

**Team:** Answering · **Type:** LLM + retrieval (classification)

## Issue it solves
A coarse `service_guess` must be resolved to a **specific, known service record** (`service_id`) —
or recognised as not-yet-known so the gap path can handle it.

## Single responsibility
Map the intake intent to exactly one `SERVICE` in the catalog (or `unknown`).

## Inputs → Outputs
- **Input:** `intent` (from A1), the service catalog.
- **Output:** `service_id` (or `null` + `unknown=true`), with a confidence.

## Step logic
1. Embed/normalise `normalized_query`; match against the `SERVICE` catalog (vector + alias table).
2. If top match ≥ threshold → set `service_id`.
3. Else mark `unknown` → downstream this becomes a likely `GAP` (a new service to acquire).

## Decisions & technologies
- **Decision:** **retrieval-assisted classification** — match against the catalog rather than asking
  the LLM to invent a service id.
- **Tech:** ChromaDB similarity over service names/aliases + a short Gemini disambiguation call when
  two candidates are close.

## Alternatives
| Alternative | Why not |
|---|---|
| Pure LLM "name the service" | Can hallucinate non-existent services; not grounded in the catalog. |
| Fixed intent classifier model | Needs training data we don't have; can't grow with new services. |

## Why optimal
Grounding identification in the actual catalog keeps it **honest and extensible** — unknown services
naturally route into the self-expanding acquisition path instead of producing a wrong answer.

## Guardrails
Never force a low-confidence match; prefer `unknown` and let acquisition fill the gap.

## State touched
Writes `service_id`.
