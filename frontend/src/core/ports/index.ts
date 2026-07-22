/**
 * Ports — the interfaces the UI depends on. Implementations live in src/infra.
 * This is what keeps the frontend flexible against the (not-yet-built) backend:
 * the UI never calls fetch directly, only these ports (docs/11 §4).
 */
import type {
  ActionPack,
  ChatEvent,
  ExperienceReportInput,
  ModerationItem,
} from "@/core/domain";

export interface SendInput {
  sessionId: string;
  message: string;
}

/** Streams an agent run as ChatEvents. Resuming a clarify is just another send(). */
export interface ChatGateway {
  send(input: SendInput, onEvent: (e: ChatEvent) => void, signal?: AbortSignal): Promise<void>;
}

export interface ActionPackGateway {
  get(sessionId: string): Promise<ActionPack>;
}

export interface ExperienceReportGateway {
  submit(input: ExperienceReportInput): Promise<{ id: string; status: string }>;
}

export interface ModerationGateway {
  queue(): Promise<ModerationItem[]>;
  promote(sourceId: string): Promise<{ ok: boolean }>;
  reject(sourceId: string): Promise<{ ok: boolean }>;
}
