# 08 · Interim Submission (T+2) — Initial Plan

> The four required points, ready to submit. Detail lives in the other docs.

## 1. Problem statement
Accessing a government service in Sri Lanka suffers from deep **information asymmetry**. For any
service (land deed transfer, NIC renewal, business registration, birth-certificate correction,
passports), the exact documents, fees, correct office, authorised officer, and processing sequence
are known mainly to counter staff — and they **change over time and vary by district**, and are
almost never consolidated online. Citizens make **3–4 repeated failed visits**, each time finding a
new missing document. The cost in time, money and frustration falls hardest on **rural and
low-literacy citizens**. No single, current, plain-language, **personalised** source tells a citizen
exactly what to do for *their* specific case.

## 2. Chosen domain
**Government & Citizen Services** (Domain #3).

## 3. Solution outline — *GovGuide*
An **agentic AI citizen-services navigator**. The citizen describes their need in plain language; the
system (a) identifies the correct service, (b) runs a short **clarifying interview** to pin the exact
sub-case (branch + district), (c) retrieves current requirements — documents, fees, the right office,
timeline — **with cited, dated sources**, and (d) produces a **personalised, printable Action Pack**
(checklist + total cost + office + visit sequence).

Because the government domain is too large to pre-index, the knowledge base is **self-expanding**:
when a query hits a gap, autonomous agents **research, curate, and write the answer back** to the
knowledge base, then answer — improving for every future user. Scope for the 12 hours: 3 flagship
services (Land Deed Transfer, NIC, Business Name Registration).

## 4. How we plan to apply AI
- **Agentic orchestration (LangGraph)** — a **hierarchical multi-agent system**: a Supervisor routes
  between an **Answering team** (intake → service-ID → clarification → retrieval → gap-grading →
  action-pack generation) and a **Knowledge-Acquisition team** (research → curate → KB-update →
  moderate). Multi-step reasoning with persisted state, not a single prompt.
- **Self-expanding RAG (Corrective-RAG + lazy ingestion)** — a grader detects insufficient retrieval
  and triggers on-demand acquisition (local source pool → live web fallback), with provenance and a
  bounded retry loop.
- **Grounded, cited generation** — every fact carries a source URL and `last-verified` date to build
  trust and curb hallucination.
- **Structured outputs (Pydantic)** — the Action Pack is a validated schema rendered to a printable
  PDF.
- **100% free tier** — Gemini Flash (LLM) + local embeddings + ChromaDB + SQLite; no paid APIs, no
  no-code tools.

---
*Working name "GovGuide" is provisional. Current scope is English-only; Sinhala/Tamil + voice are on
the roadmap.*
