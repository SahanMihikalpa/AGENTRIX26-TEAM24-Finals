"use client";

import { SUGGESTIONS } from "@/lib/constants";

export function SuggestionChips({ onPick }: { onPick: (query: string) => void }) {
  return (
    <div className="mb-7 flex flex-wrap justify-center gap-2.5">
      {SUGGESTIONS.map((s) => (
        <button
          key={s.label}
          onClick={() => onPick(s.query)}
          className="rounded-full border border-line bg-white/60 px-[18px] py-2.5 text-[13.5px] text-ink-700 backdrop-blur-sm transition-colors hover:border-slate-300 hover:bg-white/90"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
