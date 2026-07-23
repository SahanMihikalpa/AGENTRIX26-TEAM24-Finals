# `api/routes/moderation.py` — Moderation queue route

**Layer:** api/routes · **Stage:** 6b · FR-7

## 🎯 කාර්යය
Admin moderation endpoints — review queue + promote/reject. `ModerationService` එකට thin translator එකක්.

## 🔍 Code Walkthrough
- `GET /api/moderation/queue` → review එකට තියෙන sources (`ModerationItemDTO` list).
- `POST /api/moderation/{source_id}/promote` → `verified`. unknown id → **404**.
- `POST /api/moderation/{source_id}/reject` → `rejected` + de-index (quarantine). unknown id → 404.
- `_to_item(source)` — Source → DTO map.

## 🔗 සම්බන්ධතා
[`ModerationService`](../../application/moderation.md) use case, [dto](../dto.md). Queue එකට feed වෙන්නේ
[B4](../../application/agents/b4_moderation.md) + `auto_gathered` sources.

## 💡 Design decision
Route = thin translator; promote/reject **policy** use case එකේ (reject → `delete_chunks_for_source`
quarantine). "Serve-but-label" එකේ human side එක මෙතනින්.
