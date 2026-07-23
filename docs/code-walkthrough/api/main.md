# `api/main.py` — FastAPI app factory

**Layer:** api (delivery) · **Stage:** 0/6

## 🎯 කාර්යය
ASGI app එක own කරන entry point එක — middleware, lifespan, routers wire කරනවා. `/health` + chat/feedback/
moderation routes expose කරනවා. Run: `uvicorn app.api.main:app --reload`.

## 🔍 Code Walkthrough
- **`lifespan(app)`** — startup එකේ `get_settings()` read කරලා `configure_logging` + `app.state.settings`
  stash. Heavy runtime (graph + bge) boot එකේදී build කරන්නේ **නෑ** — lazy (first request එකේදී) → process
  instant start, tests build trigger කරන්නේ නෑ.
- **`create_app()`** — application **factory** (module singleton එකට අමතරව) — tests import-time side
  effects නැතුව fresh instance හදනවා. CORS middleware (settings වලින්), `/health`, routers include.
- `app = create_app()` — module-level ASGI app.

## 🔗 සම්බන්ධතා
Routers: [chat](routes/chat.md), [feedback](routes/feedback.md), [moderation](routes/moderation.md).
Runtime: [runtime.md](runtime.md) (lazy `get_runtime`).

## 💡 Design decision — factory + lazy runtime
Factory pattern → testability. Heavy runtime lazy → boot fast + tests network එකට යන්නේ නෑ.
