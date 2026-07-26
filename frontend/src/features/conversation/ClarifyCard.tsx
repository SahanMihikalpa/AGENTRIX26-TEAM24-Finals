"use client";

import { useState } from "react";
import type { Clarify } from "@/core/domain";
import { cn } from "@/lib/cn";

export function ClarifyCard({ clarify, onAnswer }: { clarify: Clarify; onAnswer: (answer: string) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [freeText, setFreeText] = useState("");

  const answer = selected ?? freeText.trim();
  const canContinue = answer.length > 0;

  // The question itself is shown as an assistant bubble above (added in useChat);
  // this card holds only the answer controls, aligned under that bubble.
  return (
    <div className="mb-4 ml-[38px] max-w-[84%] animate-rise rounded-xl border border-paper-line bg-white p-[18px]">
      <div className="mb-3 flex items-center gap-[7px] text-[12.5px] font-medium text-ink-muted">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke="#94a3b8" strokeWidth="1.7" />
          <path d="M9.5 9.5a2.5 2.5 0 1 1 3.2 2.4c-.7.25-1.2.9-1.2 1.6v.5" stroke="#94a3b8" strokeWidth="1.7" strokeLinecap="round" />
          <circle cx="11.9" cy="16.4" r="1" fill="#94a3b8" />
        </svg>
        {clarify.allowFreeText ? "Choose one, or type your own answer." : "Choose the option that fits."}
      </div>

      <div className="mb-3.5 flex flex-wrap gap-2">
        {clarify.options.map((opt) => {
          const isSel = selected === opt;
          return (
            <button
              key={opt}
              onClick={() => {
                setSelected(opt);
                setFreeText("");
              }}
              className={cn(
                "inline-flex items-center gap-[7px] rounded-[10px] border px-4 py-[9px] text-sm transition-colors",
                isSel
                  ? "border-[1.5px] border-brand bg-brand-soft font-semibold text-brand"
                  : "border-[1.5px] border-paper-line bg-white font-medium text-ink-soft hover:border-[#cfc9bb]",
              )}
            >
              {isSel && (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="#1F6FEB" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              {opt}
            </button>
          );
        })}
      </div>

      {clarify.allowFreeText && (
        <input
          value={freeText}
          onChange={(e) => {
            setFreeText(e.target.value);
            setSelected(null);
          }}
          placeholder="Or type your own answer…"
          aria-label="Type your own answer"
          className="mb-3.5 w-full rounded-[10px] border border-paper-line px-[13px] py-2.5 text-sm outline-none focus:border-brand"
        />
      )}

      <div className="flex justify-end">
        <button
          disabled={!canContinue}
          onClick={() => canContinue && onAnswer(answer)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-[10px] px-5 py-2.5 text-sm font-semibold transition-colors",
            canContinue ? "bg-brand text-white hover:bg-brand-hover" : "cursor-not-allowed bg-paper-line text-ink-faint",
          )}
        >
          Continue
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
