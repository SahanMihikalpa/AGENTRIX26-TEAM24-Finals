# A4 · Retrieval (RAG)

**Team:** Answering · **Type:** Vector + structured retrieval

## Issue it solves
Given a resolved service + variant + district, fetch the **current, relevant** evidence from the
knowledge base to ground the answer.

## Single responsibility
Retrieve candidate knowledge (chunks + structured records) for the resolved case, with metadata
filtering and source provenance.

## Inputs → Outputs
- **Input:** `service_id`, `variant_id`, `slots.district`, `normalized_query`.
- **Output:** `retrieved` = ranked chunks + linked `REQUIREMENT/FEE/OFFICE` rows + `source_id`s +
  scores.

## Step logic
1. Build a filtered query (metadata filter on `service_id`/`district`).
2. Vector search ChromaDB for top-k chunks; pull the linked structured rows from SQLite.
3. Return candidates with scores and provenance for the grader (A5).

## Decisions & technologies
- **Decision:** **hybrid retrieval** — vector search for relevance + SQL joins for exact structured
  facts (fees, office), filtered by metadata.
- **Tech:** ChromaDB (with `where` filters) + local `bge-base-en-v1.5` embeddings + SQLite joins.

## Alternatives
| Alternative | Why not |
|---|---|
| Vector-only retrieval | Fees/office must be exact, not paraphrased; needs the structured join. |
| Keyword/BM25 only | Misses paraphrase; citizens don't use official wording. |
| Remote embedding API per query | Rate-limited and slower; local embeddings are free and unlimited. |

## Why optimal
Combining semantic recall with exact structured facts yields answers that are both **findable** and
**precise**, and metadata filtering keeps district/variant answers correct.

## Guardrails
Return scores honestly (no score inflation) so A5 can detect genuine gaps; never invent rows.

## State touched
Writes `retrieved`.
