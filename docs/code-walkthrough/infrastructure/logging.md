# `infrastructure/logging.py` — Logging setup

**Layer:** infrastructure (cross-cutting) · **Stage:** 0

## 🎯 කාර්යය
සරල, dependency-free logging setup එකක්. stdout එකට structured-ish lines ලියනවා.

## 🔍 Code Walkthrough
- `configure_logging(level="INFO")` — root logging එක **එක පාරක්** configure කරනවා (`force=True` නිසා
  re-config safe). Format: `time | LEVEL | logger-name | message`.
- `get_logger(name)` — module logger එකක් දෙනවා. හැම module එකකම `get_logger(__name__)` pattern එක.

## 🔗 සම්බන්ධතා
- **Call කරන්නේ:** `api/main.py` (lifespan එකේ `configure_logging`), සහ හැම module එකක්ම `get_logger`.

## 💡 Design decision
Per-session correlation ids + LangSmith tracing (QA-8) **Stage 7 (hardening)** එකට කල් දාලා — දැනට
කුඩාවට තියාගෙන, premature structure එකක් නෑ.
