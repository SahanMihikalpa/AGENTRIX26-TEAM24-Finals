"use client";

import { useRouter } from "next/navigation";
import type { ActionPack, Citation } from "@/core/domain";
import { Logo } from "@/components/ui/Logo";
import { Checklist } from "./Checklist";
import { CostTable } from "./CostTable";
import { Citations } from "./Citations";
import { FeedbackBar } from "./FeedbackBar";
import { VerificationBadge } from "./VerificationBadge";

function PrintIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M6 9V3h12v6M6 18H4v-7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v7h-2M8 14h8v6H8z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ActionPackView({
  pack,
  sessionId,
  onBack,
}: {
  pack: ActionPack;
  sessionId: string;
  onBack: () => void;
}) {
  const router = useRouter();
  const verified = pack.verification === "verified";
  const citationsBySource = new Map<number, Citation>(
    pack.citations.filter((c) => c.sourceId != null).map((c) => [c.sourceId as number, c]),
  );

  return (
    <div className="gg-screen min-h-screen bg-paper">
      <header className="gg-chrome sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-paper-border bg-[rgba(244,242,236,.9)] px-5 py-3 backdrop-blur">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-[9px] border border-paper-border bg-paper-raised px-[13px] py-[7px] text-[13px] font-medium text-ink-soft transition-colors hover:border-[#cfc9bb]"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M15 6l-6 6 6 6" stroke="#475569" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back
        </button>
        <Logo size={26} />
        <button
          onClick={() => window.print()}
          className="inline-flex items-center gap-1.5 rounded-[9px] bg-brand px-3.5 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-brand-hover"
        >
          <PrintIcon />
          Print
        </button>
      </header>

      <main className="mx-auto max-w-[780px] px-5 pb-14 pt-[26px]">
        <div className="gg-pack rounded-[18px] border border-paper-line bg-white p-[clamp(24px,4vw,38px)] shadow-[0_10px_40px_rgba(20,33,61,.06)]">
          {pack.fallback ? (
            <div className="flex gap-3 rounded-xl border border-pending-border bg-pending-bg p-4">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="mt-0.5 flex-none">
                <path d="M12 3l9 16H3L12 3z" stroke="#d97706" strokeWidth="1.7" strokeLinejoin="round" />
                <path d="M12 10v4M12 17h.01" stroke="#d97706" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
              <div className="text-sm leading-relaxed text-pending-text">
                {pack.fallbackMessage ??
                  "We couldn't verify this service confidently enough to give you a checklist. Please contact the relevant office directly."}
              </div>
            </div>
          ) : (
            <>
              <div className="mb-[26px] flex flex-wrap items-start justify-between gap-4 border-b border-paper-hair pb-[22px]">
                <div>
                  <div className="mb-2.5 text-[11.5px] font-bold uppercase tracking-[.12em] text-brand">Action Pack</div>
                  <h1 className="m-0 mb-2.5 font-serif text-[clamp(23px,4vw,30px)] font-semibold leading-[1.12] tracking-[-0.01em]">{pack.serviceLabel}</h1>
                  {pack.caseSummary && (
                    <span className="inline-block rounded-full bg-[#f1efe7] px-[11px] py-1 text-[13px] font-medium text-ink-soft">
                      Case: {pack.caseSummary}
                    </span>
                  )}
                </div>
                <VerificationBadge verification={pack.verification} />
              </div>

              <Checklist documents={pack.documents} citationsBySource={citationsBySource} />
              <CostTable fees={pack.fees} total={pack.estimatedCostLkr} />
              <Citations citations={pack.citations} verification={pack.verification} />

              {!verified && (
                <div className="mt-[22px] flex gap-3 rounded-xl border border-pending-border bg-pending-bg p-4">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="mt-px flex-none">
                    <path d="M12 3l9 16H3L12 3z" stroke="#d97706" strokeWidth="1.7" strokeLinejoin="round" />
                    <path d="M12 10v4M12 17h.01" stroke="#d97706" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                  <div className="text-[13px] leading-relaxed text-pending-text">
                    We just gathered these requirements live and they&apos;re awaiting a final check. They
                    should be accurate — but please confirm with the office before you travel. We&apos;ll mark
                    this <strong>Verified</strong> once reviewed.
                  </div>
                </div>
              )}

              <div className="gg-noprint mt-7 flex flex-wrap items-center gap-2.5 border-t border-paper-hair pt-6">
                <button
                  onClick={() => window.print()}
                  className="inline-flex items-center gap-[7px] rounded-[11px] bg-brand px-[18px] py-[11px] text-sm font-semibold text-white transition-colors hover:bg-brand-hover"
                >
                  <PrintIcon />
                  Print
                </button>
                {/* Honest label: this opens the print dialog (from which you can
                    "Save as PDF") rather than generating a file directly. */}
                <button
                  onClick={() => window.print()}
                  className="inline-flex items-center gap-[7px] rounded-[11px] border border-[#d9d3c6] bg-white px-[18px] py-[11px] text-sm font-semibold text-ink-soft transition-colors hover:border-brand hover:text-brand"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Save as PDF (via print)
                </button>
                <button
                  onClick={() => router.push("/")}
                  className="ml-auto inline-flex items-center gap-[7px] rounded-[11px] px-3.5 py-[11px] text-sm font-medium text-ink-muted transition-colors hover:text-ink"
                >
                  Start over
                </button>
              </div>

              <FeedbackBar sessionId={sessionId} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
