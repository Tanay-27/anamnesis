"""Applies core/schema.sql to a SQLite database file. Idempotent — safe to
run against an existing database; CREATE TABLE IF NOT EXISTS means it never
clobbers data.
"""
import sqlite3
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def migrate(db_path: str) -> None:
    schema_sql = SCHEMA_PATH.read_text()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "anamnesis.db"
    migrate(target)
    print(f"Migrated {target}")
