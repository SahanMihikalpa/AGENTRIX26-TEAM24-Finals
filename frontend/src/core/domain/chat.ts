/**
 * Conversation domain — the projection of the LangGraph agent run into the UI.
 * The ChatEvent union IS the SSE contract (docs/11 §2).
 */
import type { ActionPack } from "./actionPack";

export type Role = "user" | "assistant";

export interface Message {
  id: string;
  role: Role;
  text: string;
  /** true while tokens are still streaming into this bubble */
  streaming?: boolean;
}

/** The five progress pills, mapped to graph nodes (docs/11 §1). */
export type AgentStepId = "understand" | "find" | "ask" | "lookup" | "prepare";
export type AgentStepStatus = "pending" | "active" | "done";

export interface AgentStep {
  id: AgentStepId;
  label: string;
  status: AgentStepStatus;
  /** optional sub-note, e.g. the gap-fill message on `lookup` */
  note?: string;
  /** plain-language explanation of the step, revealed when a pill is expanded */
  detail?: string;
}

/** A3 clarification card. */
export interface Clarify {
  question: string;
  options: string[];
  allowFreeText: boolean;
}

/** Self-expanding RAG surfacing (B1→B3). */
export interface GapState {
  phase: "researching" | "updated";
  text: string;
}

/**
 * ChatEvent — emitted by any ChatGateway (mock or real SSE).
 * The useChat hook reduces these into UI state.
 */
export type ChatEvent =
  | { type: "step"; id: AgentStepId; status: Exclude<AgentStepStatus, "pending">; note?: string }
  | { type: "token"; text: string }
  | { type: "message"; role: "assistant"; text: string }
  | { type: "clarify"; question: string; options: string[]; allowFreeText: boolean }
  | { type: "gap"; phase: GapState["phase"]; text: string }
  | { type: "actionPack"; pack: ActionPack }
  | { type: "done" }
  | { type: "error"; message: string };
