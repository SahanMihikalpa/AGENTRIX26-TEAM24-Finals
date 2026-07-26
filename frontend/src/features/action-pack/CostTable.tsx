import type { FeeLine } from "@/core/domain";
import { fmtMoney } from "@/lib/format";

export function CostTable({ fees, total }: { fees: FeeLine[]; total: number }) {
  return (
    <section className="mb-[30px]">
      <h2 className="m-0 mb-4 font-serif text-lg font-semibold">Estimated cost</h2>
      <div className="overflow-hidden rounded-xl border border-paper-hair">
        {fees.map((f, i) => (
          <div key={i} className="flex items-baseline justify-between gap-3 border-b border-[#f3f1ea] px-4 py-3">
            <div>
              <div className="text-[14.5px] text-ink">{f.label}</div>
              {f.note && <div className="mt-0.5 text-xs text-ink-faint">{f.note}</div>}
            </div>
            <div className="whitespace-nowrap text-[14.5px] font-semibold tabular-nums text-ink">
              {fmtMoney(f.amountLkr)}
            </div>
          </div>
        ))}
        <div className="flex items-center justify-between gap-3 bg-paper-sunken px-4 py-3.5">
          <div className="text-[14.5px] font-bold text-ink">Estimated total</div>
          <div className="whitespace-nowrap font-serif text-[18px] font-bold tabular-nums text-brand">{fmtMoney(total)}</div>
        </div>
      </div>
      <p className="m-0 mx-0.5 mt-[9px] text-xs text-ink-faint">
        Estimates only — fees can vary slightly by office and case.
      </p>
    </section>
  );
}
