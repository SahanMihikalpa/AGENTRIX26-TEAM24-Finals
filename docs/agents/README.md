# Agents

Per-agent documentation. Each file follows the same template:
**Issue it solves · Single responsibility · Inputs→Outputs · Step logic · Decisions & tech ·
Alternatives · Why optimal · Guardrails · State touched.**

## Roster

| ID | Agent | Team | Type | Doc |
|---|---|---|---|---|
| — | Supervisor / Router | — | LangGraph router | [00-supervisor.md](00-supervisor.md) |
| A1 | Intake & Intent | Answering | LLM (structured) | [a1-intake-intent.md](a1-intake-intent.md) |
| A2 | Service Identifier | Answering | LLM + retrieval | [a2-service-identifier.md](a2-service-identifier.md) |
| A3 | Clarification | Answering | LLM + interrupt | [a3-clarification.md](a3-clarification.md) |
| A4 | Retrieval (RAG) | Answering | Vector + SQL | [a4-retrieval.md](a4-retrieval.md) |
| A5 | Gap Grader | Answering | LLM (cheap) | [a5-gap-grader.md](a5-gap-grader.md) |
| A6 | Action-Pack Generator | Answering | LLM (structured) | [a6-action-pack-generator.md](a6-action-pack-generator.md) |
| B1 | Research | Acquisition | Tool-using | [b1-research.md](b1-research.md) |
| B2 | Extract & Curate | Acquisition | LLM (structured) | [b2-extract-curate.md](b2-extract-curate.md) |
| B3 | KB-Updater | Acquisition | Embed + upsert | [b3-kb-updater.md](b3-kb-updater.md) |
| B4 | Moderation gate | Acquisition | Rules + human | [b4-moderation.md](b4-moderation.md) |

## Interaction summary
`Supervisor → A1 → A2 → A3 → A4 → A5`. If `A5 = SUFFICIENT → A6` (answer). If `A5 = GAP →
B1 → B2 → B3 → (B4) → back to A4`, bounded by `N` acquisition loops. Experience reports enter at
`B2`. All agents share one persisted `GraphState` (see [../02-architecture.md](../02-architecture.md)).

## Design principle: one responsibility per agent
Splitting by responsibility keeps each node small, independently testable, and individually
explainable in the technical defense. Where free-tier call budget matters, adjacent **LLM** nodes
(e.g. A1+A2) may be **merged into one call** at implementation time without changing the logical
design.
