# A5 · Gap Grader

**Team:** Answering · **Type:** LLM (cheap call) / threshold — the **Corrective-RAG** trigger

## Issue it solves
Retrieval can return weak or off-topic context. Answering from insufficient evidence produces a
confidently wrong reply — the worst outcome for a government process. Something must decide whether
the retrieved evidence is **good enough to answer**.

## Single responsibility
Grade `retrieved` against the user's resolved need → emit `SUFFICIENT` or `GAP`. This is the switch
that drives the [self-expanding RAG loop](../03-self-expanding-rag.md).

## Inputs → Outputs
- **Input:** `normalized_query`, `variant_id`, `retrieved` (+ scores).
- **Output:** `grade ∈ {SUFFICIENT, GAP}` (+ short reason) and `answer_confidence` (0–1) — the min
  confidence of the supporting facts, which A6 uses for the
  [confidence serving gate](../05-data-model.md#confidence-serving-gate).

## Step logic
1. Quick check: are the required fields (documents, fees, office) actually covered by `retrieved`?
2. If score/coverage below threshold → `GAP`.
3. Else a short LLM verification ("does this context answer the question?") → final grade.

## Decisions & technologies
- **Decision:** **two-stage grading** — cheap similarity/coverage threshold first, a short LLM check
  only when borderline.
- **Tech:** score threshold on retrieval + a minimal Gemini Flash yes/no call.

## Alternatives
| Alternative | Why not |
|---|---|
| Always answer (no grader) | No corrective loop; hallucinations slip through. |
| Full Self-RAG critique every time | More LLM calls than the free tier comfortably allows. |
| Threshold only (no LLM) | Misses semantically-relevant-but-low-score or off-topic-but-high-score cases. |

## Why optimal
The threshold handles the easy majority cheaply; the LLM is spent only on borderline cases — accurate
gap detection at minimal free-tier cost. This is the heart of correctness *and* the innovation.

## Guardrails
Bias slightly toward `GAP` when unsure (better to research than to answer wrong); feeds the bounded
loop, so extra caution can't run away.

## State touched
Writes `grade`, `answer_confidence`.
