import type { Message } from "@/core/domain";
import { cn } from "@/lib/cn";

function Avatar() {
  return (
    <div className="mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-lg bg-brand">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
        <path d="M20 6L9 17l-5-5" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

export function MessageList({ messages }: { messages: Message[] }) {
  return (
    <>
      {messages.map((m) =>
        m.role === "user" ? (
          <div key={m.id} className="mb-4 flex animate-rise justify-end">
            <div className="max-w-[80%] rounded-[16px_16px_4px_16px] bg-brand px-4 py-3 text-[15px] leading-relaxed text-white">
              {m.text}
            </div>
          </div>
        ) : (
          <div key={m.id} className="mb-4 flex animate-rise justify-start gap-2.5">
            <Avatar />
            <div
              className={cn(
                "max-w-[84%] rounded-[4px_16px_16px_16px] border border-paper-line bg-white px-4 py-3 text-[15px] leading-relaxed text-ink",
              )}
            >
              {m.text}
              {m.streaming && <span className="ml-0.5 inline-block w-2 animate-blink text-brand">▍</span>}
            </div>
          </div>
        ),
      )}
    </>
  );
}
