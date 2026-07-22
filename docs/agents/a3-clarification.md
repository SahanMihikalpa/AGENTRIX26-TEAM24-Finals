# A3 · Clarification

**Team:** Answering · **Type:** LLM + LangGraph interrupt (human-in-the-loop)

## Issue it solves
Government processes **branch**: land transfer differs for inheritance vs. sale vs. gift, and
requirements vary by district. A generic answer is wrong for the individual — this is the exact pain
("discovering a new missing document on visit 3"). The agent must ask only the questions needed to
pin the **single correct variant**.

## Single responsibility
Drive a minimal slot-filling interview to resolve `service_id` → `variant_id` + required context
(e.g. district).

## Inputs → Outputs
- **Input:** `service_id`, the service's `SERVICE_VARIANT` set + required slots, current `slots`.
- **Output:** either a `pending_question` (back to the UI) or a resolved `variant_id` + complete
  `slots`.

## Step logic
1. Look up the variant-defining slots for the service (e.g. `relationship`, `district`).
2. Skip slots already filled by A1.
3. Ask the **single most informative** missing question → set `pending_question`, pause (interrupt).
4. On user answer, update `slots`; repeat until the variant is uniquely determined.

## Decisions & technologies
- **Decision:** model the interview as **LangGraph interrupts** over persisted state, asking one
  question at a time.
- **Tech:** `langgraph` interrupt + `SqliteSaver` checkpoint; Gemini to phrase/select the next
  question; UI renders question cards.

## Alternatives
| Alternative | Why not |
|---|---|
| Ask everything up front in a form | Worse UX; asks irrelevant questions for the chosen branch. |
| Don't clarify; answer generically | Reproduces the real-world failure (wrong docs for the case). |

## Why optimal
Minimal, adaptive questioning is the feature that makes the answer **correct the first time** — the
whole product thesis — and interrupts make it resumable and demo-friendly.

## Guardrails
Cap total questions per session; if unanswered, default to the most common variant and **state the
assumption** in the Action Pack.

## State touched
Writes `slots`, `variant_id`, `pending_question`.
