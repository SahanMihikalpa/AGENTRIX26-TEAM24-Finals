# `api/dto.py` — Wire DTOs (frontend contract)

**Layer:** api · **Stage:** 6 · [docs/11](../../11-frontend-architecture.md)

## 🎯 කාර්යය
JSON-serialisable `GraphState` artifacts → frontend එක consume කරන **exact shapes** (snake_case Pydantic).
Wire contract එක define කරන තැන.

## 🔍 DTOs
- **Requests:** `ChatRequest` (`message`, `session_id?`), `ExperienceReportRequest`
  (`outcome`, `session_id?`, `service_id?`, `text`).
- **Action Pack:** `ActionPackDTO` (+ `DocumentItemDTO`, `FeeLineDTO`, `OfficeDTO`, `CitationDTO`) — doc/11
  ActionPack.
- **Responses:** `ExperienceReportResponse` (`id`, `status`), `ModerationItemDTO`, `ModerationActionResponse`.

## 💡 Design decision — money as number (here only)
State එකේ money **precise Decimal string** එකක්; DTO එකේ `amount_lkr: float` — Pydantic coerce කරනවා wire
එකට JSON **number** විදියට (doc/11 contract). `outcome: ReportOutcome` — bad value → automatic **422**.

## 🔗 සම්බන්ධතා
Serialize වෙන්නේ [serialization.py](../application/graph/serialization.md) → validate වෙන්නේ මේ DTOs වලින්
(routes + sse).
