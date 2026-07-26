"use client";

import { useState } from "react";
import type { AgentStep, GapState } from "@/core/domain";
import { cn } from "@/lib/cn";

function Chevron({ open, color }: { open: boolean; color: string }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      className="transition-transform"
      style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
    >
      <path d="M6 9l6 6 6-6" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** A single progress pill. Done/active pills are buttons that expand a detail
 *  card; pending pills are inert. This is what turns the agent from a black box
 *  into something legible. */
function StepPill({
  step,
  expanded,
  onToggle,
}: {
  step: AgentStep;
  expanded: boolean;
  onToggle: () => void;
}) {
  const done = step.status === "done";
  const active = step.status === "active";

  if (done) {
    return (
      <button
        onClick={onToggle}
        aria-expanded={expanded}
        className={cn(
          "inline-flex items-center gap-[7px] rounded-full border px-[11px] py-1.5 transition-colors hover:border-verified-dot",
          expanded ? "border-verified-dot bg-[#dcfce7]" : "border-verified-border bg-verified-bg",
        )}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
          <path d="M20 6L9 17l-5-5" stroke="#16a34a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="whitespace-nowrap text-[12.5px] font-medium text-verified-text">{step.label}</span>
        <Chevron open={expanded} color="#16a34a" />
      </button>
    );
  }

  if (active) {
    return (
      <button
        onClick={onToggle}
        aria-expanded={expanded}
        className={cn(
          "inline-flex items-center gap-[7px] rounded-full border bg-brand-soft px-[11px] py-1.5 transition-colors hover:border-brand",
          expanded ? "border-brand" : "border-blue-200",
        )}
      >
        <span className="gg-spin inline-block h-3 w-3 rounded-full border-2 border-blue-200 border-t-brand" />
        <span className="whitespace-nowrap text-[12.5px] font-medium text-blue-700">{step.label}</span>
        <Chevron open={expanded} color="#1F6FEB" />
      </button>
    );
  }

  return (
    <div className="inline-flex items-center gap-[7px] rounded-full border border-paper-hair bg-paper-sunken px-[11px] py-1.5">
      <span className="inline-block h-[11px] w-[11px] rounded-full border-2 border-[#e0dace]" />
      <span className="whitespace-nowrap text-[12.5px] font-medium text-ink-faint">{step.label}</span>
    </div>
  );
}

export function AgentProgress({
  steps,
  gap,
  running,
}: {
  steps: AgentStep[];
  gap: GapState | null;
  running: boolean;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const expanded = steps.find((s) => s.id === expandedId && s.status !== "pending") ?? null;

  return (
    <div className="gg-chrome pointer-events-none flex justify-center px-4 pb-3">
      <div className="pointer-events-auto w-full max-w-[740px] rounded-[14px] border border-paper-line bg-white p-[13px_15px] shadow-[0_6px_28px_rgba(20,33,61,.10)]">
        <div className="mb-2.5 flex items-center gap-[7px] text-[11.5px] font-semibold uppercase tracking-[.04em] text-ink-muted">
          <span className={cn("h-[7px] w-[7px] rounded-full bg-brand", running && "animate-pulse2")} />
          {running ? "GovGuide is working" : "GovGuide"}
        </div>
        <div className="flex flex-wrap gap-[7px]">
          {steps.map((s) => (
            <StepPill
              key={s.id}
              step={s}
              expanded={expandedId === s.id}
              onToggle={() => setExpandedId((id) => (id === s.id ? null : s.id))}
            />
          ))}
        </div>

        {expanded && (expanded.note || expanded.detail) && (
          <div className="mt-2.5 flex animate-rise gap-2.5 rounded-[11px] border border-paper-line bg-paper-sunken px-[13px] py-[11px]">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="mt-px flex-none">
              <circle cx="12" cy="12" r="9" stroke="#94a3b8" strokeWidth="1.7" />
              <path d="M12 11v5" stroke="#94a3b8" strokeWidth="1.8" strokeLinecap="round" />
              <circle cx="12" cy="7.6" r="1.1" fill="#94a3b8" />
            </svg>
            <div className="min-w-0 flex-1">
              <div className="mb-[3px] text-xs font-bold uppercase tracking-[.04em] text-ink-faint">
                {expanded.label}
              </div>
              <div className="text-[13px] leading-snug text-ink-soft">
                {expanded.note ?? expanded.detail}
              </div>
            </div>
          </div>
        )}

        {gap?.phase === "researching" && (
          <div className="mt-[11px] flex animate-rise items-center gap-[9px] rounded-[10px] border border-pending-border bg-pending-bg px-3 py-[9px]">
            <span className="gg-spin inline-block h-[13px] w-[13px] flex-none rounded-full border-2 border-amber-300 border-t-amber-600" />
            <span className="text-[13px] font-medium text-pending-text">{gap.text}</span>
          </div>
        )}
        {gap?.phase === "updated" && (
          <div className="mt-[11px] flex animate-rise items-center gap-[9px] rounded-[10px] border border-verified-border bg-verified-bg px-3 py-[9px]">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="flex-none">
              <circle cx="12" cy="12" r="10" fill="#16a34a" />
              <path d="M17 9l-6 6-3-3" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="text-[13px] font-semibold text-verified-text">{gap.text}</span>
          </div>
        )}
      </div>
    </div>
  );
}
