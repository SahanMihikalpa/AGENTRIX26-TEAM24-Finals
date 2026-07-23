"use client";

/**
 * Moderation queue — the human half of the B4 "serve-but-label" policy (FR-7).
 *
 * Auto-gathered knowledge is served immediately with a "pending verification"
 * label and queued here. A moderator either **promotes** it (→ `verified`, so A6
 * drops the label for everyone after) or **rejects** it (→ quarantined and
 * de-indexed). Reject is irreversible on the backend — the source's chunks are
 * deleted — so it is confirmed before the call goes out.
 */
import { useCallback, useEffect, useState } from "react";
import type { ModerationItem } from "@/core/domain";
import { getModerationGateway } from "@/infra/gateways";
import { ModerationRow } from "./ModerationRow";

type Load = "loading" | "ready" | "error";

export function ModerationQueue() {
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [load, setLoad] = useState<Load>("loading");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoad("loading");
    setError(null);
    try {
      setItems(await getModerationGateway().queue());
      setLoad("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the queue.");
      setLoad("error");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function act(item: ModerationItem, action: "promote" | "reject") {
    if (busyId !== null) return;
    if (action === "reject") {
      const ok = window.confirm(
        `Reject "${item.title}"?\n\nIts extracted content is deleted and the source ` +
          `will no longer be retrieved or re-gathered. This cannot be undone.`,
      );
      if (!ok) return;
    }

    setBusyId(item.sourceId);
    setError(null);
    try {
      const gateway = getModerationGateway();
      const id = String(item.sourceId);
      await (action === "promote" ? gateway.promote(id) : gateway.reject(id));
      setItems((current) => current.filter((i) => i.sourceId !== item.sourceId));
      setNote(action === "promote" ? "Source promoted to verified." : "Source rejected and de-indexed.");
    } catch (e) {
      setError(e instanceof Error ? e.message : `Could not ${action} the source.`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="mx-auto max-w-[860px] px-5 py-8">
      <header className="mb-5">
        <h1 className="m-0 text-[26px] font-bold tracking-[-0.02em] text-ink-900">Moderation queue</h1>
        <p className="m-0 mt-1.5 text-[14.5px] leading-relaxed text-ink-600">
          Knowledge the agents gathered on their own. It is already being served with a
          &ldquo;pending verification&rdquo; label — promote what checks out, reject what
          doesn&apos;t.
        </p>
      </header>

      {note && (
        <div className="mb-4 rounded-xl border border-verified-border bg-verified-bg px-4 py-3 text-sm font-medium text-verified-text">
          {note}
        </div>
      )}

      {error && (
        <div className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-pending-border bg-pending-bg px-4 py-3 text-sm text-pending-text">
          <span>{error}</span>
          <button onClick={() => void refresh()} className="font-semibold underline">
            Retry
          </button>
        </div>
      )}

      {load === "loading" && <p className="text-sm text-slate-500">Loading the queue…</p>}

      {load === "ready" && items.length === 0 && (
        <div className="rounded-2xl border border-line bg-white px-5 py-8 text-center shadow-card">
          <div className="text-sm font-semibold text-ink-800">Nothing awaiting review</div>
          <p className="m-0 mt-1 text-[13.5px] text-ink-500">
            Every gathered source has been reviewed. New ones appear here as the agents
            fill knowledge gaps.
          </p>
        </div>
      )}

      {items.length > 0 && (
        <>
          <div className="mb-2.5 text-[13px] font-semibold uppercase tracking-wide text-slate-500">
            {items.length} awaiting review
          </div>
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {items.map((item) => (
              <ModerationRow
                key={item.sourceId}
                item={item}
                busy={busyId === item.sourceId}
                onPromote={() => void act(item, "promote")}
                onReject={() => void act(item, "reject")}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
