import type {
  ChatGateway,
  ExperienceReportGateway,
  ModerationGateway,
} from "@/core/ports";
import { config } from "@/infra/config";
import { HttpExperienceReportGateway } from "./httpExperienceReportGateway";
import { HttpModerationGateway } from "./httpModerationGateway";
import { MockChatGateway } from "./mockChatGateway";
import { MockExperienceReportGateway } from "./mockExperienceReportGateway";
import { MockModerationGateway } from "./mockModerationGateway";
import { SseChatGateway } from "./sseChatGateway";

/**
 * Gateway factory — the single swap point between mock and real backend.
 * UI/feature code calls these getters; it never knows which implementation
 * it got (docs/11 §4). `NEXT_PUBLIC_USE_MOCK=false` selects the real backend.
 */
let chatGateway: ChatGateway | null = null;
let experienceReportGateway: ExperienceReportGateway | null = null;
let moderationGateway: ModerationGateway | null = null;

export function getChatGateway(): ChatGateway {
  if (chatGateway) return chatGateway;
  chatGateway = config.useMock
    ? new MockChatGateway()
    : new SseChatGateway(config.apiBase);
  return chatGateway;
}

export function getExperienceReportGateway(): ExperienceReportGateway {
  if (experienceReportGateway) return experienceReportGateway;
  experienceReportGateway = config.useMock
    ? new MockExperienceReportGateway()
    : new HttpExperienceReportGateway(config.apiBase);
  return experienceReportGateway;
}

export function getModerationGateway(): ModerationGateway {
  if (moderationGateway) return moderationGateway;
  moderationGateway = config.useMock
    ? new MockModerationGateway()
    : new HttpModerationGateway(config.apiBase);
  return moderationGateway;
}

export { config };
