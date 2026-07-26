import type { ModerationGateway } from "@/core/ports";
import type { ModerationItem } from "@/core/domain";

/** In-memory review queue so /moderation is demoable with NEXT_PUBLIC_USE_MOCK=true. */
const SEED: ModerationItem[] = [
  {
    sourceId: 101,
    title: "Department for Registration of Persons — one-day service notice",
    url: "https://www.drp.gov.lk/one-day-service",
    sourceType: "portal",
    retrievedDate: "2026-07-21",
    confidence: 0.52,
    verificationStatus: "auto_gathered",
    isOfficial: true,
  },
  {
    sourceId: 102,
    title: "Land Registry circular 04/2026 — deed transfer stamp duty",
    url: "https://www.rgd.gov.lk/circulars/04-2026",
    sourceType: "circular",
    retrievedDate: "2026-07-20",
    publishedDate: "2026-05-02",
    confidence: 0.61,
    verificationStatus: "auto_gathered",
    isOfficial: true,
  },
  {
    sourceId: 103,
    title: "Citizen report — extra document requested at Gampaha DS office",
    sourceType: "experience",
    retrievedDate: "2026-07-19",
    confidence: 0.34,
    verificationStatus: "pending",
    isOfficial: true,
  },
  {
    sourceId: 104,
    title: "Sri Lanka NIC renewal — step by step (community guide)",
    url: "https://example-blog.lk/nic-renewal",
    sourceType: "portal",
    retrievedDate: "2026-07-22",
    confidence: 0.5,
    verificationStatus: "auto_gathered",
    // No official page existed, so B1's second tier found this. Capped below the
    // serving threshold — it can only become servable if a moderator promotes it.
    isOfficial: false,
  },
];

export class MockModerationGateway implements ModerationGateway {
  private items = [...SEED];

  async queue(): Promise<ModerationItem[]> {
    await new Promise((r) => setTimeout(r, 250));
    return [...this.items];
  }

  async promote(sourceId: string): Promise<{ ok: boolean }> {
    return this.remove(sourceId);
  }

  async reject(sourceId: string): Promise<{ ok: boolean }> {
    return this.remove(sourceId);
  }

  private async remove(sourceId: string) {
    await new Promise((r) => setTimeout(r, 200));
    const before = this.items.length;
    this.items = this.items.filter((i) => String(i.sourceId) !== sourceId);
    return { ok: this.items.length < before };
  }
}
