import type { ExperienceReportGateway } from "@/core/ports";
import type { ExperienceReportInput } from "@/core/domain";
import { genId } from "@/lib/id";

/** Mock feedback sink — accepts the report and returns a pending id (FR-6). */
export class MockExperienceReportGateway implements ExperienceReportGateway {
  async submit(_input: ExperienceReportInput): Promise<{ id: string; status: string }> {
    await new Promise((r) => setTimeout(r, 300));
    return { id: genId(), status: "pending" };
  }
}
