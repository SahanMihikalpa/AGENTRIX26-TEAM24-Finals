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
    content_hash        TEXT          -- for B3 dedup (not in the ER; see docs/10)
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

CREATE TABLE IF NOT EXISTS session (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    district   TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_message (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES session(id) ON DELETE CASCADE,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checklist (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES session(id) ON DELETE CASCADE,
    variant_id   INTEGER NOT NULL REFERENCES service_variant(id),
    payload_json TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_variant_service   ON service_variant(service_id);
CREATE INDEX IF NOT EXISTS idx_requirement_variant ON requirement(variant_id);
CREATE INDEX IF NOT EXISTS idx_fee_variant       ON fee(variant_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunk_source   ON kb_chunk(source_id);
CREATE INDEX IF NOT EXISTS idx_source_url        ON source(url);
CREATE INDEX IF NOT EXISTS idx_source_hash       ON source(content_hash);
