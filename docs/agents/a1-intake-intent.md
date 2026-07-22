# A1 · Intake & Intent

**Team:** Answering · **Type:** LLM (structured output)

## Issue it solves
A citizen's raw request is messy and underspecified ("I need to sort out my dad's land"). Downstream
agents need a clean, structured starting point: what is the user broadly trying to do, and what
entities did they already mention?

## Single responsibility
Normalise the free-text request and extract a structured **intent + entities**. (No language
detection — current scope is **English-only**; Sinhala/Tamil is a roadmap item.)

## Inputs → Outputs
- **Input:** `user_query` (English free text).
- **Output (Pydantic):**
  ```json
  {
    "normalized_query": "transfer inherited land deed to my name",
    "service_guess": "land_deed_transfer",
    "entities": { "district": null, "relationship": "inheritance" },
    "ambiguous": false
  }
  ```

## Step logic
1. Clean/normalise the query.
2. Extract a coarse `service_guess` + any entities (district, relationship, document type).
3. Flag `ambiguous` if the request could map to multiple services.

## Decisions & technologies
- **Decision:** one **structured LLM call** (Gemini Flash) returning a Pydantic-validated object.
- **Tech:** `langchain-google-genai` + Pydantic v2 structured output.
- **Efficiency:** A1 and **A2** may be **merged into a single call** to save free-tier quota.

## Alternatives
| Alternative | Why not |
|---|---|
| Regex / keyword intent rules | Brittle across paraphrase; citizens don't use canonical terms. |
| Dedicated NLU service (Rasa/Dialogflow) | Heavy setup; Dialogflow paid tiers; overkill for 12 h. |

## Why optimal
An LLM handles paraphrase and implicit entities robustly in one cheap call, and structured output
keeps the rest of the graph deterministic.

## Guardrails
If `ambiguous`, defer the decision to A2/A3 rather than guessing; never fabricate entities.

## State touched
Writes `intent`, partially fills `slots` (e.g. district/relationship if stated).
