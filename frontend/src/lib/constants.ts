import type { AgentStep } from "@/core/domain";

/** Fresh set of progress pills for a new run (maps to graph nodes, docs/11 §1).
 *  Each carries a plain-language `detail` shown when the pill is expanded — it
 *  makes the agent's work legible instead of a black box. */
export function freshSteps(): AgentStep[] {
  return [
    {
      id: "understand",
      label: "Understanding your request",
      status: "pending",
      detail:
        "Reading your words to work out what you actually need — in plain language, no forms or codes.",
    },
    {
      id: "find",
      label: "Finding the service",
      status: "pending",
      detail: "Matching your request to the exact government service that handles it.",
    },
    {
      id: "ask",
      label: "Asking what's needed",
      status: "pending",
      detail: "Checking whether we need one small detail from you so the checklist fits your case.",
    },
    {
      id: "lookup",
      label: "Looking up requirements",
      status: "pending",
      detail: "Pulling the documents, fees and office details from the official source for this service.",
    },
    {
      id: "prepare",
      label: "Preparing your checklist",
      status: "pending",
      detail: "Assembling your Action Pack — with the source and date behind every line.",
    },
  ];
}

/**
 * Landing-page quick actions.
 *
 * Every entry here is a **promise**: click it and you get a real checklist with
 * documents, fees and an office — not the "we couldn't verify this" fallback. So
 * each `query` is one that has been run end-to-end against the backend and
 * confirmed to resolve to a service the knowledge base has complete, verified
 * facts for. Today that is exactly two services: Land Deed Transfer &
 * Registration, and NIC Issuance.
 *
 * **Before adding one:** run the query through `POST /api/chat`, answer the A3
 * interview, and check the Action Pack comes back with `fallback: false` and a
 * non-empty `documents` list. Phrasing matters: A2 matches on keywords, so a
 * query that echoes a thin crawled catalog entry can still route away from the
 * curated service that covers it.
 *
 * The four below deliberately land on four different variants, so the demo shows
 * the A3 interview pinning a real branch rather than the same answer each time.
 */
export const SUGGESTIONS: { label: string; query: string }[] = [
  {
    // → Land Deed Transfer & Registration (sale-transfer): 3 documents, 2 fees
    label: "Transfer my late father’s land to my name",
    query: "Transfer my late father’s land to my name",
  },
  {
    // → NIC Issuance (first-time): 4 documents, 1 fee
    label: "Apply for my first National Identity Card",
    query: "Apply for my first National Identity Card",
  },
  {
    // → Land Deed Transfer & Registration (certified-copy): 2 documents, 2 fees
    label: "Get a certified copy of my land deed",
    query: "Get a certified copy of my land deed",
  },
  {
    // → NIC Issuance (english-translation): 3 documents, 1 fee
    label: "Get an English translation of my NIC",
    query: "Get an English translation of my NIC",
  },
];
