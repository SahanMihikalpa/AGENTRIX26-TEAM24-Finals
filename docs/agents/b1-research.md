# B1 · Research

**Team:** Knowledge Acquisition · **Type:** Tool-using agent

## Issue it solves
The knowledge base cannot pre-cover the whole government domain. When A5 reports a `GAP`, the system
must **go and find** the missing information autonomously.

## Single responsibility
Given a gap (service/variant/district + the query), gather candidate raw evidence from sources —
**local source pool first, live web as fallback**.

## Inputs → Outputs
- **Input:** the gap context (`service_guess`/`service_id`, `slots`, `normalized_query`).
- **Output:** raw documents (text + source metadata: title, url/path, type, date).

## Step logic
1. Formulate 1–3 focused search queries.
2. **Search the local source pool** (pre-collected gazettes/circulars/PDFs) via vector + filename
   match.
3. If insufficient → **live web** search restricted to the `*.gov.lk` allow-list.
4. Fetch + parse pages/PDFs → clean text + provenance; hand off to B2.

## Decisions & technologies
- **Decision:** **hybrid retrieval source** (local-first, web-fallback) — chosen by the team for
  reliability + realism.
- **Tech:** ChromaDB over the source pool; **Tavily** (free) / **`ddgs`** for web; **PyMuPDF** +
  **trafilatura** for parsing.

## Alternatives
| Alternative | Why not |
|---|---|
| Live web only | Venue internet / site blocking makes the demo fragile; slower. |
| Local pool only | Less impressive; can't handle truly novel queries. |
| Paid search API (SerpAPI) | Violates the free-tier rule. |

## Why optimal
Local-first guarantees a **reliable demo** and low latency; web fallback proves the system handles
genuinely new information — best of both within free-tier rules.

## Guardrails
`*.gov.lk` allow-list; per-call source/time budget; if nothing found, return empty → supervisor
routes to graceful fallback (don't loop forever).

## State touched
Produces raw evidence for B2 (carried in state as `acquisition_buffer`); increments
`acquisition_loops` via the supervisor.
