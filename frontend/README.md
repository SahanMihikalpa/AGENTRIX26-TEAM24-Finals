# GovGuide — Frontend

Next.js (App Router) + TypeScript + Tailwind. Architecture & contract:
[../docs/11-frontend-architecture.md](../docs/11-frontend-architecture.md).

## ⚠️ Filesystem note (important on this machine)
The repo currently lives on `/media/niranga/Kuppi`, which is an **NTFS (fuseblk)** drive. `npm install`
fails there with a spurious `ENOSPC` because `node_modules` relies on symlinks + huge file counts that
NTFS-via-FUSE doesn't handle. **Develop the frontend from an ext4 location** (e.g. your home folder):

```bash
# one-time: work from an ext4 copy
cp -r "/media/niranga/Kuppi/Agentrix/AGENTRIX26-TEAM24-Finals/frontend" ~/govguide-frontend
cd ~/govguide-frontend
```

(Long term, keep the whole repo on an ext4 disk for any Node work. Verified: install + build succeed on ext4.)

## Run
```bash
cp .env.example .env.local      # NEXT_PUBLIC_USE_MOCK=true by default
npm install
npm run dev                     # http://localhost:3000
```

With `NEXT_PUBLIC_USE_MOCK=true` the app runs the full scripted demo flow **with no backend**.
Set it to `false` once the FastAPI `/api/chat` SSE endpoint exists (Stage S4).

## Scripts
- `npm run dev` — dev server
- `npm run build` / `npm run start` — production
- `npm run typecheck` — `tsc --noEmit`

## Stage status
- ✅ **S0** Scaffold + contract (`core/domain`, `core/ports`, `infra/`, mock gateway)
- ✅ **S1** Home screen
- ✅ **S2** Conversation + streaming (`useChat`, message list, agent-progress pills, clarify card, gap banners, CTA)
- ✅ **S3** Action Pack view (checklist + tick state, cost table, citations, verification badge, fallback, print CSS, feedback → experience report)
- ✅ **S4** Real backend wiring — `SseChatGateway` consumes the FastAPI `/api/chat` SSE stream
  (`step`/`gap`/`clarify`/`message`/`action_pack`/`done`/`error`); clarify resume is just another
  `send()` on the same `sessionId`. Set `NEXT_PUBLIC_USE_MOCK=false` (see `.env.local`).
  *Caveat:* the feedback bar stays on the mock — the backend has no experience-report endpoint yet.
- ⛔ **S5** Moderation + polish

Contract aligned to the as-built backend `ActionPack` (`documents`/`fees`/`estimatedCostLkr`,
`verification: verified | newly_gathered_pending_verification`, `fallback`). DTO↔view-model mapping
lives in `src/infra/dto.ts` + `src/infra/mappers.ts`; the SSE adapter is `src/infra/gateways/sseChatGateway.ts`.
