import type { FeeLine } from "@/core/domain";
import { fmtMoney } from "@/lib/format";

export function CostTable({ fees, total }: { fees: FeeLine[]; total: number }) {
  return (
    <section className="mb-[30px]">
      <h2 className="m-0 mb-4 text-base font-bold">Estimated cost</h2>
      <div className="overflow-hidden rounded-xl border border-slate-200">
        {fees.map((f, i) => (
          <div key={i} className="flex items-baseline justify-between gap-3 border-b border-slate-100 px-4 py-3">
            <div>
              <div className="text-[14.5px] text-slate-800">{f.label}</div>
              {f.note && <div className="mt-0.5 text-xs text-slate-400">{f.note}</div>}
            </div>
            <div className="whitespace-nowrap text-[14.5px] font-semibold tabular-nums text-slate-900">
              {fmtMoney(f.amountLkr)}
            </div>
          </div>
        ))}
        <div className="flex items-center justify-between gap-3 bg-slate-50 px-4 py-3.5">
          <div className="text-[14.5px] font-bold text-slate-900">Estimated total</div>
          <div className="whitespace-nowrap text-[17px] font-bold tabular-nums text-brand">{fmtMoney(total)}</div>
        </div>
      </div>
      <p className="m-0 mx-0.5 mt-[9px] text-xs text-slate-400">
        Estimates only — fees can vary slightly by office and case.
      </p>
    </section>
  );
}
