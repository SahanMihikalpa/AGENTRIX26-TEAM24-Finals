import type { ChatGateway, ExperienceReportGateway } from "@/core/ports";
import { config } from "@/infra/config";
import { MockChatGateway } from "./mockChatGateway";
import { MockExperienceReportGateway } from "./mockExperienceReportGateway";
import { SseChatGateway } from "./sseChatGateway";

/**
 * Gateway factory — the single swap point between mock and real backend.
 * UI/feature code calls these getters; it never knows which implementation
 * it got (docs/11 §4). `NEXT_PUBLIC_USE_MOCK=false` selects the real backend.
 */
let chatGateway: ChatGateway | null = null;
let experienceReportGateway: ExperienceReportGateway | null = null;

export function getChatGateway(): ChatGateway {
  if (chatGateway) return chatGateway;
  chatGateway = config.useMock
    ? new MockChatGateway()
    : new SseChatGateway(config.apiBase);
  return chatGateway;
}

export function getExperienceReportGateway(): ExperienceReportGateway {
  if (experienceReportGateway) return experienceReportGateway;
  // NOTE: the backend has no experience-report endpoint yet (only /api/chat and
  // /api/sessions/{id}/action-pack exist), so the feedback bar stays on the mock
  // even when USE_MOCK=false. Swap to an HttpExperienceReportGateway once the
  // backend exposes POST /api/experience-reports.
  experienceReportGateway = new MockExperienceReportGateway();
  return experienceReportGateway;
}

export { config };
