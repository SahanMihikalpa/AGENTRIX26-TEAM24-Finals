import type { AgentStep } from "@/core/domain";

/** Fresh set of progress pills for a new run (maps to graph nodes, docs/11 §1). */
export function freshSteps(): AgentStep[] {
  return [
    { id: "understand", label: "Understanding your request", status: "pending" },
    { id: "find", label: "Finding the service", status: "pending" },
    { id: "ask", label: "Asking what's needed", status: "pending" },
    { id: "lookup", label: "Looking up requirements", status: "pending" },
    { id: "prepare", label: "Preparing your checklist", status: "pending" },
  ];
}

export const SUGGESTIONS: { label: string; query: string }[] = [
  { label: "Transfer my late father’s land to my name", query: "Transfer my late father’s land to my name" },
  { label: "Register a new business name", query: "Register a new business name" },
  { label: "Get a certified copy of my land deed", query: "Get a certified copy of my land deed" },
  { label: "Start a small business", query: "Start a small business" },
];
