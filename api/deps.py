"""Shared FastAPI dependencies. Routes should only ever need
get_store() — no route talks to sqlite3 directly.
"""
from __future__ import annotations

import os

from core.memory_store import MemoryStore

DB_PATH = os.environ.get("ANAMNESIS_DB_PATH", "anamnesis.db")


def get_store() -> MemoryStore:
    return MemoryStore(DB_PATH)
