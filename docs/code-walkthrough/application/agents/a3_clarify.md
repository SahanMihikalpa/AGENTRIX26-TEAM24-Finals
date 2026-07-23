# `application/agents/a3_clarify.py` — A3 · Clarification (slot-filling interview)

**Layer:** application/agents · **Team 1** · **Stage:** 4 · [doc](../../../agents/a3-clarification.md)

## 🎯 කාර්යය
`service_id` → **එක `variant_id`** එකකට narrow කිරීම (+ district context), **අවම ප්‍රශ්න** ගණනකින්, එකින් එක.
රජයේ process branch වෙනවා (inheritance/sale/gift) නිසා generic answer එකක් individual එකාට වැරදියි.

## 🔍 Code Walkthrough
`ClarificationAgent(store, llm=None, *, max_questions=4)` — `__call__` variant + district resolve කරනවා:
- **`_resolve_variant`** — variant එකක් pin කරන්න try කරනවා, order එකකින්:
  1. state එකේ variant_id තියෙනවා නම් done.
  2. variants එකයි නම් auto-pick.
  3. `slots` එකේ condition/relationship answer එකක් තියෙනවා නම් `_match_variant` (label match).
  4. **user ගේ වචන වලම** variant එක තිබුණොත් `_match_variant_in_text` (token match — "...NIC for the
     first time..." → first-time variant, ආයෙ අහන්නේ නෑ).
  5. තවම ambiguous → **ප්‍රශ්නයක් අහනවා** (condition options = variant labels); දැනටමත් ඇහුවා නම් first
     variant default කරලා A6 assumption එක කියනවා.
- **`_maybe_ask_district`** — district නැත්නම් අහනවා (free-text).
- **Framework-free:** `pending_question` payload එකක් ලියනවා (`{slot, question, options, allow_free_text}`);
  actual LangGraph `interrupt()`/`Command(resume)` එක **supervisor ගේ වැඩක්** (Stage 5). Re-entry එකේදී
  A3 `slots` ආයෙ කියවනවා → naturally resumable.

## 💡 Design decisions
- **Minimal questions** — guardrails (`asked_slots`, `max_questions`) නිසා loop වෙන්නේ නෑ; අනිවාර්ය නැති නම්
  default කරලා යනවා.
- Options **catalog-grounded** — LLM (optional) එක question **text** එක විතරයි rephrase කරන්නේ (options හදන්නේ නෑ).
- LLM නැත්නම් template — deterministic + quota-free.
