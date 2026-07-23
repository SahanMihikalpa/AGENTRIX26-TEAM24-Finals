import type { ModerationGateway } from "@/core/ports";
import type { ModerationItem } from "@/core/domain";
import type { ModerationActionDTO, ModerationItemDTO } from "@/infra/dto";
import { toModerationItem } from "@/infra/mappers";

/**
 * HttpModerationGateway — the real backend adapter for the B4 review loop (FR-7).
 *
 * Wraps the three moderation endpoints:
 *   GET  /api/moderation/queue           → sources still `auto_gathered`/`pending`
 *   POST /api/moderation/{id}/promote    → mark `verified`
 *   POST /api/moderation/{id}/reject     → quarantine + de-index
 *
 * Reject is **destructive** on the backend (the source's chunks are deleted so it
 * is no longer retrievable); the UI is responsible for confirming before calling.
 */
export class HttpModerationGateway implements ModerationGateway {
  constructor(private readonly apiBase: string) {}

  async queue(): Promise<ModerationItem[]> {
    const res = await fetch(`${this.apiBase}/api/moderation/queue`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`Moderation queue failed (HTTP ${res.status})`);
    const rows = (await res.json()) as ModerationItemDTO[];
    return rows.map(toModerationItem);
  }

  promote(sourceId: string): Promise<{ ok: boolean }> {
    return this.act(sourceId, "promote");
  }

  reject(sourceId: string): Promise<{ ok: boolean }> {
    return this.act(sourceId, "reject");
  }

  private async act(sourceId: string, action: "promote" | "reject") {
    const res = await fetch(`${this.apiBase}/api/moderation/${sourceId}/${action}`, {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    if (res.status === 404) throw new Error(`Source ${sourceId} no longer exists.`);
    if (!res.ok) throw new Error(`Could not ${action} source (HTTP ${res.status})`);
    const dto = (await res.json()) as ModerationActionDTO;
    return { ok: dto.ok };
  }
}
