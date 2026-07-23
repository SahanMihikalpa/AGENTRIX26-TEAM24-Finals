# `application/agents/a2_identify.py` — A2 · Service Identifier

**Layer:** application/agents · **Team 1** · **Stage:** 4 · [doc](../../../agents/a2-service-identifier.md)

## 🎯 කාර්යය
Intent එක → **එක catalog `service_id`** එකකට resolve කිරීම. **LLM එකට service id එකක් හදන්න දෙන්නේ නෑ** —
catalog එකෙන් විතරයි.

## 🔍 Code Walkthrough
`ServiceIdentifierAgent(store, llm=None, *, candidate_limit=5, min_confidence=0.5)` — `__call__`:
1. `store.find_services(query)` → candidates (lexical, keyword-overlap).
2. **candidates නෑ** → `service_unknown=True` (→ gap path → අලුත් service acquire වෙන්නේ මෙහෙමයි).
3. **එකයි** → directly resolve.
4. **කිහිපයයි** → LLM `ServiceDisambiguation` call — **candidates ගේ ids වලින්** එකක් තෝරනවා
   (`_validate_choice` — LLM දුන්න id එක candidate list එකේ තියෙනවද verify). confidence < 0.5 → unknown.
   LLM නැත්නම් lexically-best (first) candidate.

## 🔗 සම්බන්ධතා
- **Uses:** [`KnowledgeStore.find_services`](../../domain/ports/knowledge.md), [`LLMProvider`](../../domain/ports/llm.md).
- **Feeds:** A3 (variant clarify), A5 (`service_unknown` → immediate GAP).

## 💡 Design decision — retrieval-assisted classification
Candidate ids LLM එකට **constrain** කරලා → hallucinated service id එකක් කවදාවත් නෑ. Unknown = gap =
self-expansion trigger (bug එකක් නෙවෙයි, feature එකක්).
