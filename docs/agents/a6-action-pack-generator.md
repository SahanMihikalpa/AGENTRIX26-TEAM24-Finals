# A6 · Action-Pack Generator

**Team:** Answering · **Type:** LLM (structured output) → PDF

## Issue it solves
The citizen needs a concrete, **takeaway artifact** — not a wall of chat text. The output of the
problem statement is literally "a clear printed checklist they can take with them."

## Single responsibility
Compose the grounded, cited **Action Pack** from `retrieved` evidence and render it for print/PDF.

## Inputs → Outputs
- **Input:** `retrieved`, `variant_id`, `slots`, `grade` (incl. fallback mode).
- **Output (Pydantic):**
  ```json
  {
    "service": "Land Deed Transfer (inheritance)",
    "district": "Galle",
    "documents": [{ "name": "...", "mandatory": true, "source_id": 12 }],
    "fees": [{ "label": "Stamp duty", "amount_lkr": 0, "source_id": 12 }],
    "office": { "name": "DS Galle", "address": "...", "hours": "..." },
    "steps": ["...", "..."],
    "estimated_cost_lkr": 0,
    "verification": "verified | newly_gathered_pending_verification",
    "citations": [{ "title": "...", "url": "...", "last_verified": "2026-06-20" }]
  }
  ```

## Step logic
1. **Confidence gate (do this first):** if the supporting facts are `auto_gathered` and their
   `confidence < τ` (default 0.6), **do not render** — return the graceful fallback instead. A label
   does not stop a bad answer; this gate does. See
   [05 · confidence serving gate](../05-data-model.md#confidence-serving-gate).
2. Assemble structured facts from `retrieved` (no free invention — only what's grounded).
3. Add a cost/time estimate (fees + a transport heuristic via the cost tool).
4. Attach citations + `last_verified`; set `verification` label (esp. for `auto_gathered` knowledge).
5. Emit JSON → render to the Action-Pack UI + printable PDF.

## Decisions & technologies
- **Decision:** **schema-constrained generation** — the LLM fills a validated Pydantic object, not
  free prose.
- **Tech:** Gemini Flash structured output + `@react-pdf/renderer` (or WeasyPrint server-side).

## Alternatives
| Alternative | Why not |
|---|---|
| Free-text answer | Not printable/structured; easy to omit a required document. |
| Template with no LLM | Can't adapt phrasing/sequence to the specific variant. |

## Why optimal
Constrained generation gives a **deterministic, auditable** artifact where every line traces to a
source — trustworthy and directly usable at the counter.

## Guardrails
Only include grounded facts; **enforce the confidence gate** before rendering; in fallback mode,
clearly state what couldn't be verified and give the office to contact. Always show the
`verification` label and citations.

## State touched
Reads `answer_confidence`; writes `answer`, `citations`.
