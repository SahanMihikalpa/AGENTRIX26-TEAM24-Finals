/** DTO (snake_case wire) → domain view model (camelCase). The adapter boundary
 *  that keeps the UI decoupled from the backend's exact JSON (docs/11 §2). */
import type { ActionPack } from "@/core/domain";
import type { ActionPackDTO } from "./dto";

const undef = (s: string | null | undefined): string | undefined => (s ? s : undefined);
const num = (n: string | number): number => (typeof n === "number" ? n : Number(n));

export function toActionPack(dto: ActionPackDTO): ActionPack {
  return {
    serviceLabel: dto.service_label,
    district: undef(dto.district),
    documents: dto.documents.map((d) => ({
      name: d.name,
      mandatory: d.mandatory,
      note: undef(d.notes),
      sourceId: d.source_id ?? undefined,
    })),
    fees: dto.fees.map((f) => ({
      label: f.label,
      amountLkr: num(f.amount_lkr),
      note: undef(f.notes),
      sourceId: f.source_id ?? undefined,
    })),
    office: dto.office
      ? {
          name: dto.office.name,
          address: dto.office.address,
          hours: undef(dto.office.hours),
          contact: undef(dto.office.contact),
          district: undef(dto.office.district),
        }
      : undefined,
    steps: dto.steps,
    estimatedCostLkr: num(dto.estimated_cost_lkr),
    verification: dto.verification,
    citations: dto.citations.map((c) => ({
      sourceId: c.source_id ?? undefined,
      title: c.title,
      url: undef(c.url),
      lastVerified: c.last_verified,
    })),
    fallback: dto.fallback,
    fallbackMessage: undef(dto.fallback_message),
  };
}
