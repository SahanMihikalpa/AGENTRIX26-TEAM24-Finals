"use client";

import { useState } from "react";

/**
 * The message box that keeps a session going.
 *
 * Without it a session was worth exactly one run: the only way to say anything
 * was to answer a ClarifyCard, and once the Action Pack arrived the conversation
 * was over. Follow-ups ("what about Kandy?", "and if it's a gift instead?") are
 * resolved server-side against the session's history.
 *
 * Hidden while the agent is asking a structured question — the ClarifyCard owns
 * that turn, and two inputs competing for the same answer is a trap.
 */
export function Composer({
  onSend,
  disabled,
  busy,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
  busy: boolean;
}) {
  const [text, setText] = useState("");

  function submit() {
    const message = text.trim();
    if (!message || disabled) return;
    setText("");
    onSend(message);
  }

  return (
    <div className="gg-noprint border-t border-paper-border bg-[rgba(244,242,236,.95)] backdrop-blur">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="mx-auto flex max-w-[740px] items-stretch gap-2 px-5 py-3.5"
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled}
          aria-label="Ask a follow-up"
          placeholder={busy ? "Working on it…" : "Ask a follow-up, or start a new question…"}
          className="min-w-0 flex-1 rounded-xl border border-[#d9d3c6] bg-white px-4 py-3 text-[15px] text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-brand disabled:bg-paper-sunken disabled:text-ink-faint"
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          aria-label="Send"
          className="flex h-[46px] w-[46px] flex-none items-center justify-center rounded-xl bg-brand transition-colors hover:bg-brand-hover disabled:bg-[#d9d3c6]"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path
              d="M5 12h14M13 6l6 6-6 6"
              stroke="#fff"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </form>
    </div>
  );
}
