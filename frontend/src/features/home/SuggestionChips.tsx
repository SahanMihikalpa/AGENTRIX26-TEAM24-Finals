"use client";

import { SUGGESTIONS } from "@/lib/constants";

export function SuggestionChips({ onPick }: { onPick: (query: string) => void }) {
  return (
    <div className="mt-[18px] flex flex-wrap justify-center gap-2">
      {SUGGESTIONS.map((s) => (
        <button
          key={s.label}
          onClick={() => onPick(s.query)}
          className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-[13.5px] font-medium text-slate-700 transition-colors hover:border-brand hover:text-brand"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
