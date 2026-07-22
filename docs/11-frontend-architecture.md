# 11 · Frontend Architecture

> The frontend is **Next.js (App Router) + TypeScript + Tailwind** ([AD in 04](04-tech-stack-and-decisions.md)),
> talking to the **FastAPI + SSE** backend. It is built with the same hexagonal discipline as the
> backend ([AD-9](09-architecture-decisions.md)): a framework-agnostic **core** (domain types +
> ports) that the UI depends on, and swappable **adapters** (a mock gateway today, the real SSE
> gateway tomorrow) — so the UI is built and demoed **before the backend exists** and switched over
> with zero UI changes. Visual/interaction reference: the `GovGuide.dc.html` mockup.

## 1. How the UI maps to the backend (data flow)

The whole app is three screens that mirror the [agent graph](02-architecture.md#c4-level-3--components-the-agent-graph):

| UI screen | Backend it reflects | Key state |
|---|---|---|
| **Home** | nothing yet — captures the free-text request (FR-1) | `query` |
| **Conversation** | the Answering team `A1→A6` + the gap loop `B1→B3`, streamed | `messages`, `agentSteps`, `clarify`, `gap` |
| **Action Pack** | `A6` structured output + citations (FR-3, FR-5) | `actionPack` |
| **Feedback** (on pack) | experience report → `B2` pipeline (FR-6) | — |
| **Moderation** (admin) | `B4` queue (FR-7) | `queue` |

### Agent-step ↔ progress-pill mapping
The five progress pills in the mockup are a direct projection of the graph nodes:

| Pill | Backend node(s) |
|---|---|
| Understanding your request | A1 Intake & Intent |
| Finding the service | A2 Service Identifier |
| Asking what's needed | A3 Clarification |
| Looking up requirements | A4 Retrieval + A5 Grade (gap loop `B1→B3` nested here, surfaced as `gap` events) |
| Preparing your checklist | A6 Action-Pack Generator |

## 2. API contract (frontend ⇄ backend)

Defined here so both sides agree **now**, before either is built. DTOs are **snake_case** (FastAPI/
Pydantic convention); the frontend maps them to camelCase view models at the adapter boundary.

### Endpoints
| Method · Path | Purpose | Body / Returns |
|---|---|---|
| `POST /api/chat` *(SSE)* | Send a message; stream the agent run. Resuming a clarifying interview is just another call with the same `session_id`. | `{ session_id, message }` → `text/event-stream` (events below) |
| `GET /api/sessions/{id}/action-pack` | Fetch the final pack (fallback to the stream) | → `ActionPack` |
| `POST /api/experience-reports` | Submit feedback after a visit (FR-6) | `{ session_id, service_id?, outcome, text? }` → `{ id, status }` |
| `GET /api/moderation/queue` | Admin: pending `auto_gathered` items (FR-7) | → `ModerationItem[]` |
| `POST /api/moderation/{source_id}/promote` · `/reject` | Admin: promote/reject | → `{ ok }` |

> `session_id` is the LangGraph `thread_id`; the backend checkpointer makes the interview resumable
> ([02 · state](02-architecture.md#state-management-langgraph)). The client generates it (CSPRNG) or
> the server returns it on the first event.

### SSE event stream (the heart of the contract)
Each event is `event: <name>` + `data: <json>`. The union the client handles:

| `event` | `data` payload | UI effect |
|---|---|---|
| `step` | `{ id: 'understand'\|'find'\|'ask'\|'lookup'\|'prepare', status: 'active'\|'done' }` | advance the progress pills |
| `token` | `{ text }` | append to the streaming assistant bubble |
| `message` | `{ role:'assistant', text }` | a complete (non-streamed) message |
| `clarify` | `{ question, options: string[], allow_free_text: bool }` | render the clarifying card; **stream pauses for input** |
| `gap` | `{ phase:'researching'\|'updated', text }` | show the amber "researching" / green "knowledge updated" banner |
| `action_pack` | `ActionPack` | enable the "Open your Action Pack" CTA |
| `done` | `{}` | end the run |
| `error` | `{ message }` | show a graceful error |

### Core types (the contract, as TS)
Aligned to the **as-built** backend entity `backend/app/domain/entities.py::ActionPack`. Wire DTOs are
snake_case (`src/infra/dto.ts`); the UI consumes the camelCase view models below, translated by
`src/infra/mappers.ts`.

```ts
type Verification = 'verified' | 'newly_gathered_pending_verification';

interface ActionPack {
  serviceLabel: string;
  caseSummary?: string;          // UI convenience (pinned variant); may be absent
  district?: string;
  documents: DocumentItem[];     // backend: documents (not "checklist")
  fees: FeeLine[];               // backend: fees (not "costs")
  office?: ActionPackOffice;
  steps: string[];
  estimatedCostLkr: number;
  verification: Verification;
  citations: Citation[];
  fallback?: boolean;            // confidence-gate fallback (AD-8)
  fallbackMessage?: string;
}
interface DocumentItem { name: string; mandatory: boolean; note?: string; sourceId?: number; }
interface FeeLine { label: string; amountLkr: number; note?: string; sourceId?: number; }
interface Citation { sourceId?: number; title: string; url?: string; lastVerified: string; }
interface ActionPackOffice { name: string; address: string; hours?: string; contact?: string; district?: string; }
```
Citations link to facts by `sourceId`; the per-citation trust badge is derived from the pack-level
`verification`. These mirror the [A6 schema](agents/a6-action-pack-generator.md) and the
[ER model](05-data-model.md). When `fallback` is true the confidence gate fired — render
`fallbackMessage`, not a pack.

## 3. Folder structure (clean / hexagonal)

**Dependency rule:** `app` and `features` depend on `core`; `infra` *implements* `core/ports`; `core`
depends on nothing. Swapping the mock gateway for the real SSE gateway touches only `infra/`.

```
frontend/
├── src/
│   ├── app/                       # DELIVERY — Next.js App Router (routes only, thin)
│   │   ├── layout.tsx
│   │   ├── page.tsx               # Home screen
│   │   ├── chat/page.tsx          # Conversation + Action Pack (session state machine)
│   │   └── admin/moderation/page.tsx
│   │
│   ├── core/                      # PURE — no React, no fetch
│   │   ├── domain/                #   types: actionPack.ts, chat.ts, moderation.ts
│   │   └── ports/                 #   interfaces: ChatGateway, ExperienceReportGateway, ModerationGateway
│   │
│   ├── infra/                     # ADAPTERS — implement the ports
│   │   ├── config.ts              #   API base URL + USE_MOCK flag
│   │   ├── http/sse.ts            #   SSE parsing helper (fetch + ReadableStream)
│   │   ├── mappers.ts             #   snake_case DTO → camelCase view model
│   │   └── gateways/
│   │       ├── mockChatGateway.ts #   scripted flow (ported from the mockup) → runs w/o backend
│   │       ├── sseChatGateway.ts  #   real /api/chat SSE
│   │       └── index.ts           #   factory: pick mock|real from config
│   │
│   ├── features/                  # FEATURE UI (grouped by feature)
│   │   ├── home/                  #   Hero, SuggestionChips
│   │   ├── conversation/          #   MessageList, AgentProgress, ClarifyCard, GapBanner, ActionPackCTA
│   │   ├── action-pack/           #   ActionPackView, Checklist, CostTable, Citations, VerificationBadge, FeedbackBar
│   │   └── moderation/            #   ModerationQueue
│   │
│   ├── components/ui/             # shared primitives: Button, Card, Badge, Pill, Spinner, Icon
│   ├── hooks/                     # useChat (drives a ChatGateway), useActionPack, useChecklist
│   ├── lib/                       # format.ts (fmtMoney/fmtDate), cn.ts, constants.ts
│   └── styles/globals.css         # Tailwind + design tokens
├── public/
├── .env.example                   # NEXT_PUBLIC_API_BASE, NEXT_PUBLIC_USE_MOCK
├── package.json · tsconfig.json · next.config.mjs · tailwind.config.ts · postcss.config.js
```

## 4. Backend-flexibility mechanism (the key decision)

All UI talks to the **`ChatGateway` port**, never to `fetch` directly:

```ts
interface ChatGateway {
  send(input: { sessionId: string; message: string }, on: (e: ChatEvent) => void): Promise<void>;
}
```
- `MockChatGateway` reproduces the mockup's scripted run (typed events, fake timing) → the UI is fully
  demoable with **no backend**.
- `SseChatGateway` hits the real `/api/chat` SSE and emits the **same** `ChatEvent`s.
- `infra/gateways/index.ts` picks one from `NEXT_PUBLIC_USE_MOCK`. **No feature/UI code changes** when
  the backend lands — this is QA-4 (modifiability) on the frontend, and it lets the two builders work
  in parallel against a frozen contract.

## 5. State & rendering
- **Local component state** via a `useChat` hook (no Redux needed for this size). The hook owns
  `messages`, `agentSteps`, `clarify`, `gap`, `actionPack`, and exposes `send()` / `answerClarify()`.
- The conversation page is a **screen state machine** (`conversation` ↔ `pack`), like the mockup.
- Checklist tick-state and feedback are local UI state (checklist ticks are not persisted server-side
  in the MVP).
- **Print** uses a print stylesheet (the `@media print` rules already in the mockup) for the Action Pack.

## 6. Stage-wise build plan

Each stage is independently runnable and a commit milestone; aligns with [07-execution-plan.md](07-execution-plan.md).

| Stage | Scope | Done when |
|---|---|---|
| **S0 · Scaffold + contract** | Project config, Tailwind tokens, `core/domain` types, `core/ports`, `infra/config`, mock gateway, lib | `npm run dev` serves an empty themed app; types compile |
| **S1 · Home** | Hero, input, suggestion chips, navigation to `/chat?q=…` | Submitting a query routes to the conversation route |
| **S2 · Conversation + streaming** | `useChat` on `MockChatGateway`; MessageList, AgentProgress, token streaming, ClarifyCard, GapBanner, CTA | Full happy path + gap-fill path play from the mock |
| **S3 · Action Pack** | ActionPackView, Checklist, CostTable, Citations, VerificationBadge, print CSS, FeedbackBar → experience report | Pack renders from `action_pack` event; prints clean; feedback submits |
| **S4 · Real backend wiring** | `SseChatGateway` against FastAPI SSE; env swap; error/reconnect | Same UI runs against the live backend with `USE_MOCK=false` |
| **S5 · Moderation + polish** | Admin moderation queue; a11y, responsive, demo polish | Moderator can promote/reject; Lighthouse/a11y pass |

## 7. Design tokens (from the mockup)
- **Primary** `#1F6FEB` (hover `#1a5fd0`); **bg** `#f1f5f9`/`#f8fafc`; **text** `#0f172a`/`#475569`;
  **borders** `#e2e8f0`/`#cbd5e1`. **Verified** green `#16a34a`/`#166534`; **pending** amber
  `#d97706`/`#92400e`. Font **Inter**. Radii 9–18px. These go into `tailwind.config.ts`.
