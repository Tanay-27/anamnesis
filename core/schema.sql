-- Anamnesis core schema.
-- Raw daily entries are never deleted after a rollup — only archived.
-- That is the hard safety net against rollup drift: source data always
-- remains available to regenerate a corrected long-term summary from.

CREATE TABLE IF NOT EXISTS daily_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    raw_text        TEXT NOT NULL,
    structured_json TEXT NOT NULL,
    archived        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Multi-label tags (nutrition/sleep/workout, non-exclusive) — one entry
-- can carry several tags rather than being forced into one category.
CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id INTEGER NOT NULL REFERENCES daily_entries(id),
    tag      TEXT NOT NULL,
    PRIMARY KEY (entry_id, tag)
);

-- Long-format time series: one row per (date, metric). Keeps chart
-- queries a plain SELECT instead of parsing structured_json each render.
CREATE TABLE IF NOT EXISTS daily_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value       REAL NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS goals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    metric       TEXT NOT NULL,
    start_value  REAL NOT NULL,
    start_date   TEXT NOT NULL,
    target_value REAL NOT NULL,
    target_date  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Draft rollups sit here until a human approves or rejects them.
CREATE TABLE IF NOT EXISTS rollup_summaries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    period_start   TEXT NOT NULL,
    period_end     TEXT NOT NULL,
    summary_json   TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'draft',
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    reviewed_at    TEXT,
    reviewer_notes TEXT
);

-- Audit trail: one row per mutation to any tracked entity.
CREATE TABLE IF NOT EXISTS memory_versions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type   TEXT NOT NULL,
    entity_id     INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
