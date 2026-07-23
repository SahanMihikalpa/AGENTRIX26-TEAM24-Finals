# `domain/entities.py` — Pure core: entities, value objects, enums

**Layer:** domain (හදවත) · **Stage:** 1 · **Imports:** Python stdlib විතරයි (framework කිසිවක් නෑ)

## 🎯 කාර්යය
System එකේ **හැම දත්ත හැඩයක්ම** (data shape) මෙතන define කරලා තියෙනවා — `Service`, `Fee`, `Office`,
`Source`, `ActionPack` වගේ. මේවා තමයි හැම layer එකක්ම හරහා ගමන් කරන "නාම පද" (nouns).

## 🏛️ Architecture එකේ තැන
මේක **pure layer එකේ හදවත**. Rule එක දැඩියි: **stdlib විතරයි import කරන්නේ** — FastAPI/Pydantic/LangChain/
Chroma/SQL නෑ. මේක `tests/domain/test_purity.py` එකෙන් automatically enforce කරනවා (AD-9). ඒ නිසා business
concepts, තාක්ෂණයෙන් සම්පූර්ණයෙන් නිදහස්.

## 🔍 Code Walkthrough

**සම්මුති 4ක් (conventions) — හැම එකකටම common:**
- `@dataclass(frozen=True, slots=True)` → **immutable** (වෙනස් කරන්න බෑ) + hashable → LangGraph state එකේ
  ආරක්ෂිතව යවන්න පුළුවන්.
- සල්ලි හැමවිටම `Decimal` (කවදාවත් `float` නෑ — මුදල් නිරවද්‍යතාව).
- Database id එක `int | None` (`None` = තවම save කරලා නෑ).
- Collections `tuple` (immutable).

**Enums (StrEnum — string value එක්ක):**
- `Grade` — A5 ගේ තීන්දුව: `SUFFICIENT` / `GAP` (Corrective-RAG switch).
- `VerificationStatus` — `verified` / `auto_gathered` / `pending` / **`rejected`**. `rejected` කියන්නේ
  moderator (B4) කෙනෙක් quarantine කරපු source එකක් — serve කරන්නෙත් නෑ, නැවත ingest කරන්නෙත් නෑ (row එක
  dedup එකට තියාගන්නවා).
- `SourceType` — `gazette`/`circular`/`portal`/`experience`.
- `ServiceCategory` — UI grouping එකට **controlled vocabulary** එකක් (Civil Registration, Land & Property…).
  වැදගත්: `Service.category` field එක plain `str` — ඒ නිසා B3 auto-gather කරන අලුත් category එකකින්
  self-expanding path එක **block වෙන්නේ නෑ**. මේ enum එක verified seed data validate කරන්න විතරයි.
- තව: `OfficeType`, `ReportOutcome`, `ReportStatus`, `MessageRole`, `ActionPackVerification`.

**Catalog entities (රජයේ සේවා දත්ත):**
`Service` → `ServiceVariant` (branch එකක්: inheritance/sale/gift) → `Requirement` (ලියකියවිලි) + `Fee`
(ගාස්තු). `Office` + `ServiceOffice` (link), `DistrictVariation` (දිස්ත්‍රික්ක අනුව වෙනස්කම්).

**Provenance (මූලාශ්‍ර හෙළිදරව්කම):**
- `Source` — හැම fact එකක්ම මේකෙන් එකක් cite කරනවා (`confidence` + `verification_status` දෙක **වෙනම**
  signals — [confidence gate](../../04-tech-stack-and-decisions.md) බලන්න).
- `KBChunk` — vector retrieval එකට save කරන text chunk එකක් (`vector_ref` එකෙන් Chroma vector එකට link).

**Value objects (table නෙවෙයි, runtime විතරයි):**
- `RetrievedChunk` — A4 retrieval එකෙන් එන scored chunk එක (provenance එක්ක).
- **Action Pack පවුල** — `DocumentItem`, `FeeLine`, `ActionPackOffice`, `Citation`, සහ `ActionPack` (A6
  හදන අවසාන, cited, printable උත්තරය). `fallback=True` නම් confidence gate එක fail වුණා කියන එක.

**Feedback + Session:** `ExperienceReport` (පුරවැසි post-visit report — `service_id` optional),
`Session`/`SessionMessage`, `StoredChecklist` (save කරපු ActionPack).

## 🔗 සම්බන්ධතා
හැම layer එකක්ම මේවා use කරනවා: ports මේවා parameter/return type විදියට ගන්නවා; adapters SQLite rows ↔
මේ dataclasses map කරනවා; agents මේවා read/write කරනවා; API DTOs මේවා JSON කරනවා.

## 💡 Design decisions
ER diagram එකට ([`docs/05`](../../05-data-model.md)) map වෙනවා, delta කිහිපයක් එක්ක: `OFFICE.type` →
`office_type` (Python `type` builtin එක shadow නොකරන්න), `VerificationStatus.REJECTED` එකතු කරලා, runtime
value objects (RetrievedChunk, ActionPack family) — ER එකේ නෑ.
