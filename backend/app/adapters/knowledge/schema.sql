-- GovGuide knowledge base — SQLite schema (source of truth for structured facts).
-- Mirrors the ER in docs/05-data-model.md. Money is stored as TEXT to preserve
-- Decimal precision; dates as ISO strings; enums by value.

CREATE TABLE IF NOT EXISTS source (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    url                 TEXT,
    source_type         TEXT NOT NULL,
    published_date      TEXT,
    retrieved_date      TEXT NOT NULL,
    confidence          REAL NOT NULL,
    verification_status TEXT NOT NULL,
    content_hash        TEXT,         -- for B3 dedup (not in the ER; see docs/10)
    -- 1 unless the source came from B1's unrestricted second-tier search. Records
    -- provenance, not trust level, so a moderator can see they are approving
    -- something published outside government domains.
    is_official         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS service (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT NOT NULL UNIQUE,
    name_en     TEXT NOT NULL,
    category    TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_variant (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id      INTEGER NOT NULL REFERENCES service(id) ON DELETE CASCADE,
    condition_label TEXT NOT NULL,
    description     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requirement (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id    INTEGER NOT NULL REFERENCES service_variant(id) ON DELETE CASCADE,
    source_id     INTEGER NOT NULL REFERENCES source(id),
    document_name TEXT NOT NULL,
    is_mandatory  INTEGER NOT NULL,
    notes         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS fee (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL REFERENCES service_variant(id) ON DELETE CASCADE,
    source_id  INTEGER NOT NULL REFERENCES source(id),
    label      TEXT NOT NULL,
    amount_lkr TEXT NOT NULL,            -- Decimal as text
    notes      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS office (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    office_type TEXT NOT NULL,
    district    TEXT NOT NULL,
    address     TEXT NOT NULL,
    hours       TEXT NOT NULL,
    contact     TEXT NOT NULL,
    geo_lat     REAL,
    geo_lng     REAL
);

CREATE TABLE IF NOT EXISTS service_office (
    service_id INTEGER NOT NULL REFERENCES service(id) ON DELETE CASCADE,
    office_id  INTEGER NOT NULL REFERENCES office(id) ON DELETE CASCADE,
    PRIMARY KEY (service_id, office_id)
);

CREATE TABLE IF NOT EXISTS district_variation (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES service(id) ON DELETE CASCADE,
    source_id  INTEGER NOT NULL REFERENCES source(id),
    district   TEXT NOT NULL,
    notes      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS kb_chunk (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   INTEGER NOT NULL REFERENCES source(id) ON DELETE CASCADE,
    service_id  INTEGER REFERENCES service(id),
    content     TEXT NOT NULL,
    vector_ref  TEXT,
    chunk_index INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS experience_report (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id       INTEGER REFERENCES service(id),
    district         TEXT NOT NULL,
    report_text      TEXT NOT NULL,
    reported_outcome TEXT NOT NULL,
    status           TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

-- The ER's `session` / `session_message` tables are deliberately absent: LangGraph's
-- SqliteSaver checkpointer is the system of record for conversation state (AD-3),
-- keyed by the same session id, and a second copy here could only drift from it.
-- Logged as a delta in docs/05 + docs/10.

-- One row per Action Pack actually served to a citizen. The checkpointer already
-- holds the live state, but it is pruned and thread-scoped; this is the durable,
-- queryable record of what the system told people — the audit trail behind the
-- "we always show you the source" promise, and the fallback that keeps
-- GET /api/sessions/{id}/action-pack answering after a checkpoint is gone.
--
-- `session_id` is TEXT: it is the LangGraph thread id (a hex string), not a row id.
-- `variant_id` is nullable because fallback packs are served without a variant.
--
-- `service_id`/`variant_id` are recorded as plain ids with **no foreign key**, on
-- purpose. This is an append-only record of something that already happened; a
-- referential check could only ever reject a row *after* the citizen was served,
-- turning a bookkeeping edge case into a failed request. The payload is
-- self-contained, so the ids are an index for querying, not an integrity claim.
CREATE TABLE IF NOT EXISTS checklist (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    service_id   INTEGER,
    variant_id   INTEGER,
    payload_json TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_checklist_session ON checklist(session_id);

CREATE INDEX IF NOT EXISTS idx_variant_service   ON service_variant(service_id);
CREATE INDEX IF NOT EXISTS idx_requirement_variant ON requirement(variant_id);
CREATE INDEX IF NOT EXISTS idx_fee_variant       ON fee(variant_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunk_source   ON kb_chunk(source_id);
CREATE INDEX IF NOT EXISTS idx_source_url        ON source(url);
CREATE INDEX IF NOT EXISTS idx_source_hash       ON source(content_hash);
