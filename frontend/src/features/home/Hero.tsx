"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { SuggestionChips } from "./SuggestionChips";
import { HeroPackPreview } from "./HeroPackPreview";

export function Hero() {
  const router = useRouter();
  const [input, setInput] = useState("");

  function start(query: string) {
    const q = query.trim();
    if (!q) return;
    router.push(`/chat?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className="grid items-center gap-[clamp(36px,5vw,64px)] [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
      <div className="animate-rise">
        <div className="mb-5 inline-flex items-center gap-2 text-[11.5px] font-bold uppercase tracking-[.14em] text-brand">
          <span className="inline-block h-[1.5px] w-[22px] bg-brand" />
          Sri Lankan government services
        </div>

        <h1 className="m-0 mb-[18px] text-balance font-serif text-[clamp(34px,5.4vw,54px)] font-semibold leading-[1.05] tracking-[-0.02em] text-ink">
          Government services, made clear.
        </h1>
        <p className="m-0 mb-7 max-w-[460px] text-pretty text-[clamp(15px,2.2vw,17.5px)] leading-relaxed text-ink-soft">
          Tell us what you need in your own words. We&rsquo;ll find the right service and give you an
          exact, printable checklist — with the official source for every step.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            start(input);
          }}
          className="flex max-w-[520px] items-stretch gap-2 rounded-[14px] border border-[#d9d3c6] bg-white py-2 pl-4 pr-2 shadow-[0_2px_10px_rgba(20,33,61,.05)]"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            aria-label="Describe what you need"
            placeholder="e.g. transfer my late father's land to my name"
            className="min-w-0 flex-1 border-none bg-transparent text-[15.5px] text-ink outline-none placeholder:text-ink-faint"
          />
          <button
            type="submit"
            aria-label="Get started"
            className="inline-flex h-11 flex-none items-center gap-2 rounded-[10px] bg-brand px-4 text-[14.5px] font-semibold text-white transition-colors hover:bg-brand-hover"
          >
            Start
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14M13 6l6 6-6 6" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </form>

        <SuggestionChips onPick={start} />

        <div className="mt-[26px] inline-flex items-center gap-2 text-[12.5px] text-ink-muted">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" stroke="#9aa2ae" strokeWidth="1.7" strokeLinejoin="round" />
            <path d="M9 12l2 2 4-4" stroke="#9aa2ae" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>We always show you the source and the date it was checked.</span>
        </div>
      </div>

      <div className="animate-rise">
        <HeroPackPreview />
      </div>
    </div>
  );
}
