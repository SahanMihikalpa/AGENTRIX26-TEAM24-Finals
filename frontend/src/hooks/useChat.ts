"use client";

import { useCallback, useReducer, useRef } from "react";
import type { ActionPack, AgentStep, ChatEvent, Clarify, GapState, Message } from "@/core/domain";
import { getChatGateway } from "@/infra/gateways";
import { freshSteps } from "@/lib/constants";
import { genId } from "@/lib/id";

interface State {
  messages: Message[];
  steps: AgentStep[];
  clarify: Clarify | null;
  gap: GapState | null;
  actionPack: ActionPack | null;
  isRunning: boolean;
  error: string | null;
  nextId: number;
}

const initialState: State = {
  messages: [],
  steps: freshSteps(),
  clarify: null,
  gap: null,
  actionPack: null,
  isRunning: false,
  error: null,
  nextId: 0,
};

type Action =
  | { kind: "reset" }
  | { kind: "newTurn" }
  | { kind: "addUser"; text: string }
  | { kind: "running" }
  | { kind: "event"; event: ChatEvent };

/** Finalize any in-flight streaming bubble (any non-token event commits it). */
function settle(messages: Message[]): Message[] {
  const last = messages[messages.length - 1];
  if (last && last.role === "assistant" && last.streaming) {
    return [...messages.slice(0, -1), { ...last, streaming: false }];
  }
  return messages;
}

function reducer(state: State, action: Action): State {
  switch (action.kind) {
    case "reset":
      return { ...initialState, steps: freshSteps() };

    case "newTurn":
      // A follow-up is a fresh run of the pipeline, so the pills start over and
      // the previous Action Pack stops being the current answer. The transcript
      // is kept — that is the conversation. (Answering a ClarifyCard is *not* a
      // new turn: it resumes the run in flight, whose earlier pills are still
      // true and are never re-emitted.)
      return {
        ...settleState(state),
        steps: freshSteps(),
        actionPack: null,
        clarify: null,
        gap: null,
        error: null,
      };

    case "addUser":
      return {
        ...settleState(state),
        messages: [...state.messages, { id: `m${state.nextId}`, role: "user", text: action.text }],
        // Sending a message (incl. answering a clarification) dismisses the pending
        // question card and the previous turn's gap banner.
        clarify: null,
        gap: null,
        nextId: state.nextId + 1,
      };

    case "running":
      return { ...state, isRunning: true, error: null };

    case "event":
      return applyEvent(state, action.event);
  }
}

function settleState(state: State): State {
  return { ...state, messages: settle(state.messages) };
}

function applyEvent(state: State, e: ChatEvent): State {
  switch (e.type) {
    case "token": {
      const last = state.messages[state.messages.length - 1];
      if (last && last.role === "assistant" && last.streaming) {
        const updated = { ...last, text: last.text + e.text };
        return { ...state, messages: [...state.messages.slice(0, -1), updated] };
      }
      return {
        ...state,
        messages: [...state.messages, { id: `m${state.nextId}`, role: "assistant", text: e.text, streaming: true }],
        nextId: state.nextId + 1,
      };
    }

    case "message":
      return {
        ...settleState(state),
        messages: [...settle(state.messages), { id: `m${state.nextId}`, role: "assistant", text: e.text }],
        nextId: state.nextId + 1,
      };

    case "step":
      return {
        ...settleState(state),
        steps: state.steps.map((s) =>
          s.id === e.id ? { ...s, status: e.status, note: e.note ?? s.note } : s,
        ),
      };

    case "clarify":
      // Record the question as an assistant turn so it stays in the transcript.
      // Otherwise, once answered, only the citizen's reply ("Galle") would remain
      // and the conversation would read as an answer with no visible question.
      return {
        ...state,
        messages: [
          ...settle(state.messages),
          { id: `m${state.nextId}`, role: "assistant", text: e.question },
        ],
        nextId: state.nextId + 1,
        isRunning: false,
        clarify: { question: e.question, options: e.options, allowFreeText: e.allowFreeText },
      };

    case "gap":
      return { ...settleState(state), gap: { phase: e.phase, text: e.text } };

    case "actionPack":
      // Defensive: an answer arriving as an Action Pack also clears any pending question.
      return { ...settleState(state), clarify: null, actionPack: e.pack };

    case "done":
      return { ...settleState(state), isRunning: false };

    case "error":
      return { ...settleState(state), isRunning: false, error: e.message };
  }
}

export interface UseChat {
  sessionId: string;
  messages: Message[];
  steps: AgentStep[];
  clarify: Clarify | null;
  gap: GapState | null;
  actionPack: ActionPack | null;
  isRunning: boolean;
  error: string | null;
  start: (query: string) => void;
  /** A new question or follow-up — resets the progress pills, keeps the transcript. */
  send: (text: string) => void;
  /** A reply to a ClarifyCard — resumes the run in flight. */
  answer: (text: string) => void;
}

export function useChat(): UseChat {
  const [state, dispatch] = useReducer(reducer, initialState);

  const sessionRef = useRef<string>();
  if (!sessionRef.current) sessionRef.current = genId();

  const gatewayRef = useRef(getChatGateway());

  const run = useCallback((message: string) => {
    dispatch({ kind: "running" });
    void gatewayRef.current
      .send({ sessionId: sessionRef.current!, message }, (event) => dispatch({ kind: "event", event }))
      .catch((err: unknown) =>
        dispatch({ kind: "event", event: { type: "error", message: err instanceof Error ? err.message : "Something went wrong." } }),
      );
  }, []);

  const start = useCallback(
    (query: string) => {
      dispatch({ kind: "reset" });
      dispatch({ kind: "addUser", text: query });
      run(query);
    },
    [run],
  );

  const send = useCallback(
    (text: string) => {
      dispatch({ kind: "newTurn" });
      dispatch({ kind: "addUser", text });
      run(text);
    },
    [run],
  );

  const answer = useCallback(
    (text: string) => {
      dispatch({ kind: "addUser", text });
      run(text);
    },
    [run],
  );

  return {
    sessionId: sessionRef.current!,
    messages: state.messages,
    steps: state.steps,
    clarify: state.clarify,
    gap: state.gap,
    actionPack: state.actionPack,
    isRunning: state.isRunning,
    error: state.error,
    start,
    send,
    answer,
  };
}
