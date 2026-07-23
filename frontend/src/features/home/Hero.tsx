"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { SuggestionChips } from "./SuggestionChips";

function FloatCard({
  className,
  iconBg,
  icon,
  text,
  delayClass,
}: {
  className: string;
  iconBg: string;
  icon: React.ReactNode;
  text: string;
  delayClass?: string;
}) {
  return (
    <div
      className={`gg-float-card absolute flex w-[210px] items-start gap-2.5 rounded-[14px] border border-line bg-white/75 p-3.5 shadow-card backdrop-blur-[10px] animate-fade-up ${delayClass ?? ""} ${className}`}
    >
      <div className={`flex h-7 w-7 flex-none items-center justify-center rounded-lg ${iconBg}`}>{icon}</div>
      <span className="text-left text-[12.5px] leading-[1.4] text-ink-500">{text}</span>
    </div>
  );
}

export function Hero() {
  const router = useRouter();
  const [input, setInput] = useState("");

  function start(query: string) {
    const q = query.trim();
    if (!q) return;
    router.push(`/chat?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className="relative w-full max-w-[640px]">
      <FloatCard
        className="left-[calc(50%-620px)] top-[150px]"
        iconBg="bg-brand-soft"
        text="Step-by-step checklist for every service"
        icon={
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path
              d="M6 3h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
              stroke="oklch(0.5 0.18 258)"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
            <path d="M9 13l2 2 4-4" stroke="oklch(0.5 0.18 258)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        }
      />
      <FloatCard
        className="right-[calc(50%-640px)] top-[260px]"
        iconBg="bg-[oklch(0.95_0.05_160)]"
        delayClass="[animation-delay:0.1s]"
        text="Verified against official government sources"
        icon={
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 3l7 3v6c0 4.4-3 8.4-7 9-4-0.6-7-4.6-7-9V6l7-3z"
              stroke="oklch(0.5 0.13 160)"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
          </svg>
        }
      />

      <div className="mb-7 inline-flex items-center gap-[7px] rounded-full border border-line bg-white/60 px-4 py-[7px] backdrop-blur-sm">
        <span className="h-1.5 w-1.5 rounded-full bg-brand" />
        <span className="text-[12.5px] font-semibold tracking-[0.01em] text-ink-500">
          Your AI-guided path through Sri Lanka&apos;s government services
        </span>
      </div>

      <h1 className="m-0 mb-5 text-balance text-[38px] font-bold leading-[1.08] tracking-[-0.025em] text-ink-900 sm:text-[48px] lg:text-[58px]">
        Government services, made clear.
      </h1>
      <p className="mx-auto mb-10 max-w-[520px] text-[17px] leading-[1.6] text-ink-500">
        Tell us what you need in your own words. We&apos;ll find the right service and give you an
        exact, printable checklist — with the official source for every step.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          start(input);
        }}
        className="mb-4 flex w-full items-center gap-2 rounded-[18px] border border-line bg-white/85 py-2 pl-4 pr-2 shadow-soft backdrop-blur-md sm:pl-[22px]"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-label="Describe what you need"
          placeholder="e.g. transfer my late father's land to my name"
          className="min-w-0 flex-1 border-none bg-transparent py-2.5 text-[15.5px] text-ink-700 outline-none"
        />
        <button
          type="submit"
          aria-label="Get started"
          className="flex h-[42px] w-[42px] flex-none items-center justify-center rounded-xl bg-gradient-to-br from-brand to-brand-dark shadow-brand transition-[filter] hover:brightness-[1.06]"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
            <path d="M5 12h13M13 6l7 6-7 6" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </form>

      <SuggestionChips onPick={start} />

      <div className="mt-7 flex items-center justify-center gap-[7px]">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 3l7 3v6c0 4.4-3 8.4-7 9-4-0.6-7-4.6-7-9V6l7-3z"
            stroke="oklch(0.55 0.03 255)"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path d="M9.5 12l1.7 1.7L14.5 10" stroke="oklch(0.55 0.03 255)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-[13px] text-ink-400">We always show you the source and the date it was checked.</span>
      </div>
    </div>
  );
}
