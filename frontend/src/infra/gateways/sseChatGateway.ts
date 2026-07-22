import type { AgentStepId, AgentStepStatus, ChatEvent, GapState } from "@/core/domain";
import type { ChatGateway, SendInput } from "@/core/ports";
import type { ActionPackDTO } from "@/infra/dto";
import { toActionPack } from "@/infra/mappers";

/**
 * SseChatGateway — the real backend adapter (Stage S4). POSTs to `/api/chat` and
 * translates the FastAPI Server-Sent Events stream into the very same ChatEvent
 * union the UI already consumes from MockChatGateway (docs/11 §2,§4), so nothing
 * upstream of this file knows whether it's talking to the mock or the backend.
 *
 * `EventSource` is GET-only, so we read the POST response body as a stream and
 * parse SSE frames by hand. Resuming an A3 clarification is just another send()
 * with the same sessionId — the backend's checkpointer detects the paused thread
 * (`thread_id = sessionId`) and resumes it with the citizen's answer.
 *
 * Wire→view-model reconciliation lives here: backend events are snake_case
 * (`action_pack`, `allow_free_text`); the UI union is camelCase. The Action-Pack
 * payload itself is mapped through `toActionPack` (src/infra/mappers.ts).
 */
export class SseChatGateway implements ChatGateway {
  constructor(private readonly apiBase: string) {}

  async send(
    input: SendInput,
    onEvent: (e: ChatEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const res = await fetch(`${this.apiBase}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message: input.message, session_id: input.sessionId }),
      signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Chat request failed (HTTP ${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line; emit each complete one.
        let sep: number;
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const event = parseFrame(buffer.slice(0, sep));
          buffer = buffer.slice(sep + 2);
          if (event) onEvent(event);
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}

type Json = Record<string, unknown>;

/** Parse one SSE frame ("event: <name>\n data: <json>") into a ChatEvent. */
function parseFrame(frame: string): ChatEvent | null {
  let name = "message";
  const data: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith(":")) continue; // comment / keep-alive
    if (line.startsWith("event:")) name = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trim());
  }
  if (data.length === 0) return null;
  return toChatEvent(name, JSON.parse(data.join("\n")) as Json);
}

/** Map a backend (event-name, payload) pair onto the UI ChatEvent union. */
function toChatEvent(name: string, d: Json): ChatEvent | null {
  switch (name) {
    case "step":
      return {
        type: "step",
        id: d.id as AgentStepId,
        status: d.status as Exclude<AgentStepStatus, "pending">,
        note: d.note as string | undefined,
      };
    case "token":
      return { type: "token", text: String(d.text ?? "") };
    case "message":
      return { type: "message", role: "assistant", text: String(d.text ?? "") };
    case "clarify":
      return {
        type: "clarify",
        question: String(d.question ?? ""),
        options: (d.options as string[] | undefined) ?? [],
        allowFreeText: (d.allow_free_text as boolean | undefined) ?? true,
      };
    case "gap":
      return { type: "gap", phase: d.phase as GapState["phase"], text: String(d.text ?? "") };
    case "action_pack":
      return { type: "actionPack", pack: toActionPack(d as unknown as ActionPackDTO) };
    case "done":
      return { type: "done" };
    case "error":
      return { type: "error", message: String(d.message ?? "Something went wrong.") };
    default:
      return null; // unknown event names are ignored, not fatal
  }
}
