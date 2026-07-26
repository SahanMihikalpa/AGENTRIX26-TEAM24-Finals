"use client";

import { SUGGESTIONS } from "@/lib/constants";

export function SuggestionChips({ onPick }: { onPick: (query: string) => void }) {
  return (
    <div className="mt-4 flex max-w-[540px] flex-wrap gap-2">
      {SUGGESTIONS.map((s) => (
        <button
          key={s.label}
          onClick={() => onPick(s.query)}
          className="rounded-full border border-[#e0dace] bg-paper-raised px-3.5 py-[7px] text-[13px] font-medium text-ink-soft transition-colors hover:border-brand hover:bg-white hover:text-brand"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
