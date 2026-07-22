# 10 · Backend Implementation Log (as-built)

> A running, stage-by-stage record of **what the backend code actually does**, kept in lock-step with
> the build. Where reality diverges from the planning docs ([02](02-architecture.md),
> [04](04-tech-stack-and-decisions.md), [05](05-data-model.md), [07](07-execution-plan.md),
> [agents/](agents/README.md)), the delta is called out here so the design docs and the code never
> silently disagree. Updated after **every** stage.

## Build approach
- **Order:** inside-out per the hexagonal dependency rule (`domain` → `application` → `adapters`/`api`),
  with a runnable `/health` skeleton from Stage 0 so the app always boots.
- **Cadence:** one stage at a time; each stage ends green (`pytest` + `ruff` + `mypy`) and with this
  log updated, then pauses for review.
- **Dependencies grow per stage:** only the libraries a stage needs are added to
  `backend/pyproject.toml`, so each stage's environment stays minimal and verifiable. Refresh the env
  after pulling a stage with `pip install -e .[dev]`.

## Locked decisions (from planning Q&A)
| Topic | Decision | Note / delta vs docs |
|---|---|---|
| Environment manager | **conda** (env `govguide`, Python 3.11) | Docs 04 named the stack but not a package manager; conda chosen for robust native deps (torch/sentence-transformers) on Windows. |
| Domain modeling | **Pure dataclasses + enums**; Pydantic only in `api/` DTOs and agent structured-outputs | Reinforces docs 04 "PURE — no framework imports". |
| Seed/KB data | **Provided later** by the team | Stage 2 builds the loader + pipeline; only tiny synthetic fixtures are used for automated tests. |

## Progress
| Stage | Title | Status | Verified by |
|---|---|---|---|
| 0 | Scaffold & tooling | ✅ Done | `pytest`+`ruff`+`mypy` green; app imports with `/health` |
| 1 | Domain core (pure) | ✅ Done | `pytest` 9 passed; `mypy` 23 files; purity guard green |
| 2 | Data layer (SQLite + Chroma + bge) | ✅ Done | `pytest` 17 passed (incl. real bge 768-d); `ruff`/`mypy` clean |
| 3 | External adapters + infra (LLM providers, gateway, cache, web, parser) | ✅ Done | `pytest` 41 passed + 4 skipped (live); `ruff`/`mypy` clean (35 files) |
| 4a | GraphState + Team 1 agents (A1–A6) | ✅ Done | `pytest` 49 passed; `ruff`/`mypy` clean (35 files) |
| 4b | Team 2 agents (B1–B4) | ✅ Done | `pytest` 64 passed; `ruff`/`mypy` clean (40 files) |
| 5 | LangGraph wiring | ✅ Done | `pytest` 71 passed (incl. real graph runs); `ruff`/`mypy` clean (42 files) |
| 6a | API delivery — chat SSE + composition root | ✅ Done | `pytest` 103 passed + 4 skipped (live); `ruff`/`mypy` clean (58 files) |
| 6b | API delivery — feedback + moderation | ✅ Done | `pytest` 118 passed + 4 skipped (live); `ruff`/`mypy` clean (63 files) |
| 7a | Hardening — observability (correlation id, logs, tracing) | ✅ Done | `pytest` 125 passed + 4 skipped (live); `ruff`/`mypy` clean (64 files) |
| 7b | Hardening — AnswerCache short-circuit + invalidation | ✅ Done | `pytest` 132 passed + 4 skipped (live); `ruff`/`mypy` clean (65 files) |

---

## Stage 0 — Scaffold & tooling ✅

**Goal:** a clean hexagonal skeleton that boots and enforces quality gates.

### Implemented
- Full `backend/` package tree matching the proposed layout in
  [04 · repository layout](04-tech-stack-and-decisions.md#repository-layout-hexagonal): `app/{domain,
  domain/ports, application/graph, application/agents, adapters/{llm,embeddings,knowledge,web_search,
  parser}, infrastructure, api}` plus `data/source_pool/`. All are importable packages (empty
  `__init__.py`); concrete modules are filled in their own stages.
- `app/infrastructure/config.py` — a single Pydantic-Settings `Settings` object (the only reader of the
  environment). Centralises every tunable the design calls for: data-store paths, LLM/Groq/Tavily keys
  + model names, **embedding model** `BAAI/bge-base-en-v1.5`, **confidence gate** τ=0.6 (AD-8),
  **loop cap** N=2 (AD-2), **web allow-list** `gov.lk` (QA-7), **LLM rate limit** 15 rpm (AD-10),
  optional LangSmith. Comma-separated env values (CORS, allow-list) are exposed as parsed list
  properties.
- `app/infrastructure/logging.py` — minimal stdout logging setup (`configure_logging`, `get_logger`);
  correlation ids + tracing deferred to Stage 7.
- `app/api/main.py` — FastAPI **application factory** (`create_app`) + module-level `app`, CORS
  middleware from settings, a startup **lifespan** hook (model preload + DI wiring reserved for Stage
  6), and `GET /health`.
- `tests/test_health.py` — smoke test driving the real ASGI app via `TestClient`.

### Tooling & config files
- `backend/environment.yml` — conda env `govguide` (Python 3.11 + pip → editable install).
- `backend/pyproject.toml` — project metadata; Stage-0 deps (`fastapi`, `uvicorn[standard]`,
  `pydantic`, `pydantic-settings`) + dev (`pytest`, `httpx`, `ruff`, `mypy`); **strict mypy**, a
  pragmatic ruff rule set, pytest config.
- `backend/.env.example` — documented template for every config key (`.env` stays gitignored).
- `backend/README.md` — conda setup, run, and quality-gate instructions.

### Verified
```
pytest  → 1 passed
ruff    → All checks passed
mypy    → Success: no issues found in 17 source files (strict)
import  → app.api.main:app builds a FastAPI app exposing /health
```

### Deltas from the planning docs
- **Additions to the proposed tree** (all expected, none conflicting): `backend/tests/` (mirrors
  `app/`), `backend/environment.yml`, `backend/pyproject.toml`, `backend/.env.example`,
  `backend/README.md`, and this `docs/10-backend-implementation.md`.
- **Tooling made concrete:** conda + Python 3.11 + `pyproject.toml` (the docs left the package manager
  open).
- **Config centralisation:** AD-8 τ, AD-2 loop cap, AD-10 rate limit, and the QA-7 allow-list now exist
  as single tunable settings ahead of the code that consumes them — so later stages wire to config,
  not magic numbers.

### Known minor issues
- `fastapi.testclient` emits a `StarletteDeprecationWarning` (upstream Starlette↔httpx version churn).
  Harmless; revisit if it becomes an error on a future bump.

### Dependency manifests & pinning (added pre-Stage-1)
Two manifests are kept in sync: `backend/pyproject.toml` is the **source of truth** (declarative
version *ranges*); `backend/requirements.txt` is the **pinned**, pip-installable runtime set
(`pip install -r requirements.txt`) for deploy / pip-only workflows. Both grow per stage.

**LangGraph/LangChain are now 1.x** — a major jump from the 0.x era the planning docs implicitly
assumed. The stack was installed into the `govguide` env early (at the user's request) and **verified
to co-resolve and import**, pinned at:

| Package | Version | Role |
|---|---|---|
| `langgraph` | 1.2.6 | state graph / supervisor (Stage 5) |
| `langgraph-checkpoint-sqlite` | 3.1.0 | `SqliteSaver` / `AsyncSqliteSaver` checkpointer — AD-3 (pulls `aiosqlite`) |
| `langchain-core` | 1.4.8 | messages, runnables, `with_structured_output` |
| `langchain-google-genai` | 4.2.5 | Gemini Flash provider — AD-6 (pulls `google-genai` 2.9) |
| `langchain-groq` | 1.1.3 | Groq fallback provider — AD-6 |

We depend on these **specific packages**, not the `langchain` umbrella — our agents call the
`LLMProvider` port, not LangChain directly, which keeps the hexagonal boundary clean. `langsmith`
(0.8.18) arrives transitively for optional tracing (QA-8).

**1.x API deltas to honor in Stages 4–5** (vs. older tutorials): graph via
`StateGraph` + `add_conditional_edges`; human-in-the-loop via `interrupt()` + `Command(resume=...)`;
structured output via `ChatModel.with_structured_output(PydanticModel)`. The exact `interrupt`/`Command`
surface will be checked against the installed 1.2.6 when Stage 5 lands.

### Cumulative runtime dependencies
`fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `langgraph`,
`langgraph-checkpoint-sqlite`, `langchain-core`, `langchain-google-genai`, `langchain-groq`,
`chromadb`, `sentence-transformers` (→ torch), `tavily-python`, `ddgs`, `pymupdf`, `trafilatura`
(+ dev: `pytest`, `httpx`, `ruff`, `mypy`).

---

## Stage 1 — Domain core (pure) ✅

**Goal:** entities + the five ports, framework-free, with an automated purity guard.

### Implemented
- `app/domain/entities.py` — 8 `StrEnum`s (`Grade`, `VerificationStatus`, `SourceType`,
  `OfficeType`, `ReportOutcome`, `ReportStatus`, `MessageRole`, `ActionPackVerification`) plus the
  entity / value-object set as `@dataclass(frozen=True, slots=True)`: catalog (`Service`,
  `ServiceVariant`, `Requirement`, `Fee`, `Office`, `DistrictVariation`, `ServiceOffice`),
  provenance (`Source`, `KBChunk`), retrieval (`RetrievedChunk`), the Action Pack family
  (`ActionPack`, `DocumentItem`, `FeeLine`, `ActionPackOffice`, `Citation`), feedback
  (`ExperienceReport`), and session (`Session`, `SessionMessage`, `StoredChecklist`).
- `app/domain/ports/` — five sync, `@runtime_checkable` Protocols: `LLMProvider`,
  `EmbeddingProvider`, `KnowledgeStore` + `Retriever`, `WebSearch` (+ `WebResult`), `SourceParser`
  (+ `ParsedDocument`); re-exported from `ports/__init__.py`.

### Decisions realised
- **Sync ports** (user's call) — async + SSE handled later at the API/graph layer.
- **Domain stays Pydantic-free.** `LLMProvider.complete_structured(prompt, schema: type[T]) -> T`
  is generic over the schema type, so structured-output schemas (Pydantic) live in the application
  layer and `domain/` imports only the stdlib.
- **Immutable value semantics** (`frozen=True, slots=True`) + `Decimal` money + `int | None` ids.

### Deltas from the ER (docs/05)
- `OFFICE.type` → **`office_type`** in code (avoids shadowing the `type` builtin); same intent.
- Added runtime **value objects** the ER doesn't model as tables: `RetrievedChunk` (A4 output), the
  `ActionPack` family (A6 output), and the `ActionPackVerification` label enum. `CHECKLIST` is the
  persisted form, represented by `StoredChecklist` (wraps an `ActionPack`).

### Verified
```
pytest → 9 passed   (entities, ports-satisfy-protocols, + domain purity guard)
ruff   → All checks passed
mypy   → Success, 23 source files (strict)
```
`tests/domain/test_purity.py` AST-scans `app/domain/` and fails on any framework import, so the
pure-core rule (AD-9) can't silently rot.

### Dependencies
No new runtime dependencies — the domain is stdlib-only by design.

---

## Stage 2 — Data layer (SQLite + Chroma + bge) ✅

**Goal:** the knowledge store + embeddings adapters behind the Stage-1 ports, tested with a torch-free
fake embedder and verified once for real with bge.

### Implemented
- `app/adapters/knowledge/schema.sql` — full ER schema (`CREATE TABLE IF NOT EXISTS`), incl. the
  `source.content_hash` dedup column.
- `app/adapters/knowledge/chroma_sqlite.py` — `ChromaSqliteStore` implements **both**
  `KnowledgeStore` and `Retriever`: stdlib `sqlite3` (parameterized SQL, FK pragma, row↔dataclass
  mappers, Decimal-as-TEXT, ISO dates) + ChromaDB `PersistentClient` (cosine `kb_chunks` collection,
  telemetry off, **bge vectors supplied explicitly**). Catalog writes/reads, source dedup, chunk
  upsert (sets `vector_ref`), and `search()` → `RetrievedChunk[]` (cosine distance→similarity,
  provenance joined back from SQLite).
- `app/adapters/embeddings/bge.py` — `BgeEmbeddingProvider` over `bge-base-en-v1.5`: **lazy import**
  (module loads without torch), normalized vectors, BGE query instruction on `embed_query`.
- `app/adapters/knowledge/seed.py` — `KnowledgeSeeder` loads a catalog JSON via the **ports**
  (returns `SeedStats`). Format + example live in `data/seed/` (`catalog.example.json`, `README.md`).

### Decisions realised
- **Raw `sqlite3`** (user's call) — no ORM.
- **Full embeddings stack installed now** (user's call) — chromadb + sentence-transformers + torch;
  bge exercised for real (768-d).
- Chroma is a **pure vector store**; its built-in embedding function is unused; telemetry disabled.

### Port refinement (vs Stage 1)
`KnowledgeStore` gained **catalog write methods** (`add_service` / `add_variant` /
`add_requirement` / `add_fee` / `add_office`, `link_service_office`, `add_district_variation`) needed
by the seeder and (later) B3; `upsert_source` gained a `content_hash` keyword. The Stage-1 port fake
and tests were updated to match — ports firming up as adapters land, exactly as planned.

### Deltas from the ER (docs/05)
- `source.content_hash` column added (B3 dedup; not in the ER).
- Money stored as **TEXT** to preserve `Decimal` precision.
- `find_services` is **lexical (LIKE)** for now; vector service-matching is deferred to A2 / Stage 4.

### Verified
```
pytest → 17 passed   (store CRUD / dedup / filtered search via DeterministicEmbedder;
                      seed load; real bge 768-d embedding)
ruff   → All checks passed
mypy   → Success, 26 source files (strict)
```
Adapter tests use a torch-free `DeterministicEmbedder` (hashed bag-of-words) so they stay fast; the
real bge test downloads the model (~440 MB) to the HuggingFace cache on first run.

### Dependencies added
`chromadb` 1.5.9 (+ onnxruntime, opentelemetry, kubernetes client, …) and
`sentence-transformers` 5.6.0 (+ **torch 2.12.1**, transformers, scikit-learn, scipy, numpy).

---

## Stage 3 — External adapters + infra ✅

**Goal:** give the remaining ports concrete adapters (LLM providers, web search, parser) and stand up
the two cross-cutting infrastructure pieces (rate-limited LLM gateway, query→answer cache) — all
behind the Stage-1 ports, and all testable without API keys or network.

### Implemented
- **LLM providers** (`app/adapters/llm/`):
  - `base.py` — `LangChainLLMProvider`, a shared wrapper adapting any LangChain `BaseChatModel` to the
    `LLMProvider` port. The hot path is **import-free** (messages are passed as `(role, content)`
    tuples — a valid `LanguageModelInput`), so the wrapper is unit-testable with a fake model and
    importing the module never pulls LangChain. The port's **per-call `temperature`** is honoured by
    building + memoizing one chat model per distinct temperature (LangChain fixes temperature at
    construction). `complete_structured` delegates to `with_structured_output`, keeping Pydantic out
    of the domain.
  - `gemini.py` (`GeminiLLMProvider`, primary · `gemini-2.5-flash`) and `groq.py` (`GroqLLMProvider`,
    fallback · `llama-3.1-8b-instant`): thin subclasses whose factory lazy-imports the provider SDK;
    API keys are wrapped in `pydantic.SecretStr` (the providers' typed field).
- **LLM gateway** (`app/infrastructure/llm_gateway.py`, AD-10) — `LLMGateway` is a **decorator that is
  itself an `LLMProvider`**, so agents stay oblivious to it. A thread-safe `TokenBucket` (injectable
  clock/sleep) caps requests/min (default 15); transient failures retry with exponential back-off; the
  gateway then fails over to the secondary provider before giving up.
- **Query→answer cache** (`app/infrastructure/cache.py`, AD-12) — `AnswerCache`, a thread-safe **LRU**
  keyed by `CacheKey(service, variant, district)` (district normalized), with `invalidate_service()`
  for the on-upsert invalidation. Stores the domain `ActionPack` directly.
- **Web search** (`app/adapters/web_search/`):
  - `allowlist.py` — `host_allowed()` / `normalized_domains()`: the QA-7 official-domain enforcement
    shared by both adapters (a host matches a domain or any of its sub-domains; lookalikes like
    `fakegov.lk` are rejected).
  - `tavily.py` (`TavilyWebSearch`, primary) applies the allow-list both server-side
    (`include_domains`) and locally; `ddg.py` (`DdgWebSearch`, keyless fallback) biases the query with
    `site:` operators, over-fetches, then filters locally. Both lazy-import their SDK and accept an
    **injected client** for testing / DI.
- **Source parser** (`app/adapters/parser/pymupdf.py`) — `PyMuPdfSourceParser`: PDF text + metadata via
  PyMuPDF, HTML main-content via trafilatura (nav/boilerplate stripped). Both libraries lazy-imported.

### Decisions realised
- **Shared LangChain base, thin providers** — the prompt→messages→invoke and structured-output logic
  lives once in `base.py`; `gemini`/`groq` differ only by which `BaseChatModel` their factory builds,
  so adding/swapping a provider is a few lines (Strategy/Adapter, per docs/02).
- **Gateway as a port decorator** (Decorator + Façade over Gemini, AD-10) — the throttle/retry/failover
  is invisible to callers, which depend only on `LLMProvider`.
- **Hand-rolled retry/back-off (no `tenacity`)** — the token bucket is custom anyway; a ~15-line,
  fully-injected retry keeps the logic visible and dependency-light (the gateway is a defense point).
- **No API key needed to import or test** — every provider/SDK is lazy-imported and the offline tests
  inject fakes, so the stage stays green with zero keys; the key-gated live smoke is deferred.

### Deltas from the planning docs
- **Cache is an in-memory LRU, not a SQLite table** (docs/04 named a "SQLite table"). In-memory fully
  satisfies AD-12's goal — short-circuiting repeated queries / demo re-runs within a running server —
  without prematurely serializing the nested `ActionPack` to SQLite. Cross-restart persistence is
  deferred until the Action-Pack JSON DTO exists (Stage 6). **AD-12 itself is unchanged** (key +
  invalidate-on-upsert); this is a storage-mechanism detail, not a new ADR. (Noted in docs/04 too.)
- **Parser `source_type` is a provisional, medium-based hint** (PDF→`circular`, HTML→`portal`). The
  parser never classifies a government-document category from bytes; **B2 sets the authoritative
  `source_type`** during curation (Stage 4).
- **Gateway retries any exception** (bounded by `max_retries`) rather than importing provider-specific
  transient-error types — a deliberate trade-off to keep infrastructure free of adapter details.
- **Ports unchanged this stage** — unlike Stage 2 (which firmed up `KnowledgeStore`), the Stage-1
  `LLMProvider` / `WebSearch` / `SourceParser` ports needed no changes; adapters implemented them as-is.
- **`langchain-groq` now consumed** — declared since Stage 0 (for Stages 4–5), it becomes the fallback
  `LLMProvider` here.

### Verified
```
pytest → 41 passed, 4 skipped   (24 new offline: LLM wrapper, gateway throttle/retry/fallback,
                                 cache LRU/invalidation, web-search allow-list + field mapping,
                                 real PyMuPDF + trafilatura parsing; 4 skipped = opt-in live smoke)
ruff   → All checks passed
mypy   → Success, 35 source files (strict)
```
The LLM-wrapper, gateway, cache, and web-search tests are **fully offline** (fake models / injected
clients) — no keys, no network. The parser test exercises real PyMuPDF + trafilatura, skipping
automatically if absent (mirrors the bge test). A **key-gated live smoke** suite
(`tests/adapters/test_live_smoke.py`) hits the real providers; it is **opt-in** via `RUN_LIVE_TESTS=1`
(+ the relevant key), so the default gate always skips it and stays fast + hermetic.

**Live smoke run (with the team's keys, 2026-06-21):** all four pass — Gemini, Groq
(`llama-3.1-8b-instant`), Tavily, and DDG. The first run surfaced that **`gemini-2.0-flash` has
free-tier `limit: 0`** on this project (429 RESOURCE_EXHAUSTED): the key was valid, the *model* simply
isn't free-tier-eligible here. Listing the key's accessible models showed **`gemini-2.5-flash`** (and
`-lite`) work, so the default model was switched **`gemini-2.0-flash` → `gemini-2.5-flash`**
(`config.py`, `.env.example`, `gemini.py`; still "Gemini 2.x Flash" per AD-6). The AD-10 Gemini→Groq
fallback remains the safety net if the primary is ever throttled.

### Dependencies added
`tavily-python` 0.7.26, `ddgs` 9.14.4 (+ `primp`), `pymupdf` 1.27.2.3, `trafilatura` 2.1.0 (+ `lxml`).
No new dev tools. `langchain-groq` 1.1.3 (already pinned) is now exercised for the first time.

### Known minor issues
- `langchain-google-genai` / `langchain-groq` ship `py.typed`, but with no pydantic-mypy plugin
  configured their constructors are seen as `(**data: Any)`, so kwargs pass untyped — we still wrap
  keys in `SecretStr` for correctness. PyMuPDF's `Document` API is only partially typed, so the PDF
  handle is annotated `Any` with a single localized `type: ignore[no-untyped-call]`.
## Stage 4a — GraphState + Team 1 agents (A1–A6) ✅

**Goal:** the shared blackboard state and the synchronous **Answering** path
(`A1 → A2 → A3 → A4 → A5 → A6`) as framework-free agent nodes, fully unit-tested
against the Stage-1 ports — independent of Stage 3 (adapters) and Stage 5 (wiring).

> Stage 4 is split into **4a (Team 1, this section)** and **4b (Team 2, B1–B4)** to keep each
> review-paused unit coherent. Team 2 (the acquisition pipeline) is built next.

### Implemented
- `app/application/graph/state.py` — the **`GraphState`** `TypedDict` (the Blackboard, docs/02) plus a
  `new_state()` factory. It is a **plain `TypedDict` with no LangGraph import**: agents are pure
  `(GraphState) -> dict` callables; the `StateGraph`/checkpointer/`interrupt()` are Stage 5.
- `app/application/graph/serialization.py` — mappers flattening domain value objects
  (`RetrievedChunk`, `ActionPack`, `Citation`) into the JSON-serialisable state. Money is serialised
  as a **string** to preserve `Decimal` precision (same rationale as the data layer's TEXT money).
- `app/application/agents/schemas.py` — the Pydantic structured-output schemas (one per LLM call):
  `IntentExtraction` (A1), `ServiceDisambiguation` (A2), `ClarificationQuestion` (A3), `GradeDecision`
  (A5), `ActionSteps` (A6). They live in the **application** layer so the domain stays Pydantic-free.
- **Agents** `app/application/agents/a1…a6` — each a small DI'd class with `__call__(state) -> dict`:
  - **A1 IntakeIntent** — one structured LLM call → `intent`; seeds `slots` from stated entities.
  - **A2 ServiceIdentifier** — catalog match (`find_services`) + LLM disambiguation when several
    candidates are close; no confident match → `service_unknown` (→ gap path).
  - **A3 Clarification** — minimal slot-filling: pins `variant_id` (condition slot) + district, asks
    one question at a time via `pending_question`; options grounded in catalog variant labels; caps
    the interview and defaults to the most-common variant when exhausted.
  - **A4 Retrieval** — local query embedding + vector search filtered by `service_id`; writes only
    chunk text + provenance to state (AD-3 leanness).
  - **A5 GapGrader** — two-stage Corrective-RAG switch: cheap score threshold, LLM only on the
    borderline band (bias to `GAP` without one); writes `grade` + `answer_confidence`.
  - **A6 ActionPackGenerator** — **confidence gate first** (AD-8), then assembles documents/fees/office
    **deterministically from the store**; LLM (optional) only sequences `steps`.

### Decisions realised
- **Agents are LangGraph-free** (user's hexagonal intent): they depend only on `domain.ports` + the
  application schemas, so they unit-test with fakes and add **zero new runtime dependencies**. The
  graph assembly, supervisor router, reducers and `SqliteSaver` are deferred to Stage 5.
- **Minimal LLM footprint (AD-10 / free tier):** only **A1** strictly needs the LLM; **A2/A3/A5/A6**
  take an *optional* `LLMProvider` with deterministic fallbacks — the answering path is testable and
  quota-light, and the LLM is spent only where it adds value (intent, disambiguation, phrasing,
  borderline grading, step narration).
- **A6 correctness refinement:** hard facts (documents/fees/office) are read deterministically from the
  store at generation time — guaranteeing groundedness *and* picking up rows a gap-loop acquisition
  just wrote — while the LLM is constrained to the `steps` narrative only.
- **Config not imported in `application/`:** tunables that agents need (τ, thresholds, question cap,
  candidate limit) are **constructor parameters** with sensible defaults, injected at the edges in
  Stage 5/6 from `Settings`. This also avoids touching the shared `config.py` while Stage 3 is in
  flight on another branch.

### Deltas from the planning docs (and why)
- **`GraphState` field types/shape (vs docs/02 illustration):** `service_id`/`variant_id` are
  `int | None` (the catalog uses integer PKs, not the doc's illustrative `str`); `pending_question`
  is a structured dict `{slot, question, options, allow_free_text}` — it maps 1:1 onto the doc/11
  `clarify` SSE event and tells the Stage-5 resume step which slot the reply fills. A few fields the
  agent docs name are made explicit: `service_unknown` (A2), `grade_reason` (A5), `asked_slots` (A3
  guardrail) and the Team-2 fields (`acquisition_buffer`, `curated`, `kb_updated`, `moderation_queue`).
- **A2 matching is lexical + LLM disambiguation** for the MVP. The Stage-2 note deferred "vector
  service-matching" to A2/Stage 4; full vector matching remains a **noted enhancement** — lexical
  `find_services` + a short disambiguation call is enough for the seeded flagship services and keeps
  A2 deterministic and quota-light.
- **A4 returns chunks only; A6 re-reads structured rows** (vs the A4 doc listing linked
  `REQUIREMENT/FEE/OFFICE` rows in its output). This keeps the checkpointed state lean (AD-3) and is
  *more* correct for the self-expanding loop — A6 always sees the freshest rows after a B3 upsert.
- **A6 assembles facts deterministically + LLM-narrates steps** (vs the A6 doc showing the LLM filling
  the whole pack). Stronger groundedness guarantee for QA-1/AD-8. The cost/transport heuristic (cost
  tool) is still deferred to Stage 7; `estimated_cost_lkr` is currently the sum of fees.

### Verified
```
pytest → 49 passed   (graph state + serialization; A1–A6 each tested for happy path,
                      gap/unknown branches, the A6 confidence gate + verified-bypass)
ruff   → All checks passed
mypy   → Success, 35 source files (strict)
```
Agent tests use a `ScriptedLLM` fake (replays structured outputs) and a **real** `ChromaSqliteStore`
seeded with a tiny two-service catalog via `KnowledgeSeeder` (torch-free `DeterministicEmbedder`), so
A2/A3/A4/A6 are exercised against genuine SQLite + Chroma behaviour while staying fast.

### Dependencies added
None — the answering agents are pure Python over the ports + Pydantic (already present). LangGraph
enters in Stage 5.

---

## Stage 4b — Team 2 agents (B1–B4) ✅

**Goal:** the **Knowledge Acquisition** pipeline `B1 → B2 → B3 → B4` (the
self-expanding RAG loop, docs/03) as framework-free agent nodes over the ports —
the path A5 triggers on a `GAP`.

### Implemented
- **New port** `app/domain/ports/source_pool.py` — **`SourcePool`** (+ `PooledDocument`
  value object): read access to the local, pre-collected, *not-yet-ingested* source pool that B1
  searches before the web (AD-7). The pool is a store distinct from the KB (docs/02 C4-L3) and had no
  port; this is an **additive Stage-4b port** (re-exported from `ports/__init__.py`, fake added to the
  `tests/domain/test_ports.py` contract test). Its adapter over `data/source_pool/` (file read +
  PyMuPDF/trafilatura parse) is **Stage 3** (parallel).
- `app/application/agents/schemas.py` — B2 extraction schemas: `CuratedExtraction` (+ nested
  `CuratedRequirement` / `CuratedFee` / `CuratedOffice`). Money stays a **string** (no float).
- **Agents** `app/application/agents/b1…b4`:
  - **B1 Research** — orchestrates `SourcePool` (local-first) then `WebSearch` (allow-listed fallback,
    QA-7); writes raw candidates to `acquisition_buffer`. Pure port-orchestrator (parsing lives in the
    adapters); `acquisition_loops` is bumped by the supervisor, not B1.
  - **B2 Extract & Curate** — one structured LLM call per raw doc → `CuratedExtraction` + a `SOURCE`
    (`auto_gathered`); `confidence = authority(origin) * extraction_certainty`; drops docs with no
    identifiable service. Writes `curated`.
  - **B3 KB-Updater** — **idempotent**: dedup by url + SHA-256 content hash, then write `SOURCE` +
    structured rows (reuse-or-create service/variant by slug/condition label, never overwriting
    `verified`), chunk → embed locally (AD-4) → upsert vectors with `service_id` metadata. Sets
    `kb_updated` so the supervisor re-runs A4.
  - **B4 Moderation Gate** — **serve-but-label, never block** (MVP = rules only): appends non-verified
    acquired records to `moderation_queue` (deduped by url+title), flagging low-confidence/web items
    for review.

### Decisions realised
- **Agents stay LangGraph-free and port-only** — Team 2 adds **no new runtime dependency**; it only
  introduces the `SourcePool` *interface* (its adapter is Stage 3). Tested entirely with fakes + the
  real seeded `ChromaSqliteStore` (for B3's genuine SQLite/Chroma writes, dedup and reuse).
- **B3 is idempotent by content hash** — re-running a bounded gap loop (cap `N`) can't double-write;
  this is what makes "the first user's research is cached for everyone after" safe.
- **Confidence is provenance-weighted** (B2) — local pool (0.8) is trusted more than a web snippet
  (0.5), multiplied by the LLM's own extraction certainty; this feeds AD-8's serving gate and B4's
  review flag.

### Deltas from the planning docs (and why)
- **`SourcePool` is a new port** (not named in docs 01–09): the architecture models the local source
  pool as a first-class store (AD-7, C4-L3) but no interface existed. Added additively in Stage 4b;
  logged here so the Stage-3 builder knows to implement its adapter.
- **B1 is a pure port-orchestrator** (vs the doc listing PyMuPDF/trafilatura inside B1): fetch/parse
  lives in the `SourcePool`/web adapters (Stage 3), keeping the agent layer framework-free. The web
  fallback currently carries the result **snippet** as evidence; full-page fetch+parse is a noted
  enhancement.
- **B4 is rules-only in-graph** (per the doc's explicit MVP note): it builds the in-state
  `moderation_queue`; the DB promote/reject transitions need a `KnowledgeStore` status-update method +
  the moderation API, which are **Stage 6**. The interrupt-driven console is roadmap.
- **Experience-report intake** (the second B2→B3 entrypoint, docs/03) reuses the same B2/B3 path; the
  API that feeds a report into it is wired in **Stage 6**. Stage 4b implements the research-driven path.

### Verified
```
pytest → 64 passed   (+15: SourcePool port contract; B1 local/web/fallback routing + allow-list;
                      B2 provenance + authority-weighted confidence + drop-unmappable; B3 new-service
                      write, idempotent dedup, reuse-service/append-variant; B4 queue/skip/flag/dedup)
ruff   → All checks passed
mypy   → Success, 40 source files (strict)
```
B3 tests run against a **real** `ChromaSqliteStore` (torch-free `DeterministicEmbedder`), so dedup and
reuse-or-create are exercised against genuine SQLite + Chroma behaviour.

### Dependencies added
None — Team 2 agents are pure Python over the ports + Pydantic. The `SourcePool`/`WebSearch` adapters
(Tavily/`ddgs`, PyMuPDF/trafilatura) and their deps land with Stage 3.

### What's next
- **Stage 5 — LangGraph wiring:** assemble the `StateGraph`, the supervisor/router (state-driven edges
  + the bounded gap loop), `interrupt()`/`Command(resume=...)` for A3, and the `SqliteSaver`
  checkpointer; inject concrete adapters + `Settings` tunables (τ, `N`, allow-list) into the agents.
- **Stage 3 (parallel):** implement the `SourcePool` adapter (new this stage) alongside the LLM /
  WebSearch / SourceParser adapters.

---

## Stage 5 — LangGraph wiring ✅

**Goal:** assemble the ten agents into one compiled, supervised `StateGraph` — the
Answering path `A1→A6` plus the bounded acquisition loop `B1→B4` — with A3's
human-in-the-loop interview as a real LangGraph `interrupt()`, and an injected
checkpointer. This is the first stage that imports LangGraph.

### API verified against the installed runtime (langgraph 1.2.6)
Before wiring, the exact 1.x surface was probed in the `govguide` env (the planning
docs flagged this): `from langgraph.graph import StateGraph, START, END`;
`from langgraph.types import interrupt, Command`;
`from langgraph.checkpoint.{sqlite.SqliteSaver, memory.MemorySaver}`;
`add_conditional_edges(source, path, path_map)`; `compile(checkpointer=...)`.
The interrupt lifecycle was confirmed end-to-end: a hit `interrupt(payload)` surfaces
as `result["__interrupt__"][0].value` and pauses; `invoke(Command(resume=answer),
config)` re-enters the node with the answer.

### Implemented
- `app/application/graph/dependencies.py` — **`GraphDependencies`**, a frozen bundle of the ports +
  tunables (τ, `N`, `top_k`, A3 cap, A5 thresholds, allow-list). The builder is **config-free**: it
  takes this, never importing `Settings` or concrete adapters. (`store` and `retriever` are separate
  ports but usually the same `ChromaSqliteStore`.)
- `app/application/graph/builder.py` — **`build_graph(deps, *, checkpointer=None)`**: constructs the
  agent nodes, wires the topology, and returns the compiled graph.
  - **State-driven supervisor** as conditional edges (zero LLM quota on routing): `route_after_identify`
    (unknown → straight to `A4`; known → `A3`), `route_after_clarify` (`pending_question` → `clarify`
    else `A4`), `route_after_grade` (`SUFFICIENT → A6`; `GAP & loops<N → enter_gap`; else `A6`
    fallback).
  - **Two wiring-only nodes** (kept out of the agents): `clarify` calls `interrupt(pending_question)`
    and writes the resumed answer into `slots[slot]`; `enter_gap` increments `acquisition_loops` and
    resets the per-loop scratch (`acquisition_buffer`/`curated`/`kb_updated`). Loop bookkeeping lives
    in the supervisor, not the agents.
  - Topology: `START→a1→a2 ┬unknown→a4 / └known→a3⇄clarify→a4`; `a4→a5 ┬SUFFICIENT→a6 / ├GAP&loops<N→
    enter_gap→b1→b2→b3→b4→a4 / └GAP&loops≥N→a6`; `a6→END`.
- `app/application/graph/__init__.py` — re-exports only the **agent-free** pieces (`GraphState`,
  `new_state`, `GraphDependencies`); `build_graph` is imported from its module to break an import cycle
  (agents depend on `GraphState`; the builder depends on the agents).

### Two small agent refinements (discovered while wiring; logged here)
- **B3 hands the new `service_id` back** — for an *unknown-service* gap, re-entering `A4` alone never
  clears `service_unknown`, so the loop couldn't converge. B3 now returns the `service_id` it created
  **only when `service_unknown` was set**; a known-service gap keeps its existing id. This is the
  natural "return control to A4" handoff and makes Scenario B (unseen service) converge with a plain
  `b4→a4` edge.
- **A1↔A3 slot bridge** — A1 seeds the variant condition as `relationship`; A3 now resolves the
  variant from `condition` **or** `relationship`, so A1's extracted "inheritance" auto-resolves the
  variant instead of forcing a redundant clarifying question.

### Deltas from the planning docs (and why)
- **Loop-back target is `A4` with a B3 handoff** (vs the supervisor doc's bare "back to A4"): re-entry
  alone can't clear `service_unknown`, so B3 returns the new `service_id` — documented above.
- **`enter_gap` increments the loop counter** (vs the doc's "B1 increments via the supervisor"): the
  increment + scratch-reset is a single supervisor-owned wiring node, keeping B1 a pure researcher.
- **Checkpointer is injected, not hard-wired** — `build_graph` takes it as a parameter (`SqliteSaver`
  in prod via the API, `MemorySaver` in tests). The application layer never imports the checkpointer
  backend; that wiring is Stage 6.

### Verified
```
pytest → 71 passed   (+7: graph happy-path on a seeded service; full gap loop acquiring an unseen
                      service then answering it "pending verification"; bounded loop → graceful
                      fallback; A3 interrupt→resume; B3 service_id handoff; A3 relationship bridge)
ruff   → All checks passed
mypy   → Success, 42 source files (strict)
```
The graph tests run the **real compiled `StateGraph`** end-to-end over a `MemorySaver`, with a
`ScriptedLLM` and a seeded `ChromaSqliteStore` — so the self-expanding loop (research → curate → embed
→ re-retrieve → answer) and the interrupt/resume interview are exercised against genuine LangGraph
execution.

### Dependencies added
None new — `langgraph` + `langgraph-checkpoint-sqlite` were already declared (Stage 0) and are now
actually imported. The `SqliteSaver`/`MemorySaver` choice is made at the edge (Stage 6 / tests).

### What's next
- **Stage 6 — API delivery (SSE):** map graph execution to the doc/11 SSE events (`step`/`token`/
  `clarify`/`gap`/`action_pack`/`done`), construct `GraphDependencies` from `Settings` + the real
  adapters, mount `SqliteSaver`, and add the experience-report + moderation endpoints.
- **Stage 3 (parallel):** the LLM / WebSearch / SourceParser / `SourcePool` adapters the deps expect.

---

## Stage 6a — API delivery: chat SSE + composition root ✅

**Goal:** expose the agent runtime over HTTP/SSE — the citizen-facing `POST /api/chat`
stream and the Action-Pack fetch — by assembling the **Stage-3 adapters** into the
**Stage-5 graph** behind a composition root. (Stage 6 is split: **6a** = the core chat
path here; **6b** = experience-reports + moderation.)

### Implemented
- **`SourcePool` adapter** (`app/adapters/source_pool/filesystem.py`, `FilesystemSourcePool`) — the
  one adapter Stage 3 left open (flagged in 4b). It reads `data/source_pool/` and returns the best
  keyword/filename matches as `PooledDocument`s, delegating PDF/HTML extraction to the `SourceParser`.
  Matching is **lexical** for the MVP (the doc's "ChromaDB over the pool" vector index stays a noted
  enhancement).
- **Composition root** (`app/api/runtime.py`) — `build_runtime(settings)` wires every adapter
  (`LLMGateway(Gemini, fallback=Groq)`, `BgeEmbeddingProvider`, `ChromaSqliteStore`,
  `FilesystemSourcePool`, Tavily-or-DDG) into `GraphDependencies`, compiles the graph with a
  **persistent `SqliteSaver`** (AD-3), and returns an `AppRuntime`. `get_runtime` is a FastAPI
  dependency that builds this **lazily** and caches it on `app.state` — so the process boots instantly,
  the bge model loads on first use, and tests override the dependency (no keys, no network, no torch).
- **SSE translation** (`app/api/sse.py`) — `EventTranslator` maps `graph.stream(stream_mode="updates")`
  chunks to the doc/11 event stream: node→`step` pill transitions, `enter_gap`→`gap:researching`,
  `b3`(kb updated)→`gap:updated`, `a6`→`action_pack` (+ `message` on fallback), `__interrupt__`→
  `clarify`, then `done`; `format_sse` renders the frames.
- **DTOs** (`app/api/dto.py`) — snake_case Pydantic `ActionPackDTO` (+ item models) and `ChatRequest`.
  Money is rendered as a **number** on the wire (the state carries a precise `Decimal` string; Pydantic
  coerces it) — matching the doc/11 contract.
- **Routes** (`app/api/routes/chat.py`):
  - `POST /api/chat` → `StreamingResponse` of a **sync** generator. Starlette runs it in a worker
    thread, so the synchronous graph + its SQLite checkpointer execute off the event loop with **no
    manual async bridge**. A new `session_id` is minted when absent.
  - **Resume vs. fresh** is decided by `graph.get_state(config).next`: a paused interview (non-empty
    `next`) resumes with `Command(resume=message)`; anything else starts a fresh `new_state` run.
  - `GET /api/sessions/{id}/action-pack` reads the final `answer` from the checkpointed state (404 if
    none).
- `app/api/main.py` now stashes `Settings` on `app.state` and mounts the chat router (health probe
  retained).

### Decisions realised
- **Sync generator over `StreamingResponse`** (not a manual thread+`asyncio.Queue` bridge) — verified
  the `graph.stream` chunk shapes up front (incl. the `__interrupt__` chunk + `get_state().next`), then
  let Starlette's threadpool own the off-loop execution. Simpler and keeps the checkpointer on one
  thread.
- **Lazy, override-friendly runtime** — construction is key-free and cheap (all SDK/model imports are
  lazy), so `build_runtime` runs without secrets; the API tests inject a fake `AppRuntime` (real graph
  over a `ScriptedLLM` + seeded store + `MemorySaver`) via `dependency_overrides`.
- **Graceful in-stream errors** — the producer catches exceptions and emits an SSE `error` frame rather
  than tearing the response with a 500 mid-stream.

### Deltas from the planning docs (and why)
- **`token` events are not emitted** (doc/11 lists them): the MVP streams complete `action_pack` +
  `step`/`gap` events, not per-token LLM output (that needs `stream_mode="messages"` + provider token
  streaming). Fallbacks surface as a `message` frame. Token streaming is a noted enhancement.
- **`AnswerCache` is constructed but not yet consulted** — AD-12's key is `service+variant+district`,
  which only exists *after* A2/A3 resolve, so a correct short-circuit needs mid-graph cache nodes +
  invalidation on B3. Deferred to Stage 7 (it's an optimization, not correctness); the runtime already
  holds the cache ready.
- **First-request warm-up** — the bge model loads on the first `/api/chat` (lazy `get_runtime`), not at
  boot, so tests and cold starts stay fast; a warm-up request is recommended before a demo.

### Verified
```
pytest → 103 passed, 4 skipped   (+8 here: 4 chat-SSE — happy/clarify+resume/gap-loop/pack-fetch
                                  driving the REAL compiled graph through TestClient; 4 SourcePool)
ruff   → All checks passed
mypy   → Success, 58 source files (strict)
```
The chat tests run the genuine LangGraph SSE path end-to-end over a `TestClient` with a fake runtime, so
the event translation, interrupt→resume, and the self-expanding loop are all exercised against real
graph execution. **Env note:** this stage refreshed the env (`pip install -e .[dev]`) to pull the
Stage-3 SDKs (`pymupdf`/`trafilatura`/`tavily`/`ddgs`), which also un-skipped Stage 3's real-parser
tests (the 4 remaining skips are the opt-in live-provider smoke).

### Dependencies added
None new — Stage 6a is FastAPI + the already-declared `langgraph` checkpointer. The Stage-3 provider
SDKs were installed into the env this stage (declared since Stage 3).

### What's next
- **Stage 6b — feedback + moderation:** `POST /api/experience-reports`, `GET /api/moderation/queue`,
  `POST /api/moderation/{source_id}/promote|reject`. These need three additive `KnowledgeStore` methods
  (write an experience report, list the `auto_gathered` queue, set a source's verification status) +
  the experience-report → B2/B3 entrypoint.
- **Stage 7 — hardening:** wire the `AnswerCache` short-circuit + invalidation, correlation-id tracing
  (QA-8), and token streaming.

---

## Stage 6b — API delivery: feedback + moderation ✅

**Goal:** close the citizen-feedback and admin-moderation loops over HTTP — the
experience-report intake (the **second** B2→B3 entrypoint, docs/03) and the B4
moderation queue (list / promote / reject). This completes the doc/11 §2 endpoint
contract and turns B4's in-graph "serve-but-label" into a real human review path.

### Implemented
- **Domain** (`domain/`):
  - `VerificationStatus` gains **`REJECTED`** — needed to express the moderator's
    *reject* transition (a 4th state distinct from `verified`/`auto_gathered`/`pending`):
    rejected sources are quarantined (dropped from the queue, de-indexed) but **kept** for
    dedup. A delta from the ER's three-value enum (logged below + in docs/05).
  - `ExperienceReport.service_id` widened `int → int | None` to match the ER's **nullable**
    FK (a report may be filed before a service is resolved; the API resolves it from the
    session when possible).
  - **`KnowledgeStore` port** gains four additive methods: `add_experience_report`,
    `list_sources_for_moderation` (`auto_gathered` + `pending`, newest first),
    `set_source_verification_status` (promote/reject; `None` if the id is unknown), and
    `delete_chunks_for_source` (reject's de-index — removes the chunks from SQLite + Chroma
    while leaving the `source` row).
- **Adapter** (`adapters/knowledge/chroma_sqlite.py`) — the four methods over SQLite +
  Chroma: experience-report insert; a status-filtered, `id DESC` queue read; an UPDATE +
  re-read; and a chunk delete that collects the `vector_ref`s and calls
  `collection.delete(ids=…)` so the vectors actually leave the index.
- **Application use cases** (new, framework-free — stdlib `logging` only):
  - `application/feedback.py` · **`ExperienceReportIntake`** — *persist always, ingest
    best-effort*: it saves the report (`status=pending`), then runs the **same B2/B3 agents**
    over the report text (shaped as a `source_type=experience`, `origin=experience` buffer
    entry). Anything B3 writes lands as `auto_gathered` and surfaces in the moderation queue.
    A guard (`try/except` + log) guarantees a flaky LLM/embed never loses the citizen's report.
  - `application/moderation.py` · **`ModerationService`** — owns the promote/reject *policy*
    (promote → `verified`; reject → `rejected` **and** `delete_chunks_for_source`), so the
    route stays a thin translator.
  - **B2 refinement:** the authority map gains `experience: 0.4` (citizen reports are useful
    real-world signal but the least authoritative origin → lower `confidence`, so they are
    more likely to be gated/flagged for review).
- **API** (`api/`):
  - `dto.py` — `ExperienceReportRequest` (`outcome` typed as `ReportOutcome`, so a bad value
    is a free **422**), `ExperienceReportResponse` (`{id, status}`), `ModerationItemDTO`,
    `ModerationActionResponse` (`{ok}`).
  - `session_state.py` (new) — `thread_config` / `session_values` helpers shared by the chat
    resume path and the report intake (which reads `service_id`/`district` from the session's
    checkpointed state). `chat.py` was refactored onto `thread_config` (de-duplicated its
    private `_config`).
  - `routes/feedback.py` — `POST /api/experience-reports` (201 + `{id, status}`); resolves
    `service_id`/`district` from the session when the body omits them.
  - `routes/moderation.py` — `GET /api/moderation/queue`, `POST /api/moderation/{source_id}/
    promote|reject` (404 on an unknown id).
  - `runtime.py` — `AppRuntime` gains `experience_intake` + `moderation`, wired in
    `build_runtime` from the same store/LLM/embedder the graph uses; `main.py` mounts both
    new routers.

### Decisions realised
- **Reject = quarantine, not delete.** The `source` row is intentionally retained (so B3's
  url+hash dedup still blocks the same page from being re-ingested by a future gap loop, per
  the B4 guardrail), while its **chunks are removed** from the vector index so it is no longer
  retrieved or served. This is the cleanest way to honour "rejected items are quarantined so
  they aren't re-ingested" *and* stop serving moderator-rejected content — and it keeps the
  moderation concern out of A4/A6 (no status-aware retrieval needed).
- **The feedback path reuses B2/B3 verbatim** (not a parallel extractor) — exactly the docs/03
  "same pipeline, second source" design, so citizen outcomes grow the KB the same way web
  research does, and inherit the same provenance, dedup, confidence and moderation guarantees.
- **Persist-always / ingest-best-effort** — filing feedback (FR-6) must never fail because of a
  downstream LLM hiccup, so the report write is committed first and the B2→B3 step is guarded.
- **Use-case layer for policy, thin routes** — promote/reject and the intake orchestration live
  in `application/` (testable without HTTP); the routers only translate DTOs ↔ use cases.

### Deltas from the planning docs (and why)
- **`VerificationStatus.REJECTED` is new** (the ER lists three values). Reject genuinely needs a
  4th state: with only `verified`/`auto_gathered`/`pending`, a rejected source could neither
  leave the queue nor avoid being mistaken for never-reviewed. Documented in docs/05.
- **Four store methods, not the three** the Stage-6a note projected. The extra one
  (`delete_chunks_for_source`) is what makes *reject* a real quarantine rather than a label
  flip; it's a single-responsibility companion to "set verification status".
- **Moderation queue reads the DB, not B4's in-state `moderation_queue`.** B4's in-graph queue
  is per-session scratch; the authoritative, cross-session review list is "sources whose
  `verification_status` is `auto_gathered`/`pending`", which is what the admin endpoint serves.
- **`ModerationItemDTO` carries the source fields only** (id, title, url, type, confidence,
  status, dates) — enough for a moderator to decide. Joining each item back to its service name
  is a noted UI enhancement (kept out to keep the port returning pure `Source`).
- **Cache invalidation on promote is deferred to Stage 7** — the `AnswerCache` isn't consulted
  yet (Stage 6a), so there's nothing to invalidate; when the cache short-circuit lands, promote
  should call `invalidate_service`.

### Verified
```
pytest → 118 passed, 4 skipped   (+15: 4 store methods incl. reject-quarantine/keep-row;
                                  3 intake — persist+grow-KB / vague-report-no-write /
                                  ingest-failure-keeps-report; 2 moderation-service policy;
                                  4 chat-API feedback incl. 422 + empty-text skip; 2 chat-API
                                  moderation incl. promote-drops/reject-keeps-row + 404)
ruff   → All checks passed
mypy   → Success, 63 source files (strict)
```
The feedback/moderation API tests drive the **real** routers through `TestClient`; the intake
tests run B2→B3 against a real seeded `ChromaSqliteStore` (so the experience-report write +
dedup are genuine), and the moderation-service tests use bare stores so the de-index assertion
is unambiguous. The 4 skips remain the opt-in live-provider smoke.

### Dependencies added
None — Stage 6b is FastAPI + the existing agents/store. No new runtime or dev dependency.

### What's next
- **Stage 7 — hardening** (split into **7a** observability + **7b** AnswerCache, below).

---

## Stage 7a — Hardening: observability & cross-cutting ✅

**Goal:** make a run **traceable** end-to-end (QA-8) and finish the cross-cutting
guardrail wiring, *without* touching the answering path. Stage 7 is split:
**7a (this section)** = correlation ids + structured logging + optional LangSmith
tracing + a guardrail-coverage pass; **7b** = the AD-12 `AnswerCache` short-circuit
(it adds graph nodes + changes the SSE contract, so it earns its own reviewable unit,
mirroring the 4a/4b and 6a/6b splits).

### Implemented
- **Correlation ids** (`infrastructure/logging.py` + `api/middleware.py`):
  - A `correlation_id_var` `ContextVar` holds the current request's id; a logging
    `Filter` stamps it onto **every** record, and the stdout format gains a
    `%(correlation_id)s` column — so one request's lines (async handler **and** the
    threadpool running the sync graph) share an id and grep together.
  - **`CorrelationIdMiddleware`** is **pure ASGI** (deliberately *not*
    `BaseHTTPMiddleware`, which buffers the body and would break the `/api/chat` SSE
    stream): it reads an inbound `X-Correlation-ID` or mints a fresh one, binds the
    contextvar for the request, and echoes the id on the response. Added **last** in
    `create_app` so it is the outermost layer (covers CORS preflight too).
- **Optional LangSmith tracing** (`configure_tracing`): when `LANGCHAIN_TRACING_V2`
  *and* a `LANGSMITH_API_KEY` are set, the LangChain env vars (current + legacy names)
  are exported at startup so LangGraph traces every run; otherwise a **no-op** (the
  default run stays fully offline / free-tier safe). Wired in the `main.py` lifespan.
- **Guardrail-coverage pass:** the confidence serving gate (AD-8) and the QA-7
  web allow-list are already covered by agent/adapter tests
  (`tests/application/test_a6_action_pack.py`, `tests/adapters/test_web_search.py`);
  Stage 7a adds the observability tests rather than duplicating those.

### Decisions realised
- **Pure-ASGI middleware over `BaseHTTPMiddleware`** — the one correctness trap here is
  that Starlette's `BaseHTTPMiddleware` buffers streaming responses; a pure-ASGI wrapper
  leaves the SSE send path untouched (verified: all chat-SSE tests still pass with the
  middleware in the stack).
- **ContextVar, not parameter threading** — the correlation id reaches deep log calls
  (incl. the threadpool-run graph, since `anyio.to_thread` copies the context) without
  plumbing an id through every function.
- **Tracing is opt-in and key-gated** — observability must never silently exfiltrate
  data or burn quota; tracing turns on only when explicitly configured.

### Deltas from the planning docs (and why)
- **Token streaming stays deferred** (listed under the original Stage 7). It is a
  *feature* (needs `stream_mode="messages"` + provider token streaming), not hardening,
  and the stream already carries complete `step`/`gap`/`action_pack` events; pulling it
  into the hardening stage would add risk for little MVP value. Noted as an enhancement.
- **Cache work moved to 7b** — see the split rationale above.

### Verified
```
pytest → 125 passed, 4 skipped   (+7: correlation filter stamps records / default id /
                                  filter attached by configure_logging / tracing off
                                  unless flag+key / tracing sets env when configured;
                                  2 API — generated id on the response, inbound id echoed)
ruff   → All checks passed
mypy   → Success, 64 source files (strict)
```
The middleware is exercised through the real ASGI stack via `TestClient`; crucially, the
**existing chat-SSE tests still pass**, proving the pure-ASGI correlation layer does not
buffer or break the stream.

### Dependencies added
None — correlation ids use stdlib `contextvars`; the middleware uses Starlette types
(already present via FastAPI); tracing only sets env vars LangChain already reads.

### What's next
- **Stage 7b — AnswerCache (AD-12)** — below.

---

## Stage 7b — Hardening: AnswerCache short-circuit + invalidation ✅

**Goal:** wire AD-12 so an identical, already-answered request (`service + variant +
district`) skips the whole graph and replays the stored answer — saving the scarce
LLM quota (and on a repeat of a gap-filled service, the entire acquisition loop) —
while never serving a stale answer after the KB changes.

### Implemented
- **Cache port in the domain** (`domain/ports/cache.py`, `AnswerCache`): a `Protocol`
  with primitive-arg methods (`get_answer` / `put_answer` / `invalidate_service`) over the
  **serialised answer dict**. Putting the abstraction in `domain/ports` lets the
  `application` graph builder depend on it **without importing `infrastructure`**
  (dependency rule intact); the key (`service_id` + optional `variant_id`/`district`)
  is passed as plain args, so the port carries no infra/transport types.
- **Implementation** (`infrastructure/cache.py`): `AnswerCache` → renamed
  **`InMemoryAnswerCache`** (now clearly "the in-memory impl of the port"); it stores the
  **serialised `answer` dict** (exactly what A6 writes to state and the API serves — no
  domain⇄transport round-trip), keyed by an internal normalized `CacheKey`. Still a
  thread-safe LRU with per-service invalidation.
- **Graph wiring** (`application/graph/builder.py`): three wiring nodes, **no-ops when
  `deps.cache is None`** so the topology and existing tests are unchanged:
  - `cache_lookup` — sits right after resolution (A2 unknown → here; A3 done → here),
    where `service+variant+district` is known. On a hit it writes `answer` (+ citations)
    and routing **ends the run**; on a miss it falls through to A4.
  - `cache_store` — after A6; caches a real served pack (**never a fallback**) for a
    resolved service.
  - `cache_invalidate` — between B3 and B4; drops the service's cached answers after a KB
    upsert. The gap-loop re-entry stays `B4 → A4` so it **always re-retrieves fresh**.
- **SSE** (`api/sse.py`): a cache hit on `cache_lookup` advances the `prepare` pill and
  emits the `action_pack` straight away (so the UI contract is identical to a normal run,
  just without the `lookup` step).
- **Moderation invalidation** (`application/moderation.py` + a new
  `KnowledgeStore.get_service_ids_for_source`): promote (label flips pending→verified) and
  reject (content quarantined) both invalidate the affected service's cache — reject
  captures the service ids **before** de-indexing removes the chunks.
- **Composition root** (`api/runtime.py`): one `InMemoryAnswerCache` is built and shared
  by the graph (`deps.cache`) **and** `ModerationService`, so invalidation reaches the
  same entries the graph populates.

### Decisions realised
- **Cache the serialised dict, not the `ActionPack`** — the graph, SSE and DTO all speak
  the serialised `answer`, so storing that form avoids a fragile reverse-serialiser
  (Decimal/date/enum round-trips) and makes the cache nodes trivial. The port's value type
  is `dict[str, Any]`.
- **Port in `domain`, impl in `infrastructure`** — keeps the builder/application free of
  any infra import while still letting production inject the real cache (inverted
  dependency, like every other adapter).
- **Always-present, self-disabling nodes** — one topology for cached and uncached builds;
  when no cache is injected the nodes return `{}` and behave exactly as before (verified:
  every pre-existing graph/chat test still passes unchanged).
- **Never cache a fallback** — a confidence-gated / gap-exhausted fallback is *not* stored,
  so a later attempt (after the KB grows or a source is verified) can still succeed.

### Deltas from the planning docs (and why)
- **`AnswerCache` (impl) renamed `InMemoryAnswerCache`; `AnswerCache` is now the port.**
  A naming refinement so the abstraction (domain) and the in-memory implementation
  (infrastructure) are distinct. Call-sites (`runtime`, tests) updated.
- **Value type is the serialised dict** (docs/04 / the old code implied `ActionPack`).
  Functionally identical for AD-12; logged as a storage-shape detail (the AD-12 *contract*
  — key + invalidate-on-upsert — is unchanged). docs/04's cache note is updated.
- **Gap-filled (initially-unknown) services cache under `variant_id=None`** the first time
  (the unknown path skips A3, so no variant is pinned); the *next* known-service query
  resolves a variant and re-caches under it. So the very first repeat re-runs A4–A6 (but
  **not** the gap loop — the KB already grew), then subsequent repeats hit. A minor,
  self-correcting edge; noted rather than over-engineered for the MVP.
- **Cross-restart persistence still deferred** — the cache remains in-memory (AD-12's goal
  is short-circuiting within a running server / demo re-runs); a SQLite-backed cache stays
  a documented future option.

### Verified
```
pytest → 132 passed, 4 skipped   (+6: store get_service_ids_for_source; 2 moderation cache
                                  invalidation (promote/reject); 2 graph — cache hit skips A6
                                  / fallback not cached; 1 API — repeat query served from cache,
                                  proven by the missing `lookup` pill on the 2nd run)
ruff   → All checks passed
mypy   → Success, 65 source files (strict)
```
The graph cache tests run the **real compiled graph** and assert the LLM step-generation
call count does *not* increase on the cached run (A6 genuinely skipped); the API test proves
the same end-to-end over SSE (a cache hit omits the `lookup` pill). The real `build_runtime`
composition root was also smoke-built from scratch (graph compiles; the cache instance is
shared by the graph and moderation).

### Dependencies added
None — AD-12 uses stdlib `collections.OrderedDict` + `threading`; the port is a `Protocol`.

### Backend stages complete
Stages 0–7 are done. The backend boots (`/health`), serves the full doc/11 API contract
(chat SSE + resume, action-pack fetch, experience reports, moderation), self-expands its KB
under the confidence gate, caches answers (AD-12), and is correlation-id traceable (QA-8).
**Noted enhancements (not blockers):** per-token streaming (`stream_mode="messages"`),
full-page web fetch in B1, vector service-matching in A2, and a SQLite-backed cache.
