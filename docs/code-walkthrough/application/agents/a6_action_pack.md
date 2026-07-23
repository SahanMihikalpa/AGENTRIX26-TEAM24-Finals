# `application/agents/a6_action_pack.py` — A6 · Action-Pack Generator

**Layer:** application/agents · **Team 1** · **Stage:** 4 · [doc](../../../agents/a6-action-pack-generator.md) · **ADR:** AD-8

## 🎯 කාර්යය
පුරවැසියාට යන අවසාන, **grounded + cited + printable** උත්තරය (Action Pack) හැදීම — නැත්නම් confidence gate
එකෙන් block වුණොත් graceful **fallback** එක.

## 🔍 Code Walkthrough
`ActionPackAgent(store, llm=None, *, confidence_threshold=0.6)` — `__call__`:

**1. Confidence gate මුලින්ම (`_gate`, AD-8):** *label* එකක් *bad answer* එකක් නවත්තන්නේ නෑ, ඒ නිසා:
- `grade != SUFFICIENT` → fallback.
- retrieved එකේ `auto_gathered` (unverified) facts තියෙනවා **සහ** `answer_confidence < τ (0.6)` → fallback.
- එහෙම නැත්නම් → pack එක render කරනවා.

**2. Deterministic fact assembly (`_build_pack`):** hard facts (documents, fees, office) **store එකෙන්
කෙළින්ම** කියවනවා (resolved variant/district එකට) → හැම line එකක්ම real row එකකට trace වෙනවා, **LLM
invention නෑ**. `estimated_cost_lkr` = fees sum. LLM (optional) එක **steps** narrative එක විතරයි sequence
කරනවා (`_default_steps` = deterministic fallback).

**3. Fallback pack (`_fallback_pack`):** documents/fees හිස්, "office එකට contact කරන්න" step එකක්,
`fallback=True`. **වැදගත්:** service unknown නම් citations **හිස්** — A4 ගේ closest chunks වෙන services වලට
අයිති නිසා ඒවා cite කළොත් citizen misled වෙනවා.

**4. Provenance:** `_verification` (හැම chunk එකම verified නම් `VERIFIED`, නැත්නම්
`NEWLY_GATHERED_PENDING_VERIFICATION`), `_citations` (source-id dedup).

## 💡 Design decision (delta from docs)
Doc එක LLM එකෙන් මුළු ActionPack එකම fill කරනවා කිව්වා; මෙතන **facts deterministic + LLM steps විතරයි**
→ stronger groundedness guarantee. Gate එක **first** — deliberate (AD-8).
