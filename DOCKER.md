# Running GovGuide in Docker

Two containers — the FastAPI backend and the Next.js frontend — wired by
[`docker-compose.yml`](docker-compose.yml).

## Quick start

```bash
cp backend/.env.example backend/.env   # then fill in GEMINI_API_KEY / GROQ_API_KEY / TAVILY_API_KEY
docker compose up --build
```

- Frontend → <http://localhost:3100>
- Moderation queue → <http://localhost:3100/moderation>
- Backend health → <http://localhost:8000/health>

> The moderation endpoints carry **no authentication**. Put `/moderation` and
> `/api/moderation/*` behind auth before exposing a deployment publicly.

Stop with `docker compose down`. The knowledge base is bind-mounted, so nothing
is lost.

### Why 3100 and not 3000

On Windows, Hyper-V reserves blocks of the dynamic port range at boot, and on
this machine one of them covers 3000:

```bash
netsh int ipv4 show excludedportrange protocol=tcp
```

Binding a reserved port fails with *"An attempt was made to access a socket in a
way forbidden by its access permissions"* even though nothing is listening. The
compose file therefore publishes the frontend on `${FRONTEND_PORT:-3100}`, and
`CORS_ORIGINS` on the backend follows the same variable — the two must agree or
the browser blocks the SSE call.

To use a different port, set it once and rebuild the frontend (the API base is
inlined at build time, but the port itself is not, so a plain restart is enough
unless you also change the backend URL):

```bash
FRONTEND_PORT=4000 docker compose up -d
```

Reclaiming 3000 itself needs an elevated `net stop winnat && net start winnat`,
which drops the reservations until the next reboot — but it also tears down
every other running container's port mappings, so the port variable is the
cheaper fix.

## Why CPU-only, not CUDA

The only GPU-capable workload in the stack is the local `bge-base-en-v1.5`
embedder ([`app/adapters/embeddings/bge.py`](backend/app/adapters/embeddings/bge.py)).
Everything else is a remote API (Gemini, Groq, Tavily) or plain CPU work
(Chroma, SQLite, PyMuPDF). Measured on the development machine:

| Operation | CPU cost |
| --- | --- |
| One query embedding | ~63 ms |
| 64 document chunks, batched | ~2.2 s |

Against that, [`llm_gateway.py`](backend/app/infrastructure/llm_gateway.py)
throttles every agent call through a 15 rpm token bucket — ~4 s per call once
the bucket drains, and a single turn makes several. Embedding is well under 1%
of end-to-end latency, so a GPU cannot move the number that matters.

The cost of taking CUDA anyway: on Linux the default PyPI `torch` is the CUDA
build, which pulls `nvidia-cudnn`, `cublas`, `cusparse` and friends — roughly
4 GB of image for that <1%. The backend Dockerfile therefore installs torch from
the CPU wheel index *before* `requirements.txt`, which is what keeps the image
around 2–3 GB instead of 7 GB.

If a bulk re-embed ever becomes the bottleneck (a much larger catalog than
today's 10 sources / 2 services), the cheaper fixes in order are: batch harder
in `KnowledgeSeeder`, switch the seeding pass to ONNX Runtime, or run one-off
seeding on the host with a CUDA torch — none of which require the *serving*
image to carry CUDA.

## Things worth knowing

**`NEXT_PUBLIC_*` is build-time.** Next.js inlines those variables into the
client bundle during `next build`, so they are compose *build args*, not
environment. Changing `NEXT_PUBLIC_API_BASE` needs `docker compose build
frontend`, not a restart.

**The API base is a browser URL.** The SSE connection to `/api/chat` is opened
by the user's browser, not by the frontend container, so the value is
`http://localhost:8000`. `http://backend:8000` resolves only inside the compose
network and would fail in the browser.

**Secrets are never baked in.** `backend/.dockerignore` excludes `.env`; compose
supplies it at run time via `env_file`.

**The model ships with the image.** `bge-base-en-v1.5` (~440 MB) is downloaded
during the build into `/opt/hf`, so the container boots without a HuggingFace
round-trip and the first `/api/chat` request does not pay for a download.

**Data lives on the host.** `./backend/data` is bind-mounted to `/app/data`,
carrying the seeded Chroma collection, `govguide.sqlite3`, and the LangGraph
checkpoint database that lets an A3 clarification interview resume across
requests.

**Requests are capped.** `CHAT_RATE_LIMIT_RPM` (default 10) and
`API_RATE_LIMIT_RPM` (default 60) reject excess traffic per client IP with a
`429`, so nobody can drain the day's Gemini free-tier quota. The limits are
per-process — a multi-replica deployment would need a shared counter.

**The first run of an upgraded database migrates itself.** The `session` and
`session_message` tables are dropped (LangGraph's checkpointer supersedes them)
and `checklist` is reshaped to key on the thread id. Only *empty* tables are
touched; a populated one is left alone with a warning in the logs.

**A corrupt checkpoint file heals itself.** `checkpoints.sqlite3` holds transient
conversation state in WAL mode, and a container killed mid-write can leave it
torn — after which *every* chat request would fail with "file is not a database",
because the saver is read before the graph runs. On startup an unreadable file is
renamed to `checkpoints.corrupt-<timestamp>.sqlite3` (never deleted) and a fresh
one takes its place. The cost is in-flight clarification interviews; served Action
Packs are in `checklist` and the knowledge base is a separate database, so nothing
durable is lost.

## Common operations

Re-seed the knowledge base inside the container:

```bash
docker compose exec backend python -m app.cli seed
```

Validate a catalog without writing anything:

```bash
docker compose exec backend python -m app.cli seed --dry-run
```

Find catalog entries the crawl duplicated (read-only — it only proposes):

```bash
docker compose exec backend python -m app.cli merge-services --suggest
```

Fold reviewed duplicates into the curated service (drop `--dry-run` to apply):

```bash
docker compose exec backend python -m app.cli merge-services --into 2 --duplicates 5,6,7 --dry-run
```

Tail the backend logs:

```bash
docker compose logs -f backend
```

Rebuild the frontend against a different backend URL:

```bash
docker compose build --build-arg NEXT_PUBLIC_API_BASE=http://192.168.1.10:8000 frontend
```
