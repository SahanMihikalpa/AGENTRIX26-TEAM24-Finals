"use client";

import { useState } from "react";
import type { ReportOutcome } from "@/core/domain";
import { getExperienceReportGateway } from "@/infra/gateways";

/** Post-visit feedback → experience report (FR-6, docs/03 feedback loop). */
export function FeedbackBar({ sessionId }: { sessionId: string }) {
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(outcome: ReportOutcome) {
    if (busy || done) return;
    setBusy(true);
    try {
      await getExperienceReportGateway().submit({ sessionId, outcome });
      setDone(true);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="gg-noprint mt-[18px] flex items-center gap-[9px] rounded-xl border border-verified-border bg-verified-bg px-4 py-3.5 text-sm font-medium text-verified-text">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M20 6L9 17l-5-5" stroke="#16a34a" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Thank you — this helps us keep GovGuide accurate.
      </div>
    );
  }

  return (
    <div className="gg-noprint mt-[18px] flex flex-wrap items-center justify-between gap-3 rounded-xl border border-paper-hair bg-paper-sunken px-4 py-3.5">
      <span className="text-sm font-medium text-ink-soft">Did this match what the office asked for?</span>
      <div className="flex gap-2">
        <button
          onClick={() => submit("matched")}
          disabled={busy}
          className="rounded-[9px] border border-[#d9d3c6] bg-white px-4 py-[7px] text-[13px] font-semibold text-ink-soft transition-colors hover:border-verified-dot hover:text-verified-text disabled:opacity-60"
        >
          Yes
        </button>
        <button
          onClick={() => submit("extra_doc")}
          disabled={busy}
          className="rounded-[9px] border border-[#d9d3c6] bg-white px-4 py-[7px] text-[13px] font-semibold text-ink-soft transition-colors hover:border-[#cfc9bb] disabled:opacity-60"
        >
          Not quite
        </button>
      </div>
    </div>
  );
}
