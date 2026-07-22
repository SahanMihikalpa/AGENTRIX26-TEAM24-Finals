import type { ChatGateway, SendInput } from "@/core/ports";
import type { ChatEvent } from "@/core/domain";
import { LAND_PACK, BUSINESS_PACK } from "./mockData";

/**
 * MockChatGateway — reproduces the scripted demo flow from GovGuide.dc.html as
 * typed ChatEvents, so the entire UI runs and demos with NO backend (docs/11 §4).
 * The real SseChatGateway (Stage S4) emits the exact same events.
 *
 * Per-session memory simulates the LangGraph checkpointer: the first send() runs
 * intake → identify → clarify (then pauses); the second send() (the clarify
 * answer) runs retrieval → [gap-fill] → action pack.
 */
type Flow = "land" | "business";
interface SessionState {
  stage: "awaiting_clarify" | "done";
  flow: Flow;
}

const sessions = new Map<string, SessionState>();

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function streamWords(text: string, emit: (e: ChatEvent) => void) {
  const words = text.split(" ");
  for (let i = 0; i < words.length; i++) {
    emit({ type: "token", text: (i === 0 ? "" : " ") + words[i] });
    await sleep(45);
  }
}

function detectFlow(message: string): Flow {
  return /(business|register|company|shop|trade|name)/i.test(message) ? "business" : "land";
}

export class MockChatGateway implements ChatGateway {
  async send(input: SendInput, emit: (e: ChatEvent) => void): Promise<void> {
    const existing = sessions.get(input.sessionId);

    if (!existing) {
      await this.runIntake(input, emit);
    } else if (existing.stage === "awaiting_clarify") {
      await this.runAnswer(input, existing.flow, emit);
    } else {
      // follow-up after completion — just acknowledge
      await streamWords("Your Action Pack is ready above. Start over to ask about another service.", emit);
      emit({ type: "done" });
    }
  }

  private async runIntake(input: SendInput, emit: (e: ChatEvent) => void) {
    const flow = detectFlow(input.message);

    await sleep(450);
    emit({ type: "step", id: "understand", status: "active" });
    await sleep(1050);
    emit({ type: "step", id: "understand", status: "done" });
    emit({ type: "step", id: "find", status: "active" });
    await sleep(1000);
    emit({ type: "step", id: "find", status: "done" });

    if (flow === "land") {
      await streamWords(
        "I can help with that. This looks like a Land Deed Transfer — let me ask one quick question to get it exactly right.",
        emit,
      );
      emit({ type: "step", id: "ask", status: "active" });
      emit({
        type: "clarify",
        question: "What's the basis of the transfer?",
        options: ["Inheritance", "Sale", "Gift"],
        allowFreeText: true,
      });
    } else {
      await streamWords("Happy to help you register a business name. One quick question first.", emit);
      emit({ type: "step", id: "ask", status: "active" });
      emit({
        type: "clarify",
        question: "What type of business are you registering?",
        options: ["Sole proprietorship", "Partnership", "Private company"],
        allowFreeText: true,
      });
    }

    sessions.set(input.sessionId, { stage: "awaiting_clarify", flow });
    emit({ type: "done" });
  }

  private async runAnswer(input: SendInput, flow: Flow, emit: (e: ChatEvent) => void) {
    const answer = input.message;
    emit({ type: "step", id: "ask", status: "done" });

    if (flow === "land") {
      emit({ type: "step", id: "lookup", status: "active" });
      await streamWords(
        `Thanks — an ${answer.toLowerCase()} transfer. I'm pulling together exactly what the Land Registry will ask for.`,
        emit,
      );
      await sleep(800);
      emit({ type: "step", id: "lookup", status: "done" });
      emit({ type: "step", id: "prepare", status: "active" });
      await sleep(1500);
      emit({ type: "step", id: "prepare", status: "done" });
      emit({ type: "actionPack", pack: { ...LAND_PACK, caseSummary: answer } });
      await streamWords(
        "Your Action Pack is ready — your document checklist, the estimated cost, and the official sources, all in one place.",
        emit,
      );
    } else {
      // gap-fill path (self-expanding RAG)
      emit({ type: "step", id: "lookup", status: "active", note: "researching" });
      emit({ type: "gap", phase: "researching", text: "We don't have this one yet — researching it now…" });
      await streamWords(
        "Got it. I don't have this exact service saved yet — give me a moment to research the current requirements.",
        emit,
      );
      await sleep(2800);
      emit({ type: "gap", phase: "updated", text: "Knowledge updated — this service is now saved for everyone." });
      emit({ type: "step", id: "lookup", status: "done" });
      emit({ type: "step", id: "prepare", status: "active" });
      await sleep(1700);
      emit({ type: "step", id: "prepare", status: "done" });
      emit({ type: "actionPack", pack: { ...BUSINESS_PACK, caseSummary: answer } });
      await streamWords(
        "All set. I've added this service to GovGuide. Here's your Action Pack — because it was just gathered, it's marked pending a final check.",
        emit,
      );
    }

    sessions.set(input.sessionId, { stage: "done", flow });
    emit({ type: "done" });
  }
}
