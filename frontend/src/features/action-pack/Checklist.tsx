"use client";

import { useState } from "react";
import type { Citation, DocumentItem } from "@/core/domain";

function SourceLink({ citation }: { citation: Citation }) {
  const content = (
    <>
      Source: {citation.title}
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
        <path d="M7 17L17 7M9 7h8v8" stroke="#1F6FEB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </>
  );
  const cls = "mt-[5px] inline-flex items-center gap-1 text-[12.5px] font-medium text-brand";
  return citation.url ? (
    <a href={citation.url} target="_blank" rel="noopener noreferrer" className={cls}>
      {content}
    </a>
  ) : (
    <span className={cls}>{content}</span>
  );
}

export function Checklist({
  documents,
  citationsBySource,
}: {
  documents: DocumentItem[];
  citationsBySource: Map<number, Citation>;
}) {
  const [checked, setChecked] = useState<Record<number, boolean>>({});

  return (
    <section className="mb-[30px]">
      <h2 className="m-0 mb-1 text-base font-bold">What to bring</h2>
      <p className="m-0 mb-4 text-[13.5px] text-slate-500">Tick each item as you collect it.</p>
      {documents.map((item, i) => {
        const cite = item.sourceId != null ? citationsBySource.get(item.sourceId) : undefined;
        return (
          <label key={i} className="flex cursor-pointer items-start gap-[13px] border-b border-slate-100 py-[13px]">
            <input
              type="checkbox"
              checked={!!checked[i]}
              onChange={() => setChecked((c) => ({ ...c, [i]: !c[i] }))}
              className="mt-[3px] h-[18px] w-[18px] flex-none cursor-pointer accent-brand"
            />
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-[9px]">
                <span className="text-[15px] font-medium text-slate-800">{item.name}</span>
                {item.mandatory ? (
                  <span className="rounded-[5px] bg-brand-soft px-[7px] py-0.5 text-[10.5px] font-bold uppercase tracking-[.04em] text-brand">
                    Required
                  </span>
                ) : (
                  <span className="rounded-[5px] bg-slate-100 px-[7px] py-0.5 text-[10.5px] font-bold uppercase tracking-[.04em] text-slate-500">
                    Optional
                  </span>
                )}
              </div>
              {item.note && <div className="mt-1 text-[13px] leading-relaxed text-slate-500">{item.note}</div>}
              {cite && <SourceLink citation={cite} />}
            </div>
          </label>
        );
      })}
    </section>
  );
}
