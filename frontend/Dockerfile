# syntax=docker/dockerfile:1.7
#
# GovGuide frontend — Next.js 16 (App Router), standalone output.

# ── Stage 1: deps — install from the lockfile only, so this layer caches ─────
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci


# ── Stage 2: builder — compile the app ───────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* are inlined into the client bundle at BUILD time, so they are
# build args, not run-time env. NEXT_PUBLIC_API_BASE must be reachable from the
# *browser*: the SSE call to /api/chat is made by the user's browser, not by
# this container — so it is http://localhost:8000, never http://backend:8000.
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ARG NEXT_PUBLIC_USE_MOCK=false
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE \
    NEXT_PUBLIC_USE_MOCK=$NEXT_PUBLIC_USE_MOCK \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build


# ── Stage 3: runner — the traced bundle only, no node_modules ────────────────
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 10001 -S nodejs \
 && adduser -S -u 10001 -G nodejs nextjs

# `standalone` ships its own minimal server.js; static assets are copied
# alongside it because Next deliberately leaves them out of the trace.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]

CMD ["node", "server.js"]
