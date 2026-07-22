"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { SuggestionChips } from "./SuggestionChips";

export function Hero() {
  const router = useRouter();
  const [input, setInput] = useState("");

  function start(query: string) {
    const q = query.trim();
    if (!q) return;
    router.push(`/chat?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className="w-full max-w-[620px] text-center">
      <h1 className="m-0 mb-3.5 text-[40px] font-bold leading-[1.12] tracking-[-0.03em] text-balance">
        Government services made clear.
      </h1>
      <p className="mx-auto mb-[30px] max-w-[480px] text-[17px] leading-[1.55] text-slate-600">
        Tell us what you need in your own words. We&apos;ll find the right service and give you an
        exact, printable checklist — with the official source for every step.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          start(input);
        }}
        className="flex items-stretch gap-2 rounded-xl border border-slate-300 bg-white py-2 pl-4 pr-2 shadow-sm"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-label="Describe what you need"
          placeholder="e.g. transfer my late father's land to my name"
          className="min-w-0 flex-1 border-none bg-transparent text-base text-slate-900 outline-none"
        />
        <button
          type="submit"
          aria-label="Get started"
          className="flex h-11 w-11 flex-none items-center justify-center rounded-[11px] bg-brand transition-colors hover:bg-brand-hover"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M5 12h14M13 6l6 6-6 6" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </form>

      <SuggestionChips onPick={start} />

      <div className="mt-[34px] inline-flex items-center gap-[7px] text-[13px] text-slate-500">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
          <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" stroke="#94a3b8" strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M9 12l2 2 4-4" stroke="#94a3b8" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>We always show you the source and the date it was checked.</span>
      </div>
    </div>
  );
}
