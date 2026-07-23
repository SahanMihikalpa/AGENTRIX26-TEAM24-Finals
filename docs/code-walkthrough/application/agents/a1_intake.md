# `application/agents/a1_intake.py` — A1 · Intake & Intent

**Layer:** application/agents · **Team 1 (Answering)** · **Stage:** 4 · [doc](../../../agents/a1-intake-intent.md)

## 🎯 කාර්යය
Messy free-text request එකක් → **structured intent** එකක්. Graph එකේ **පළමු node** එක.

## 🔍 Code Walkthrough
`IntakeIntentAgent(llm)` — `__call__(state)`:
1. එක **structured LLM call** එකක් (`IntentExtraction` schema) — query එක normalize කරලා,
   coarse `service_guess` (snake_case) දීලා, user කිව්ව entities විතරක් pull කරනවා (`ambiguous` flag).
2. **Slot seeding:** entities වල district/relationship තිබුණොත් `slots` එකට දානවා → A3 ට ඒවා ආයෙ අහන්න වෙන්නේ නෑ.

Return: `{"intent": ..., "slots": ...}` (partial state update).

## 🔗 සම්බන්ධතා
- **Uses:** [`LLMProvider`](../../domain/ports/llm.md), [`IntentExtraction`](schemas.md).
- **Feeds:** A2 (service_guess/normalized_query), A3 (seeded slots).

## 💡 Design decision
"Never invent facts" — system prompt එකෙන් hallucination අඩු කරනවා. A1+A2 එකට merge කරන්නත් පුළුවන් (LLM
calls අඩු කරන්න, docs/04) ඒත් මෙතන separate — traceability එකට.
