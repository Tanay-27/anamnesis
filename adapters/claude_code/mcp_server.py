"""MCP server exposing Anamnesis's memory store as tools Claude Code can
call. This file is deliberately thin — it holds no business logic of its
own, just wraps core/ functions for the MCP transport. A future
AnthropicAPIAdapter or OpenAICompatAdapter would wire the same core/
functions into a different tool-calling mechanism, not reimplement them.

Classification happens on the CALLING MODEL's side, not here: log_update
takes already-classified tags/structured fields as arguments. The tool
description is the "prompt" that teaches Claude Code how to classify
before calling it — this is the "swap the stub for a real prompt-driven
version" step from the plan, done by moving classification into the
conversation rather than into more Python rules.

The `_*` functions below hold the actual logic and take a MemoryStore
explicitly, so they're unit-testable without touching the MCP transport
or the module-level singleton. The `@mcp.tool()`-decorated wrappers are
what Claude Code actually calls, and just forward to those.

Run directly for a local smoke test: `python -m adapters.claude_code.mcp_server`
Register with Claude Code via `.mcp.json` (see repo root).
"""
from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from core.memory_store import MemoryStore

DB_PATH = os.environ.get("ANAMNESIS_DB_PATH", "anamnesis.db")
EAGER_INDEX_DAYS = int(os.environ.get("ANAMNESIS_EAGER_INDEX_DAYS", "15"))


def _log_update(
    store: MemoryStore, date: str, raw_text: str, tags: list[str], structured: dict[str, Any]
) -> dict:
    entry_id = store.add_entry(date=date, raw_text=raw_text, structured=structured, tags=tags)
    return {"entry_id": entry_id, "tags": tags}


def _get_eager_index(store: MemoryStore, days: int) -> list[dict]:
    entries = store.get_entries()
    recent = entries[-days:] if days else entries
    return [{"date": e.date, "tags": e.tags, "structured": e.structured} for e in recent]


def _search_memory(store: MemoryStore, query: str) -> list[dict]:
    results = store.search_entries(query)
    return [
        {"date": e.date, "tags": e.tags, "raw_text": e.raw_text, "archived": e.archived}
        for e in results
    ]


mcp = FastMCP("anamnesis")
_store = MemoryStore(DB_PATH)


@mcp.tool()
def log_update(date: str, raw_text: str, tags: list[str], structured: dict[str, Any]) -> dict:
    """Persist a daily health-tracking update.

    Before calling this, read the user's raw update and classify it
    yourself: pick every applicable tag from {"workout", "sleep",
    "nutrition", "general"} — an entry can have more than one (e.g. a
    day that mentions skipping the gym because of bad sleep is both
    "workout" and "sleep"), and extract structured fields worth keeping
    as numbers or short facts (e.g. {"weight_kg": 83.5} or
    {"day_type": "push", "intensity": "high"}). Pass your own
    classification as `tags` and `structured` — do not just pass the
    raw text through unclassified.
    """
    return _log_update(_store, date, raw_text, tags, structured)


@mcp.tool()
def get_eager_index(days: int = EAGER_INDEX_DAYS) -> list[dict]:
    """Return the recent window of non-archived entries (the "eager
    index") as compact JSON. Use this at the start of a session to load
    recent context without re-reading the full history.
    """
    return _get_eager_index(_store, days)


@mcp.tool()
def search_memory(query: str) -> list[dict]:
    """Keyword search over all logged entries, including archived ones
    that have already been rolled up into long-term memory."""
    return _search_memory(_store, query)


if __name__ == "__main__":
    mcp.run()
