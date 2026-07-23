# `application/graph/serialization.py` — domain ↔ state mappers

**Layer:** application/graph · **Stage:** 4

## 🎯 කාර්යය
Domain dataclasses ↔ JSON-serialisable `GraphState` dicts අතර **boundary mappers**. Blackboard එකේ
primitives විතරයි (checkpointing survive වෙන්න), ඒ නිසා domain value objects මෙතනදී flatten වෙනවා.

## 🔍 Code Walkthrough
- `retrieved_to_state(chunk)` — A4 `RetrievedChunk` → dict (content, score, + provenance: source_id,
  title, url, verification_status, confidence, last_verified).
- `citation_to_state(citation)` — Citation → dict.
- `action_pack_to_state(pack)` — A6 `ActionPack` → `answer` dict (documents, fees, office, steps,
  citations, fallback…).

## 💡 Design decision — money as string
`amount_lkr` / `estimated_cost_lkr` **string** විදියට serialize කරනවා → `Decimal` precision රැකෙනවා (data
layer එකේ TEXT choice එකම). API layer එකෙන් wire එකට JSON number කරනවා (docs/11).

## 🔗 සම්බන්ධතා
Use කරන්නේ [A4](../agents/a4_retrieval.md) (`retrieved_to_state`), [A6](../agents/a6_action_pack.md)
(`action_pack_to_state`).
