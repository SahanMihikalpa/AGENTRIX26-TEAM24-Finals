export function ActionPackCTA({ service, onOpen }: { service: string; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="ml-[38px] flex w-[84%] max-w-[84%] animate-rise items-center gap-3.5 rounded-2xl border-[1.5px] border-brand bg-white px-5 py-[18px] text-left transition-colors hover:bg-[#f8fbff]"
    >
      <div className="flex h-[42px] w-[42px] flex-none items-center justify-center rounded-[11px] bg-brand-soft">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M7 3h7l4 4v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" stroke="#1F6FEB" strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M9 12l2 2 4-4" stroke="#1F6FEB" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="text-[15px] font-bold text-ink">Open your Action Pack</div>
        <div className="mt-0.5 text-[13px] text-ink-muted">{service} · checklist, costs &amp; sources</div>
      </div>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M9 6l6 6-6 6" stroke="#1F6FEB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}
