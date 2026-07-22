# 01 · Problem, Domain & Solution

## Chosen domain
**Government & Citizen Services** (AgenTriX 2026 domain #3), Sri Lanka.

## Problem statement
Accessing a government service in Sri Lanka suffers from deep **information asymmetry**.
For any service — land deed transfer, NIC renewal, business registration, birth-certificate
correction, passports — the exact documents, fees, the correct office, the authorised officer,
and the processing sequence are known mainly to the counter staff. These requirements **change
over time, vary by district, and are almost never consolidated in one current place online**.
Official sites are incomplete or outdated.

The result: citizens make **3–4 repeated failed visits**, each time discovering one more missing
document. The cost in time, money and frustration falls hardest on **rural citizens** (repeated
transport costs) and those with **low formal-language literacy**. There is no single, current,
plain-language, **personalised** source that tells a citizen exactly what to do for *their*
specific case.

### Why it is genuinely hard (and why naive solutions fail)
- **The domain is huge** — hundreds of services across many departments. A knowledge base cannot
  be fully built up front, and it goes stale.
- **Processes branch** — e.g. land transfer differs for *inheritance vs. sale vs. gift*;
  requirements differ by *district*. A generic answer is wrong for the individual.
- **Trust matters** — a confidently wrong answer about a government process wastes a real trip.
  Answers must be grounded and attributable.

## Solution outline — *GovGuide*
An **agentic AI citizen-services navigator**. A citizen describes their need in plain language.
The system then:

1. **Identifies the correct service** from the natural-language request.
2. Runs a short **clarifying interview** — asks only the questions needed to pin the exact
   sub-case (branch + district).
3. **Retrieves the current requirements** (documents, fees, office + officer, expected timeline)
   from a curated knowledge base, **with a cited source and `last-verified` date** for every fact.
4. **If the knowledge base has a gap**, autonomous agents **research, curate, and write the answer
   back** to the knowledge base (the [self-expanding RAG](03-self-expanding-rag.md) loop), then
   answer.
5. Generates a **personalised, printable Action Pack**: exact document checklist for *their* case,
   total estimated cost (fees + transport), step-by-step office sequence, and the right office.
6. **Self-improves** — after a visit, citizens submit a short *experience report* that (after
   moderation) updates the knowledge base.

### Scope for the 12 hours
Three flagship services done excellently, chosen to showcase both hero features:

| Service | In demo as | Why |
|---|---|---|
| **Land Deed Transfer** | Seeded | Best showcase of the branching **clarifying interview** (inheritance / sale / gift) |
| **NIC services** | Seeded | High volume, relatable, simple |
| **Business Name Registration** | **Live gap-fill** | Unseen at start → showcases the **self-expanding RAG** live |

## Value & commercial model (for the pitch — 40%)
- **B2G** — license to ICTA / government as the citizen-facing front-end over existing portals;
  cuts counter congestion and repeat visits.
- **B2C freemium** — free guidance; premium for document-prep help, appointment booking, an
  agent/broker marketplace.
- **Data product** — anonymised analytics on service bottlenecks for policy makers.
- **Defensible moat** — the self-expanding, crowd-verified knowledge base improves with every
  query and experience report (network effect).
- **Roadmap** — Sinhala/Tamil + voice for low-literacy users; replicable to other South-Asian
  bureaucracies.

## Mapping to the AgenTriX rubric
| Phase | Weight | How GovGuide scores |
|---|---|---|
| Ideation | 30% | Self-expanding RAG + agentic clarifying interview = original, strong problem–solution fit |
| Code Review | 30% | Clean LangGraph graph, efficient free-tier AI workflow, grounded/cited RAG |
| Pitching | 40% | Real equity impact, clear B2G/B2C model, defensible data moat, live demo of the loop |
