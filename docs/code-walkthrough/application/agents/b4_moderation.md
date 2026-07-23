# `application/agents/b4_moderation.py` — B4 · Moderation Gate

**Layer:** application/agents · **Team 2** · **Stage:** 4b · [doc](../../../agents/b4-moderation.md)

## 🎯 කාර්යය
Auto-gathered knowledge එක **usable ඒත් provisional** විදියට තියාගැනීම. Policy: **serve-but-label, never
block** — අලුත් records retrievable/answerable, ඒත් human review එකකට queue වෙනවා (`verified` කරන්න).

## 🔍 Code Walkthrough
`ModerationGateAgent(*, confidence_threshold=0.6)` — `__call__`:
- Curated records වලින් `verified` නොවන ඒවා `moderation_queue` එකට append (url+title **dedup**, loops අතර).
- Queue entry: `source_title`, `url`, `service_name`, `confidence`, `status="pending"`, **`needs_review`**
  (confidence < τ **හෝ** origin == "web" → moderator මුලින්ම බලන්න ඕන ඒවා).

## 🔗 සම්බන්ධතා
- **Feeds:** [`api/routes/moderation.py`](../../api/routes/moderation.md) (queue surface),
  [`application/moderation.py`](../moderation.md) (promote/reject use case).

## 💡 Design decision — MVP rules-only
මේ node එක **rules-only** (LLM නෑ) — queue එකට append විතරයි. Actual promote/reject transitions Stage 6
moderation API + store status update (`set_source_verification_status`). "Never block" = availability +
self-expansion එක නවතින්නේ නෑ; trust එක *label* එකෙන් (A6) + human review එකෙන් manage කරනවා.
