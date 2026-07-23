# `application/feedback.py` — Experience-report intake (use case)

**Layer:** application (use case) · **Stage:** 6b · [docs/03](../../03-self-expanding-rag.md)

## 🎯 කාර්යය
පුරවැසි post-visit report එකක් ("ඒගොල්ලෝ X එකකුත් ඉල්ලුවා") — **B2→B3 pipeline එකට දෙවන entrypoint**
එක. web research විතරක් නෙවෙයි, real-world citizen signal එකකුත් KB එක වර්ධනය කරනවා.

## 🔍 Code Walkthrough
`ExperienceReportIntake(store, llm, embedder)` — `submit(report)`:
1. Report එක **හැමවිටම persist** (`add_experience_report`, `status=pending`).
2. **Best-effort ingest** (`_ingest`) — report එක B1-style buffer entry (`origin="experience"`) කරලා
   → B2 curate → curated තිබුණොත් B3 KB update.
3. Ingest fail වුණත් (flaky LLM/embed) report **save වෙලා call success** — `try/except` එකෙන් catch.

## 🔗 සම්බන්ධතා
- **Reuses:** [B2](agents/b2_curate.md), [B3](agents/b3_kb_updater.md) agents (same pipeline).
- **Called by:** [`api/routes/feedback.py`](../api/routes/feedback.md).

## 💡 Design decision
"Report **always saved**, ingest best-effort" — citizen ගේ report එකක් flaky LLM එකක් නිසා නැති වෙන්නේ නෑ.
B3 ලියන ඕනම දෙයක් `auto_gathered` → moderation queue (provisional, human promote කරනකම්). Framework-free
(stdlib logging විතරයි).
