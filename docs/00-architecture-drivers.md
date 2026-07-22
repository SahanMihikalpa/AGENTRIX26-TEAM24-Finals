# 00 · Architecture Drivers (Quality Attributes)

> **Read this first.** Architecture is the set of decisions that are hard to change later, and
> *every* such decision in the following docs earns its place by serving one of the quality
> attributes below — never "because it's cool" and never *only* "because of the 12-hour limit".
> The 12 h / free-tier / no-code / must-be-agentic items are **project constraints** (a fixed
> budget we design *within*); the table below is the set of **drivers** we design *toward*.

## Functional requirements (what it must do)
Traceable to use cases in [06-use-cases.md](06-use-cases.md):
1. Accept a free-text service request and identify the correct government service.
2. Run a minimal clarifying interview to pin the exact variant + district.
3. Retrieve current requirements, fees, office, and timeline — grounded and cited.
4. Detect a knowledge gap and acquire the missing knowledge autonomously.
5. Produce a personalised, printable Action Pack.
6. Accept experience reports and let a moderator promote knowledge to `verified`.

## Quality attributes — the real drivers
Each is written as a concrete scenario, not a vague wish. The right-hand column is a forward
reference to the mechanism that satisfies it.

| # | Quality attribute | Scenario | How the architecture responds |
|---|---|---|---|
| QA-1 | **Trustworthiness / correctness** *(dominant)* | A confidently wrong answer about a government process sends a citizen on a wasted, paid trip. | Grounded RAG; every fact carries `source_id` + `last_verified`; Corrective-RAG grader (A5); **confidence-gated serving** (A6); `auto_gathered` knowledge labelled and moderated (B4). |
| QA-2 | **Responsiveness** | On the happy path the citizen gets an answer in a few seconds; even during a live gap-fill they see continuous progress, never a silent hang. | Local embeddings (no API round-trip); cheap two-stage grader; **SSE streaming of agent-step progress**; local-source-pool-first research. |
| QA-3 | **Cost-efficiency / free-tier survivability** | Under multi-agent load the system stays within Gemini free-tier limits (~15 RPM) for an entire demo. | Bounded acquisition loops (`N ≤ 2`); merged `A1+A2` call; embeddings computed locally; **central rate-limited LLM gateway**; query→answer cache. |
| QA-4 | **Modifiability** | Swap the LLM (Gemini→Groq), vector store (Chroma→pgvector), or web search (Tavily→DDG) without touching agent logic. | **Ports & adapters** (hexagonal layout); Strategy + Adapter patterns. |
| QA-5 | **Extensibility of knowledge** | The KB cannot cover the whole government domain at start; it must grow where real users actually need it. | Self-expanding RAG — lazy / on-demand ingestion ([03](03-self-expanding-rag.md)). |
| QA-6 | **Availability / graceful degradation** | Venue internet is blocked, or a gap simply can't be filled — the system still returns something useful. | Local source pool primary, web fallback; loop-cap → graceful fallback ("contact this office directly"). |
| QA-7 | **Security & privacy** | A government-facing tool must not ingest junk pages or hold unnecessary citizen data. | `*.gov.lk` source allow-list; moderation gate (B4); minimal PII; Pydantic-validated structured outputs. |
| QA-8 | **Traceability / observability** *(for the defense)* | Every decision the system makes must be inspectable after the fact. | Single typed `GraphState` + `SqliteSaver` checkpointer; LangSmith traces; per-session correlation id. |

## Priority ranking (when two drivers conflict)
**QA-1 Trustworthiness > QA-6 Availability > QA-2 Responsiveness > QA-3 Cost > QA-4/5 evolvability.**
Concretely: we would rather *refuse to answer* (QA-1) than answer fast (QA-2) or answer at all
(QA-6) — which is exactly why `auto_gathered` facts below the confidence threshold trigger the
fallback instead of being rendered into an Action Pack.

## Dominant driver per container
This is what justifies the per-container style choices in [02-architecture.md](02-architecture.md#c4-level-2--containers).

| Container | Dominant driver | Resulting style |
|---|---|---|
| Next.js UI | Responsiveness (QA-2) | Layered SPA + SSE |
| FastAPI backend | Security (QA-7), Responsiveness (QA-2) | Layered + Façade over the agent runtime |
| Agent Runtime (LangGraph) | Correctness (QA-1), Traceability (QA-8) | Orchestration (Supervisor) over a **Blackboard** state |
| Knowledge Acquisition pipeline | Extensibility (QA-5) | **Pipe-and-Filter** (B1→B2→B3) |
| Knowledge Base (Chroma + SQLite) | Correctness (QA-1), Cost (QA-3) | **Data-Centred / Repository** |
| Source Pool | Availability (QA-6) | Data-Centred |
