/**
 * A static Action-Pack preview beside the hero — shows, in one glance, what the
 * product hands back: a checklist, a dated official source, and a total. Purely
 * decorative marketing content; the real pack is generated in the chat flow.
 */
export function HeroPackPreview() {
  return (
    <div className="relative animate-rise">
      {/* Offset paper card behind, for depth. */}
      <div className="absolute inset-y-4 -left-3.5 right-[-14px] rounded-[20px] border border-paper-border bg-paper-hair" />
      <div className="relative rounded-[20px] border border-paper-line bg-white p-6 shadow-[0_22px_60px_rgba(20,33,61,.14)]">
        <div className="mb-3.5 flex items-start justify-between gap-3">
          <div>
            <div className="mb-1.5 text-[10.5px] font-bold uppercase tracking-[.12em] text-brand">
              Action Pack
            </div>
            <div className="font-serif text-[21px] font-semibold tracking-tight">Land Deed Transfer</div>
          </div>
          <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-verified-border bg-verified-bg px-2.5 py-[5px] text-[11.5px] font-semibold text-verified-text">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" fill="#16a34a" />
              <path d="M17 9l-6 6-3-3" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Verified
          </span>
        </div>

        <div className="border-t border-paper-hair pt-3.5">
          {["Original title deed of the property", "Death certificate of previous owner"].map((doc) => (
            <div key={doc} className="flex items-center gap-[11px] py-2">
              <span className="flex h-[17px] w-[17px] flex-none items-center justify-center rounded-[5px] bg-brand">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <span className="text-sm text-ink">{doc}</span>
            </div>
          ))}
          <div className="flex items-center gap-[11px] py-2">
            <span className="inline-block h-[17px] w-[17px] flex-none rounded-[5px] border-2 border-[#d9d3c6]" />
            <span className="text-sm text-ink-muted">Grant of probate / letters of admin</span>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-[11px] rounded-xl border border-paper-hair bg-paper-raised px-[13px] py-[11px]">
          <div className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-lg bg-[#f1efe7]">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path d="M4 21V9l8-5 8 5v12" stroke="#64748b" strokeWidth="1.7" strokeLinejoin="round" />
              <path d="M4 21h16M9 21v-6h6v6" stroke="#64748b" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[12.5px] font-semibold text-ink">Registrar General&rsquo;s Department</div>
            <div className="mt-px text-[11px] text-ink-muted">Last verified: 20 Jun 2026</div>
          </div>
          <span className="h-[7px] w-[7px] flex-none rounded-full bg-verified-dot" />
        </div>

        <div className="mt-3.5 flex items-center justify-between">
          <span className="text-[13px] font-semibold text-ink">Estimated total</span>
          <span className="font-serif text-[19px] font-bold text-brand">LKR 10,550</span>
        </div>
      </div>
    </div>
  );
}
