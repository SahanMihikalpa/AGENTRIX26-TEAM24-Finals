# `application/agents/a5_grader.py` — A5 · Gap Grader

**Layer:** application/agents · **Team 1** · **Stage:** 4 · [doc](../../../agents/a5-gap-grader.md)

## 🎯 කාර්යය
Retrieve කරපු evidence එක **answer කරන්න ඇතිද?** කියලා තීරණය කිරීම — `SUFFICIENT` හෝ `GAP`. මේක තමයි
**Corrective-RAG switch** එක (self-expanding loop එක drive කරන්නේ මේකෙන්).

## 🔍 Code Walkthrough
`GapGraderAgent(llm=None, *, sufficient_above=0.5, gap_below=0.3)` — `__call__`:
- `service_unknown` හෝ empty retrieval → **immediate GAP**.
- `top_score` (best chunk score) බලනවා:
  - **≥ 0.5** → SUFFICIENT.
  - **< 0.3** → GAP.
  - **0.3–0.5 (borderline band)** → **cheap LLM yes/no** (`GradeDecision`) — LLM නැත්නම් GAP bias
    (answer wrong වෙනවට වඩා research කරන එක හොඳයි).
- **`answer_confidence`** — supporting chunks වල **min source confidence** එක (A6 serving gate එකේ input).

## 🔗 සම්බන්ධතා
- **Uses:** [`LLMProvider`](../../domain/ports/llm.md) (borderline විතරයි), `GradeDecision` schema.
- **Feeds:** supervisor (SUFFICIENT→A6, GAP→B1), A6 (`answer_confidence` gate).

## 💡 Design decision — Two-stage grading (cost)
බහුතරය cheap threshold එකෙන් handle කරලා, **borderline band එකට විතරයි** LLM call එකක් වියදම් කරනවා →
free-tier quota save. "When unsure, prefer GAP" — under-answer කරන එක mislead කරනවට වඩා හොඳයි (QA-1).
