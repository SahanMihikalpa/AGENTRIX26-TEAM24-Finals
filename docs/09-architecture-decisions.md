# 09 · Architecture Decision Record (ADR Log)

> The decisions that are **hard to reverse** — each with its **trade-off stated**, because every
> architectural choice costs something. "Why optimal" lives in the detailed docs; this log exists so
> the technical defense can show we knew the price of each choice and accepted it on purpose.
> Drivers referenced as `QA-n` are defined in [00-architecture-drivers.md](00-architecture-drivers.md).

| ID | Decision | Driver(s) | Rationale | Trade-off accepted |
|---|---|---|---|---|
| **AD-1** | **Hierarchical supervisor + 2 teams** (not single ReAct agent, not swarm) | QA-1, QA-8 | The gap→research→retry loop and branching interview stay correct, bounded, and traceable. | More nodes to build and wire than one agent; supervisor is a central control point. |
| **AD-2** | **Self-expanding RAG** (Corrective-RAG + lazy ingestion) | QA-5, QA-1 | KB grows only where real users hit gaps; the first user's research is cached for everyone after — a genuine data moat. | First-hit latency for an uncached service; `auto_gathered` facts need confidence-gating (AD-8) + moderation. |
| **AD-3** | **Blackboard `GraphState` + `SqliteSaver` checkpointer** | QA-8, QA-2 | One inspectable, resumable state object → trivial debugging, resumable interview, zero infra. | Shared mutable state can bloat; heavy artifacts (retrieved chunks) must be kept lean / out of the persisted state. |
| **AD-4** | **Local `bge-base-en-v1.5` embeddings** (not an embedding API) | QA-3, QA-2 | No rate limits, offline, free; reserves the Gemini quota for reasoning. | ~400 MB model + cold-start latency (preload at boot); English-only quality; **must use the same model at write and read**. |
| **AD-5** | **SQLite + ChromaDB** (not Postgres + pgvector) | QA-3 | Single-file, zero-config, persists to disk; fastest to stand up in 12 h; clean ER diagram. | Single-writer concurrency limits under heavy parallel writes; migrate to Postgres post-event. |
| **AD-6** | **Gemini 2.x Flash (free tier) behind an `LLMProvider` port** | QA-3, QA-4 | Generous free tier, native tool-calling, long context; swappable via the port. | Free-tier rate limits + provider-lock risk; mitigated by the Strategy/Adapter port and AD-10. |
| **AD-7** | **Local-source-pool-first, live web as fallback** | QA-6, QA-2 | Guarantees a reliable, low-latency demo; web proves true novelty handling. | The pool must be pre-curated; pool content can go stale; allow-listing limits reach. |
| **AD-8** | **Confidence-gated serving of `auto_gathered` knowledge** | QA-1 | A *label* doesn't stop a *bad* answer; below-threshold facts must not be rendered into an Action Pack. | May refuse a genuinely-correct but low-confidence find (false negative) — accepted: under-answering beats misleading. |
| **AD-9** | **Hexagonal (ports & adapters) project layout** | QA-4, QA-8 | Domain core depends on nothing; adapters are swappable; patterns become structural, not claimed. | More indirection/boilerplate than a flat layout — justified by modifiability + testability. |
| **AD-10** | **Central rate-limited LLM gateway** (one throttle for all agents) | QA-3 | Token-bucket + retry/backoff keeps the whole multi-agent system under the free-tier ceiling. | A shared throughput bottleneck / single point in front of the LLM — acceptable given the ceiling is the real limit. |
| **AD-11** | **Synchronous orchestration** (not an event-driven bus) | QA-8 | Single-node app; a traceable state graph is simpler to build and defend in 12 h. | No async fan-out / independent scaling — acceptable at this scale; revisit if multi-tenant. |
| **AD-12** | **Query→answer cache** keyed by `service+variant+district` | QA-3, QA-2 | Identical queries (and demo re-runs) skip the whole graph. | Risk of serving a stale answer after the KB updates — mitigated by cache invalidation on KB upsert for that key. |

## How to extend this log
New hard-to-reverse decision → add a row with **Decision · Driver(s) · Rationale · Trade-off**.
If a decision has *no* trade-off, it probably isn't an architectural decision — it's an
implementation detail and belongs in the relevant agent/tech doc instead.
