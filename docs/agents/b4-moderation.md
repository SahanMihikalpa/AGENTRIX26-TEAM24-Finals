# B4 · Moderation Gate

**Team:** Knowledge Acquisition · **Type:** Rules + human-in-the-loop *(optional for MVP)*

## Issue it solves
Auto-gathered knowledge (and citizen experience reports) can be wrong or outdated. Serving it as
"official truth" is risky. There must be a way to keep it **usable but clearly provisional** until a
human confirms it.

## Single responsibility
Govern the promotion of knowledge from `auto_gathered`/`pending` → `verified`, and surface low-
confidence items to a moderator.

## Inputs → Outputs
- **Input:** newly written records (with `confidence`, `verification_status`).
- **Output:** a moderation queue entry; on approval, `verification_status = verified`.

## Step logic
1. Items below a confidence threshold (or from web fallback / experience reports) → queue as
   `pending`.
2. They remain **retrievable and answerable**, but answers carry a "pending verification" label.
3. A moderator approves/rejects; approval promotes to `verified` (and removes the label for future
   users).

## Decisions & technologies
- **Decision:** **serve-but-label** rather than block — never hide useful info, but never overstate
  certainty.
- **Tech:** SQLite status field + a minimal moderator view; LangGraph human-in-the-loop interrupt
  (post-MVP).

## Alternatives
| Alternative | Why not |
|---|---|
| Auto-trust everything | Risk of confidently serving wrong government info. |
| Block until verified | Defeats the on-demand value; citizen gets nothing now. |

## Why optimal
"Serve-but-label" preserves immediate usefulness while protecting trust and giving a clean path to
crowd/human verification — directly enabling the **self-improving data moat**.

## Guardrails
Provisional answers are always labelled + cited; rejected items are quarantined so they aren't re-
ingested.

## State touched
Updates `SOURCE.verification_status`; influences the `verification` label A6 shows.

## MVP note
For the 12-hour build this can be a **status flag + simple queue view**; the full interrupt-driven
console is roadmap.
