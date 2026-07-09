import sqlite3

from core.migrate import migrate

EXPECTED_TABLES = {
    "daily_entries": {"id", "date", "raw_text", "structured_json", "archived", "created_at"},
    "entry_tags": {"entry_id", "tag"},
    "daily_metrics": {"id", "date", "metric_name", "value", "created_at"},
    "goals": {
        "id", "metric", "start_value", "start_date",
        "target_value", "target_date", "status", "created_at",
    },
    "rollup_summaries": {
        "id", "period_start", "period_end", "summary_json",
        "status", "created_at", "reviewed_at", "reviewer_notes",
    },
    "memory_versions": {"id", "entity_type", "entity_id", "snapshot_json", "created_at"},
}


def test_migrate_creates_all_tables(tmp_path):
    db_path = tmp_path / "test.db"
    migrate(str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        for table, expected_cols in EXPECTED_TABLES.items():
            cursor = conn.execute(f"PRAGMA table_info({table})")
            actual_cols = {row[1] for row in cursor.fetchall()}
            assert actual_cols == expected_cols, (
                f"{table}: expected {expected_cols}, got {actual_cols}"
            )
    finally:
        conn.close()


def test_migrate_is_idempotent(tmp_path):
    db_path = tmp_path / "test.db"
    migrate(str(db_path))
    migrate(str(db_path))  # must not raise
