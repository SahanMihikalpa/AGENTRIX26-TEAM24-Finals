import type { ExperienceReportGateway } from "@/core/ports";
import type { ExperienceReportInput } from "@/core/domain";
import type { ExperienceReportResponseDTO } from "@/infra/dto";

/**
 * HttpExperienceReportGateway — the real backend adapter for FR-6.
 *
 * POSTs to `POST /api/experience-reports`, which persists the report and feeds it
 * through the same B2→B3 pipeline the gap loop uses, so citizen feedback grows the
 * knowledge base (docs/03 feedback loop).
 *
 * `serviceId` and the district are deliberately *not* sent when unknown: the
 * backend resolves them from the session's checkpointed state, which is more
 * reliable than anything the browser could infer.
 *
 * The wire `id` is an integer; the port speaks strings (ids are opaque to the UI),
 * so it is stringified here at the adapter boundary.
 */
export class HttpExperienceReportGateway implements ExperienceReportGateway {
  constructor(private readonly apiBase: string) {}

  async submit(input: ExperienceReportInput): Promise<{ id: string; status: string }> {
    const res = await fetch(`${this.apiBase}/api/experience-reports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        outcome: input.outcome,
        session_id: input.sessionId || null,
        service_id: input.serviceId ?? null,
        text: input.text ?? "",
      }),
    });

    if (!res.ok) {
      throw new Error(`Experience report failed (HTTP ${res.status})`);
    }

    const dto = (await res.json()) as ExperienceReportResponseDTO;
    return { id: String(dto.id), status: dto.status };
  }
}
