import type { ModerationItem } from "@/core/domain";
import { Button } from "@/components/ui/Button";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/cn";

const SOURCE_LABEL: Record<ModerationItem["sourceType"], string> = {
  gazette: "Gazette",
  circular: "Circular",
  portal: "Gov. portal",
  experience: "Citizen report",
};

/** Confidence is the B4 signal a moderator triages on — colour it accordingly. */
function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    value >= 0.6
      ? "border-verified-border bg-verified-bg text-verified-text"
      : value >= 0.4
        ? "border-pending-border bg-pending-bg text-pending-text"
        : "border-paper-line bg-paper-hair text-ink-soft";
  return (
    <span
      className={cn("rounded-full border px-2.5 py-1 text-[12px] font-semibold", tone)}
      title="Extraction confidence recorded when this source was gathered"
    >
      {pct}% confident
    </span>
  );
}

export function ModerationRow({
  item,
  busy,
  onPromote,
  onReject,
}: {
  item: ModerationItem;
  busy: boolean;
  onPromote: () => void;
  onReject: () => void;
}) {
  return (
    <li className="flex flex-col gap-3 rounded-xl border border-paper-line bg-white p-4 md:flex-row md:items-center">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-paper-hair px-2 py-0.5 text-[12px] font-semibold text-ink-soft">
            {SOURCE_LABEL[item.sourceType]}
          </span>
          {!item.isOfficial && (
            <span
              className="rounded-md border border-pending-border bg-pending-bg px-2 py-0.5 text-[12px] font-semibold text-pending-text"
              title="Found outside official government domains. Promoting this makes it servable as fact — check the page itself first."
            >
              Not a .gov.lk source
            </span>
          )}
          <ConfidencePill value={item.confidence} />
          <span className="text-[12.5px] text-ink-muted">
            Gathered {fmtDate(item.retrievedDate)}
            {item.publishedDate ? ` · published ${fmtDate(item.publishedDate)}` : ""}
          </span>
        </div>

        <div className="mt-1.5 text-sm font-semibold text-ink">{item.title}</div>

        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-0.5 inline-block max-w-full truncate text-[12.5px] text-brand hover:underline"
          >
            {item.url}
          </a>
        )}
      </div>

      <div className="flex flex-none gap-2">
        <Button variant="secondary" disabled={busy} onClick={onReject}>
          Reject
        </Button>
        <Button disabled={busy} onClick={onPromote}>
          Promote
        </Button>
      </div>
    </li>
  );
}
