import type { Citation, Verification } from "@/core/domain";
import { fmtDate } from "@/lib/format";
import { VerificationDot } from "./VerificationBadge";

function CitationCard({ cite, verification }: { cite: Citation; verification: Verification }) {
  const inner = (
    <>
      <div className="flex h-[34px] w-[34px] flex-none items-center justify-center rounded-[9px] bg-[#f1efe7]">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
          <path d="M4 21V9l8-5 8 5v12" stroke="#64748b" strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M4 21h16M9 21v-6h6v6" stroke="#64748b" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold text-ink">{cite.title}</div>
        <div className="mt-0.5 text-[12.5px] text-ink-muted">Last verified: {fmtDate(cite.lastVerified)}</div>
      </div>
      <VerificationDot verification={verification} />
    </>
  );
  const cls =
    "flex items-center gap-3 rounded-xl border border-paper-hair p-[13px_15px] transition-colors hover:border-[#cfc9bb] hover:bg-paper-raised";
  return cite.url ? (
    <a href={cite.url} target="_blank" rel="noopener noreferrer" className={cls}>
      {inner}
    </a>
  ) : (
    <div className={cls}>{inner}</div>
  );
}

export function Citations({ citations, verification }: { citations: Citation[]; verification: Verification }) {
  return (
    <section className="mb-2">
      <h2 className="m-0 mb-1 font-serif text-lg font-semibold">Sources &amp; trust</h2>
      <p className="m-0 mb-4 text-[13.5px] text-ink-muted">
        Every requirement above is based on these official sources.
      </p>
      <div className="flex flex-col gap-2.5">
        {citations.map((c, i) => (
          <CitationCard key={c.sourceId ?? i} cite={c} verification={verification} />
        ))}
      </div>
    </section>
  );
}
