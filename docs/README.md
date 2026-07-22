# GovGuide — Documentation

> **GovGuide** is an agentic AI navigator for Sri Lankan government & citizen services.
> Describe what you need in plain language; the system identifies the correct service,
> asks only the questions needed to pin your exact case, retrieves the current
> requirements (with cited, dated sources), and produces a printable **Action Pack**
> (document checklist, fees, the right office, and the step sequence).
>
> Built for **AgenTriX 2026** (ComES, University of Ruhuna) — a 12-hour agentic AI / RAG hackathon.

## What makes it different
1. **Truly agentic** — a hierarchical multi-agent system (LangGraph), not a single chatbot.
2. **Self-expanding RAG** — the knowledge base cannot cover the whole government domain up front, so it **grows on demand**: when a query hits a gap, agents research the answer, curate it, and write it back to the knowledge base for every future user.
3. **Trustworthy** — every fact is grounded in a cited source with a `last-verified` date.

## Document map

| Doc | Purpose | Feeds report deliverable |
|---|---|---|
| [00-architecture-drivers.md](00-architecture-drivers.md) | Quality attributes (the drivers) + dominant driver per container | **Architecture** / defense |
| [01-problem-and-solution.md](01-problem-and-solution.md) | Problem, domain, solution outline, value & commercial model | Pitch |
| [02-architecture.md](02-architecture.md) | Hybrid styles, C4 L1/L2/L3 views, ports & patterns, state | **Architecture diagram** |
| [03-self-expanding-rag.md](03-self-expanding-rag.md) | The knowledge-gap loop (Corrective-RAG + lazy ingestion) | Architecture / Pitch |
| [04-tech-stack-and-decisions.md](04-tech-stack-and-decisions.md) | Full stack with decision · alternatives · why-optimal; hexagonal layout | Code review |
| [05-data-model.md](05-data-model.md) | Entities, schema, ER diagram, confidence serving gate | **ER diagram** |
| [06-use-cases.md](06-use-cases.md) | Actors, use cases, scenarios | **Use-case diagram** |
| [07-execution-plan.md](07-execution-plan.md) | 12-hour build sequence + repo structure | — |
| [08-initial-plan-submission.md](08-initial-plan-submission.md) | The T+2 interim submission (4 points) | Interim submission |
| [09-architecture-decisions.md](09-architecture-decisions.md) | ADR log — every hard-to-reverse decision with its trade-off | Code review / defense |

| [10-backend-implementation.md](10-backend-implementation.md) | As-built backend log — what each stage actually implemented + deltas from plan | Code review |

| [11-security-and-cryptography.md](10-security-and-cryptography.md) | Threat model (STRIDE + OWASP LLM + RAG), crypto usage, controls, PDPA | Code review / defense |

| [12-frontend-architecture.md](11-frontend-architecture.md) | API/SSE contract, hexagonal folder structure, components, stage-wise build | Code review |


| [agents/](agents/README.md) | Per-agent documentation (issue · I/O · decisions · alternatives · optimality) | Technical defense |

## Conventions used in every doc
Each non-trivial decision is documented as:
- **Decision & technology** — what we chose and the tool/library.
- **Driver** — the quality attribute it serves ([00-architecture-drivers.md](00-architecture-drivers.md)), *not* "because it's cool".
- **Alternatives** — other viable options.
- **Why optimal** — reasoning, given the quality attributes and within our 4 project constraints (12 h · free-tier only · no no-code · must be agentic/RAG).
- **Trade-off** — what the choice costs (logged for hard-to-reverse decisions in [09-architecture-decisions.md](09-architecture-decisions.md)); every architectural choice costs something.

## Status
- Scope (current): **English-only**. Sinhala/Tamil deferred to the roadmap.
- Phase: **backend implementation in progress** (stage-by-stage; see
  [10-backend-implementation.md](10-backend-implementation.md)). Done: **Stage 0 — scaffold & tooling**
  (`backend/` hexagonal skeleton, conda env, FastAPI `/health`, green `pytest`/`ruff`/`mypy`).
