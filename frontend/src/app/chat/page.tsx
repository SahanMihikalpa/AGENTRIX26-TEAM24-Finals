"use client";

/**
 * Conversation + Action Pack screen.
 * STAGE S2: live conversation driven by useChat (streaming, clarifying card,
 *           agent-progress pills, gap-fill banners, Action Pack CTA).
 * STAGE S3: the pack screen renders the full ActionPackView.
 */
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { useChat } from "@/hooks/useChat";
import { MessageList } from "@/features/conversation/MessageList";
import { AgentProgress } from "@/features/conversation/AgentProgress";
import { ClarifyCard } from "@/features/conversation/ClarifyCard";
import { ActionPackCTA } from "@/features/conversation/ActionPackCTA";
import { ActionPackView } from "@/features/action-pack/ActionPackView";

type Screen = "conversation" | "pack";

function ChatInner() {
  const params = useSearchParams();
  const q = params.get("q") ?? "";

  const chat = useChat();
  const startedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [screen, setScreen] = useState<Screen>("conversation");

  useEffect(() => {
    if (!startedRef.current && q) {
      startedRef.current = true;
      chat.start(q);
    }
  }, [q, chat]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages, chat.clarify, chat.actionPack]);

  const showCTA = !!chat.actionPack && !chat.clarify && !chat.isRunning;

  if (screen === "pack" && chat.actionPack) {
    return (
      <ActionPackView
        pack={chat.actionPack}
        sessionId={chat.sessionId}
        onBack={() => setScreen("conversation")}
      />
    );
  }

  return (
    <div className="gg-screen min-h-screen bg-slate-100">
      <header className="gg-chrome sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-slate-50/90 px-5 py-3 backdrop-blur">
        <Logo size={28} />
        <Link href="/">
          <Button variant="secondary">Start over</Button>
        </Link>
      </header>

      <main className="mx-auto max-w-[740px] px-5 pb-[220px] pt-6">
        <MessageList messages={chat.messages} />

        {chat.clarify && <ClarifyCard clarify={chat.clarify} onAnswer={chat.answer} />}

        {showCTA && chat.actionPack && (
          <ActionPackCTA service={chat.actionPack.serviceLabel} onOpen={() => setScreen("pack")} />
        )}

        {chat.error && (
          <div className="ml-[38px] max-w-[84%] rounded-xl border border-pending-border bg-pending-bg px-4 py-3 text-sm text-pending-text">
            {chat.error}
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <AgentProgress steps={chat.steps} gap={chat.gap} running={chat.isRunning} />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatInner />
    </Suspense>
  );
}
