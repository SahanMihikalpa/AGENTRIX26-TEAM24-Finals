# 07 · 12-Hour Execution Plan

Goal: a working, demoable agentic system by **T+11** (final deliverables) with a frozen repo at
**T+12**. Commit often with meaningful messages (git history is judged).

## Workstream split (2 builders)
- **Builder 1 — Agent/Backend:** LangGraph graph, agents A1–A6 / B1–B4, RAG, tools, FastAPI.
- **Builder 2 — Data/Frontend:** source pool + seed data + SQLite schema, Next.js UI, Action-Pack PDF,
  demo prep.

## Timeline

| Window | Backend (Builder 1) | Data/Frontend (Builder 2) | Commit milestone |
|---|---|---|---|
| **T+0 → T+0:30** | Repo scaffold, env, `LLMProvider` (Gemini), Chroma + SQLite init | Collect source pool (gazettes/circulars/PDF), draft seed schema | `chore: scaffold + providers` |
| **T+0:30 → T+2** | RAG core: embeddings, retriever, **A4 + A5 grader**; FastAPI `/chat` SSE skeleton | Seed Land Transfer + NIC into SQLite + Chroma; Next.js chat shell | `feat: rag retrieval + grader`; **submit interim plan (T+2)** |
| **T+2 → T+4** | **A1/A2** intake+identify, **A3** clarification (slot-filling + interrupt) | Clarifying-question cards UI; wire SSE to UI | `feat: intake + clarification interview` |
| **T+4 → T+6** | **A6** Action-Pack generator (Pydantic → JSON) | Action-Pack view + **print/PDF** | `feat: action pack + pdf` |
| **T+6 → T+8** | **Team 2**: B1 research (local pool → web), B2 curate, B3 KB-updater; gap loop wired with cap N | Business-Reg source files into the pool (un-ingested); office directory | `feat: self-expanding rag loop` |
| **T+8 → T+9:30** | B4 moderation flag + experience-report intake; tools (office lookup, cost estimator) | Moderator view (minimal) + experience-report form | `feat: moderation + feedback loop` |
| **T+9:30 → T+11** | Harden: loop cap, allow-list, error fallbacks; trace/logging | **Record 1–2 min demo video**; finalise report diagrams | `test: guardrails + polish`; **final deliverables (T+11)** |
| **T+11 → T+12** | Final commits, README, freeze | Verify demo runs clean from scratch | `docs: final` → **FREEZE** |

## Definition of done (MVP)
- [ ] Seeded service answers correctly with citations (Scenario A).
- [ ] Unseen service triggers the gap loop and answers live (Scenario B).
- [ ] Action Pack renders + prints to PDF.
- [ ] Experience report submits and appears in the moderation queue (Scenario C).
- [ ] Loop cap + allow-list enforced; graceful fallback on failure.
- [ ] Report has ER, architecture, and use-case diagrams.

## Risk register
| Risk | Mitigation |
|---|---|
| Gemini free-tier rate limits under multi-agent load | Local embeddings; merge A1+A2; cheap grader; bounded loops; cache. |
| Live web slow/blocked at venue | **Hybrid**: local source pool is primary; web is fallback only. |
| Scope creep across many services | Lock to 3 flagship services (2 seeded + 1 live gap-fill). |
| Clarifying interview loops forever | Max question count per session; default to most-common variant if unanswered. |
| Demo flakiness | Seed deterministically; pre-stage gap-fill sources in the pool; dry-run before recording. |

## Out of scope for 12 h (roadmap)
- Sinhala/Tamil + voice input.
- Real appointment booking / payments.
- Full moderator console and auth.
- Postgres + cloud deploy (post-event "polish" repo).
