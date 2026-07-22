# Supervisor / Router

**Team:** — (top level) · **Type:** LangGraph conditional router

## Issue it solves
Something must decide *what happens next* at each turn — continue the interview, retrieve, answer,
or divert into knowledge acquisition — without hard-coding a single rigid path, and without letting
agents call each other chaotically.

## Single responsibility
Own the control flow of the graph: choose the next node from the current `GraphState` and enforce
global guardrails (loop cap, fallback).

## Inputs → Outputs
- **Input:** `GraphState`.
- **Output:** the name of the next node (a routing decision), or `END`.

## Step logic
1. If `pending_question` is set → wait for user input (interrupt), then route to `A3`.
2. If `service_id` missing → route to `A1/A2`.
3. If `variant_id`/required slots missing → route to `A3`.
4. After retrieval, branch on `grade`: `SUFFICIENT → A6`; `GAP` and `acquisition_loops < N → B1`;
   `GAP` and loops exhausted → `A6` in **fallback mode**.
5. After `B3/B4` → route back to `A4`.

## Decisions & technologies
- **Decision:** implement routing as **LangGraph conditional edges** driven mostly by explicit state
  (rules), with the LLM only where genuine ambiguity exists.
- **Tech:** `langgraph.StateGraph`, `add_conditional_edges`.

## Alternatives
| Alternative | Why not |
|---|---|
| Pure LLM "supervisor agent" deciding every hop | More tokens, less determinism, harder to defend; wasteful on free tier. |
| Hard-coded linear flow | Cannot express the dynamic gap loop. |

## Why optimal
State-driven routing is **deterministic, cheap, and traceable** — every transition is inspectable,
which is ideal for debugging and the technical defense, and it spends zero LLM quota on plumbing.

## Guardrails
Enforces `acquisition_loops ≤ N`; guarantees a terminal answer (fallback) so the graph never hangs.

## State touched
Reads all fields; writes `acquisition_loops`, routing metadata.
