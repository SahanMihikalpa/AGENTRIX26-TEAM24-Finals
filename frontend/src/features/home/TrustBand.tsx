/**
 * The dark differentiator band: the one thing that sets GovGuide apart — every
 * requirement is backed by a named, dated official source. This is the trust
 * story, told once, boldly.
 */
export function TrustBand() {
  return (
    <section className="mt-[clamp(56px,8vw,96px)] bg-night text-white">
      <div className="mx-auto grid max-w-[1120px] items-center gap-[clamp(36px,5vw,64px)] px-7 py-[clamp(44px,6vw,72px)] [grid-template-columns:repeat(auto-fit,minmax(300px,1fr))]">
        <div>
          <div className="mb-5 inline-flex items-center gap-[7px] rounded-full border border-[rgba(34,197,94,.35)] bg-[rgba(34,197,94,.14)] px-[11px] py-[5px] text-[11.5px] font-bold text-[#86efac]">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" fill="#16a34a" />
              <path d="M17 9l-6 6-3-3" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Trust is the product
          </div>
          <h2 className="m-0 mb-4 text-balance font-serif text-[clamp(24px,4vw,36px)] font-semibold leading-[1.12] tracking-[-0.02em]">
            Every requirement, backed by an official source.
          </h2>
          <p className="m-0 mb-6 max-w-[460px] text-pretty text-[15px] leading-relaxed text-[#aeb8c9]">
            Each document, fee and office comes from a named government source — with the date we last
            checked it. No guesswork, no surprise trips. Just what to bring, and the proof behind it.
          </p>
          <div className="flex flex-wrap gap-2">
            {["Named official source", "Dated & verified", "Printable"].map((t) => (
              <span
                key={t}
                className="rounded-full border border-[rgba(255,255,255,.14)] px-[13px] py-1.5 text-[12.5px] text-[#cbd5e1]"
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-2xl bg-white p-5 text-ink shadow-[0_22px_60px_rgba(0,0,0,.3)]">
          <div className="flex items-center gap-3">
            <div className="flex h-[38px] w-[38px] flex-none items-center justify-center rounded-[9px] bg-[#f1efe7]">
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none">
                <path d="M4 21V9l8-5 8 5v12" stroke="#64748b" strokeWidth="1.7" strokeLinejoin="round" />
                <path d="M4 21h16M9 21v-6h6v6" stroke="#64748b" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold">Registrar General&rsquo;s Department</div>
              <div className="mt-0.5 text-[12.5px] text-ink-muted">Last verified: 20 Jun 2026</div>
            </div>
            <span className="inline-flex items-center gap-[5px] rounded-full bg-verified-bg px-[9px] py-1 text-[11.5px] font-semibold text-verified-text">
              <span className="h-1.5 w-1.5 rounded-full bg-verified-dot" />
              Verified
            </span>
          </div>
          <div className="mt-3 border-t border-paper-hair pt-3 font-mono text-[12.5px] text-ink-faint">
            source card — shown on every requirement
          </div>
        </div>
      </div>
    </section>
  );
}
