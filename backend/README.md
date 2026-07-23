# GovGuide — Backend

Agentic AI navigator for Sri Lankan government & citizen services. This is the
**FastAPI backend**: a hierarchical multi-agent system (LangGraph) over a
self-expanding RAG knowledge base, laid out in a **hexagonal (ports & adapters)**
architecture. See [`../docs/`](../docs/README.md) for the full design and
[`../docs/10-backend-implementation.md`](../docs/10-backend-implementation.md)
for the as-built log.

## Prerequisites

- [Conda](https://docs.conda.io/) (Anaconda or Miniconda)

## Setup

```bash
# from backend/
conda env create -f environment.yml
conda activate govguide
```

This creates a Python 3.11 environment and installs the project in editable mode
with dev tools. As later stages add dependencies, refresh with:

```bash
pip install -e .[dev]
```

Pip-only / deploy (no conda): `pip install -r requirements.txt` installs the pinned runtime set.

> The first real embedding call downloads the `bge-base-en-v1.5` model (~440 MB) to the
> HuggingFace cache. Tests use a torch-free fake embedder, so `pytest` stays fast.

## Run

```bash
# from backend/, with the env active
uvicorn app.api.main:app --reload --port 8000
```

Then check the health probe: <http://localhost:8000/health> → `{"status":"ok",...}`.

## Quality gates

```bash
pytest          # tests
ruff check .    # lint
mypy            # type-check (strict)
```

## Layout (hexagonal — dependencies point inward)

```
app/
├── domain/          # PURE — entities + ports (interfaces). No framework imports.
├── application/     # USE CASES — LangGraph graph + agents. Depends only on domain.ports.
├── adapters/        # IMPLEMENTATIONS of ports (LLM, embeddings, knowledge, web, parser).
├── infrastructure/  # Cross-cutting: config, logging, LLM gateway, cache.
└── api/             # DELIVERY: FastAPI routers, SSE, Pydantic DTOs, DI wiring.
data/source_pool/    # Pre-collected gazettes/circulars/PDFs (provided later).
tests/               # Mirrors app/; pure layers tested with fakes.
```

**The dependency rule:** `domain` imports nothing; `application` imports only
`domain.ports`; `adapters` implement those ports; `api` wires concrete adapters
in at startup. Swapping a provider (Gemini→Groq, Chroma→pgvector) touches only
`adapters/`.

## Build status

Implemented stage by stage; see the as-built log in
[`../docs/10-backend-implementation.md`](../docs/10-backend-implementation.md).
Current: **Stage 6b — feedback + moderation** (`POST /api/experience-reports` feeds
citizen feedback through the same B2→B3 pipeline; `GET /api/moderation/queue` +
`POST /api/moderation/{source_id}/promote|reject` drive the B4 review loop). This
completes the API contract; **Stage 7 — hardening** next.
