# `application/agents/b3_kb_updater.py` — B3 · KB-Updater

**Layer:** application/agents · **Team 2** · **Stage:** 4b · [doc](../../../agents/b3-kb-updater.md) · **ADR:** AD-2, AD-4

## 🎯 කාර්යය
Curated records **KB එකට persist කිරීම** — self-expanding වෙන්නේ මෙතනින්. පළමු user ගේ research එක
ඊළඟ හැමෝටම cache වෙනවා (data moat එක).

## 🔍 Code Walkthrough
`KBUpdaterAgent(store, embedder, *, max_chunk_chars=500)` — `__call__` → හැම curated record එකකටම
`_write_record`:
1. **Dedup** — `source_exists(url, content_hash)` (SHA-256 of text). දැනටමත් තියෙනවා නම් skip → gap loop
   re-run **idempotent**.
2. **SOURCE** upsert (`auto_gathered`) + structured rows: `_resolve_service` / `_resolve_variant`
   (**reuse-or-create** — slug/label match වුණොත් reuse, verified data overwrite කරන්නේ නෑ), requirements,
   fees, offices (+ link), district variation — හැම එකකටම `source_id` attach.
3. **Chunks** — text chunk කරලා, **local embed** (AD-4, A4 එකේ එකම model), `service_id` metadata එක්ක
   Chroma upsert → ඊළඟ loop එකේ A4 ට retrieve කරන්න පුළුවන්.
- **Loop convergence:** `kb_updated=True`. `service_unknown` gap එකක් නම්, අලුත් `service_id` එක state
  එකට දෙනවා → A4 `service_unknown` එකේ loop වෙනවා නෙවෙයි, real service එකකින් re-retrieve.

## 🔗 සම්බන්ධතා
- **Uses:** [`KnowledgeStore`](../../domain/ports/knowledge.md) (writes), [`EmbeddingProvider`](../../domain/ports/embeddings.md).
- **Feeds back:** supervisor → A4 (re-retrieval); cache invalidation (AD-12).

## 💡 Design decision
**Reuse-or-create + dedup** = idempotent, safe re-runs; `auto_gathered` කවදාවත් `verified` overwrite
කරන්නේ නෑ. මේකයි "KB grows only where real users hit gaps" (AD-2).
