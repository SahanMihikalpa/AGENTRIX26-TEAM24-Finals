import type { AgentStep, GapState } from "@/core/domain";
import { cn } from "@/lib/cn";

function StepPill({ step }: { step: AgentStep }) {
  const done = step.status === "done";
  const active = step.status === "active";
  return (
    <div
      className={cn(
        "inline-flex items-center gap-[7px] rounded-full border px-[11px] py-1.5",
        done && "border-verified-border bg-verified-bg",
        active && "border-blue-200 bg-brand-soft",
        !done && !active && "border-slate-100 bg-slate-50",
      )}
    >
      {done && (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
          <path d="M20 6L9 17l-5-5" stroke="#16a34a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {active && <span className="gg-spin inline-block h-3 w-3 rounded-full border-2 border-blue-200 border-t-brand" />}
      {!done && !active && <span className="inline-block h-[11px] w-[11px] rounded-full border-2 border-slate-200" />}
      <span
        className={cn(
          "whitespace-nowrap text-[12.5px] font-medium",
          done && "text-verified-text",
          active && "text-blue-700",
          !done && !active && "text-slate-400",
        )}
      >
        {step.label}
      </span>
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
  return (
    <div className="gg-chrome pointer-events-none fixed inset-x-0 bottom-0 flex justify-center px-4 pb-[18px]">
      <div className="pointer-events-auto w-full max-w-[740px] rounded-[14px] border border-slate-200 bg-white p-[13px_15px] shadow-[0_6px_28px_rgba(15,23,42,.10)]">
        <div className="mb-2.5 flex items-center gap-[7px] text-[11.5px] font-semibold uppercase tracking-[.04em] text-slate-500">
          <span className={cn("h-[7px] w-[7px] rounded-full bg-brand", running && "animate-pulse2")} />
          {running ? "GovGuide is working" : "GovGuide"}
        </div>
        <div className="flex flex-wrap gap-[7px]">
          {steps.map((s) => (
            <StepPill key={s.id} step={s} />
          ))}
        </div>

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
