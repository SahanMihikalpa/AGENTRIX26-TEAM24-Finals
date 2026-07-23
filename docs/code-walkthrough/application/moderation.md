# `application/moderation.py` — Moderation use case

**Layer:** application (use case) · **Stage:** 6b · [doc](../../agents/b4-moderation.md)

## 🎯 කාර්යය
B4 "serve-but-label" policy එකේ **human side** එක. Auto-gathered knowledge එක immediately serve වෙනවා
("pending verification" label එකෙන්), මෙතන human review එකකට queue වෙනවා.

## 🔍 Code Walkthrough
`ModerationService(store)`:
- `queue(*, limit=50)` — review එකට තියෙන sources (`auto_gathered`/`pending`).
- `promote(source_id)` → `verified` (A6 "pending" label එක හැමෝටම drop). unknown id → `False`.
- `reject(source_id)` → `rejected` **+ de-index**: `delete_chunks_for_source` (chunks + vectors අයින් →
  retrieve/serve වෙන්නේ නෑ), ඒත් `source` row එක තියාගන්නවා → dedup එකෙන් re-ingestion block.

## 🔗 සම්බන්ධතා
- **Uses:** [`KnowledgeStore`](../domain/ports/knowledge.md) moderation methods.
- **Called by:** [`api/routes/moderation.py`](../api/routes/moderation.md).

## 💡 Design decision
Promote/reject **policy** මෙතන (use case) → API route එක thin translator එකක් විතරයි. Reject = quarantine
(delete නෙවෙයි) — dedup එකට source row එක ඕන. Depends only on `KnowledgeStore` port.
