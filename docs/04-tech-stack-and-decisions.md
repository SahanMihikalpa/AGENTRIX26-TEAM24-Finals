# 04 · Tech Stack & Decisions

Every row: **decision (technology) · alternatives · why optimal** under our four hard constraints
— *12 hours · free-tier only in the product · no no-code/low-code · must be agentic/RAG*.

| Layer | Decision (technology) | Alternatives | Why optimal |
|---|---|---|---|
| Agent framework | **LangGraph** | LangChain `AgentExecutor`, CrewAI, AutoGen | Explicit state graph + bounded loops + checkpointing + human-in-the-loop fit the gap loop exactly; traceable for the defense. |
| Orchestration pattern | **Hierarchical supervisor + 2 teams** | Single agent, sequential chain, swarm | See [02-architecture.md](02-architecture.md). |
| RAG strategy | **Corrective RAG + self-expanding KB** | Static KB, web-every-time, GraphRAG, fine-tune | See [03-self-expanding-rag.md](03-self-expanding-rag.md). |
| LLM | **Gemini 2.x Flash (free tier)** via `langchain-google-genai` | Groq-Llama (free), Mistral (free), local Ollama | Generous free tier, native tool/function calling, long context, fast; wrapped behind an `LLMProvider` interface so it can be swapped. |
| Embeddings | **Local `bge-base-en-v1.5`** (sentence-transformers) | Gemini `text-embedding-004` (free API), `all-MiniLM-L6-v2`, OpenAI (paid ❌) | Local = **no rate limits**, offline, free, strong English retrieval; avoids spending the Gemini quota on embeddings so it is reserved for reasoning. |
| Vector store | **ChromaDB** (local, persistent) | FAISS, Qdrant, pgvector (Supabase) | Zero-config, metadata filtering (service/district), 12-hour-friendly; persists to disk for the demo. |
| Structured DB | **SQLite** | Postgres, Supabase | Single file, zero setup → clean **ER diagram**; trivially migratable to Postgres later. |
| Web research tool | **Tavily free tier**, fallback **`ddgs` (DuckDuckGo)** | SerpAPI (paid ❌), raw scraping | Free, agent-oriented results; `*.gov.lk` allow-list. (`ddgs` needs no key.) |
| PDF/HTML parsing | **PyMuPDF** (`fitz`) + **trafilatura** | `pdfplumber`, `unstructured` | Robust, fast text extraction from gazette/circular PDFs and portal pages. |
| Backend | **FastAPI** (async) + **SSE** streaming | Flask, Django, Node/Express | Async suits multi-agent + streaming; Pydantic gives validated structured outputs; first-class LangGraph integration. |
| Structured outputs | **Pydantic v2** models | Raw JSON parsing | Schema-validated agent outputs (checklist, curated records) → reliable, testable. |
| State / memory | **LangGraph `SqliteSaver` checkpointer** | In-memory `MemorySaver`, Redis | Resumable interview state per session, zero infra. |
| LLM throttling | **Central LLM gateway** (token-bucket + retry/backoff) | Per-agent ad-hoc calls | One choke point keeps the whole multi-agent system under the Gemini free-tier ceiling (AD-10). |
| Caching | **Query→answer cache** (SQLite table) | No cache | Identical `service+variant+district` queries (and demo re-runs) skip the graph; saves quota (AD-12). |
| Frontend | **Next.js (App Router) + Tailwind** | Streamlit, plain React, Vite | Polished, professional UI for the pitch/demo video; SSE-friendly. |
| PDF generation (Action Pack) | **`@react-pdf/renderer`** or server-side **WeasyPrint** | Browser print-to-PDF | Clean, printable checklist the citizen can carry. |
| Observability | **LangSmith (free)** or structured logging | None | Trace every agent step — strengthens the technical defense. |

## Free-tier compliance checklist
- ✅ LLM: Gemini **free tier** only (no paid keys in the product).
- ✅ Embeddings: **local**, $0.
- ✅ Vector DB + relational DB: **local**, $0.
- ✅ Web search: Tavily free tier / `ddgs` (free).
- ✅ No n8n / no-code — everything is hand-written Python + TypeScript.

## AI-workflow efficiency notes (Code Review — 30%)
- **Minimise LLM calls per turn:** merge `A1`+`A2` into one structured call; the grader `A5` is a
  single cheap call (or an embedding-similarity threshold + a short verify call).
- **Cache aggressively:** the self-expanding KB means a researched answer is computed once and reused;
  a query→answer cache short-circuits identical queries entirely.
- **Reserve the Gemini quota for reasoning** by keeping embeddings local.
- **Embedding invariant:** the **same** `bge-base-en-v1.5` model must be used at write (B3) and read
  (A4) — mixing models silently degrades retrieval.
- **Bounded loops** (`N ≤ 2`) keep worst-case calls predictable.

## Repository layout (hexagonal)

Rationale in [09 · AD-9](09-architecture-decisions.md). **The dependency rule:** dependencies point
inward — `domain` imports nothing, `application` imports only `domain.ports`, `adapters` implement
those ports, `api` wires the concrete adapters in at startup. Swapping Gemini→Groq or Chroma→pgvector
touches only `adapters/`. That is modifiability (QA-4) proven by structure.

```
sevana/
├── backend/
│   └── app/
│       ├── domain/                  # PURE — no framework imports
│       │   ├── entities.py          #   Service, Variant, Requirement, Source, Checklist
│       │   └── ports/               #   the interfaces (the C4-L3 sockets)
│       │       ├── llm.py           #     LLMProvider
│       │       ├── embeddings.py    #     EmbeddingProvider
│       │       ├── knowledge.py     #     KnowledgeStore / Retriever
│       │       ├── web_search.py    #     WebSearch
│       │       └── parser.py        #     SourceParser
│       │
│       ├── application/             # USE CASES — depends only on domain.ports
│       │   ├── graph/               #   LangGraph: state.py, supervisor.py, edges.py
│       │   └── agents/              #   A1..A6, B1..B4 (call ports, never concrete tech)
│       │
│       ├── adapters/                # IMPLEMENTATIONS of ports (swappable)
│       │   ├── llm/gemini.py        #   Strategy/Adapter → LLMProvider
│       │   ├── llm/groq.py          #   (fallback, same interface)
│       │   ├── embeddings/bge.py
│       │   ├── knowledge/chroma_sqlite.py    # Repository
│       │   ├── web_search/tavily.py · ddg.py
│       │   └── parser/pymupdf.py
│       │
│       ├── infrastructure/          # cross-cutting: llm_gateway (rate limit), cache, logging, config
│       │
│       └── api/                     # DELIVERY: FastAPI routers, SSE, Pydantic DTOs, DI wiring
│   └── data/source_pool/            # pre-collected gazettes/circulars/PDF
├── frontend/                        # Next.js + Tailwind
└── docs/                            # this folder
```

### As-built notes
The code follows this layout. Tooling made concrete + small additions during implementation
(full log in [10-backend-implementation.md](10-backend-implementation.md)):
- **Environment:** **conda** (env `govguide`, Python 3.11); Python deps + `ruff`/`mypy`/`pytest`
  config live in `backend/pyproject.toml`; `backend/environment.yml` pins the env.
- **Additions to the tree:** `backend/tests/` (mirrors `app/`), `backend/pyproject.toml`,
  `backend/environment.yml`, `backend/requirements.txt`, `backend/.env.example`, `backend/README.md`.
- **Single config source:** `app/infrastructure/config.py` holds every tunable (τ confidence gate,
  acquisition loop cap, `gov.lk` allow-list, LLM rate limit), so agents/adapters wire to settings,
  not literals.
- **Dependency manifests:** `pyproject.toml` (declarative ranges, source of truth) +
  `requirements.txt` (pinned, pip-installable). **LangGraph/LangChain are now 1.x** — pinned
  `langgraph` 1.2.6, `langgraph-checkpoint-sqlite` 3.1.0, `langchain-core` 1.4.8,
  `langchain-google-genai` 4.2.5, `langchain-groq` 1.1.3 (verified to co-resolve + import). Deps
  still grow per stage.
- **Cache (as-built, Stage 3 → wired Stage 7b):** the query→answer cache (AD-12, the "SQLite table"
  row above) is an **in-memory LRU** — `InMemoryAnswerCache` in `app/infrastructure/cache.py`,
  implementing the `AnswerCache` port in `app/domain/ports/cache.py`. It is **consulted mid-graph**
  (a `service+variant+district` hit short-circuits A4–A6, and a repeat of a gap-filled service skips
  the whole acquisition loop) and **invalidated per service** on B3 upsert and on moderation
  promote/reject. It stores the serialised answer dict (not the `ActionPack`) — functionally
  identical for AD-12. It fully serves AD-12's intra-process re-run / quota savings; cross-restart
  SQLite persistence remains deferred. Full rationale + delta in
  [10-backend-implementation.md](10-backend-implementation.md).
