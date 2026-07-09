"""Human review workflow for draft rollups.

Approve: promotes a rollup and archives its source entries (never
deletes — archive_entries only flips a flag). Reject: leaves everything
untouched and flags the rollup for attention, so a bad LLM output never
silently corrupts long-term memory.

Both paths write a memory_versions snapshot, so the audit trail records
who decided what and when even though there's only one user.
"""
from __future__ import annotations

from core.memory_store import MemoryStore


class RollupNotFoundError(ValueError):
    pass


def approve_rollup(store: MemoryStore, rollup_id: int, reviewer_notes: str | None = None) -> None:
    rollup = store.get_rollup(rollup_id)
    if rollup is None:
        raise RollupNotFoundError(f"no such rollup: {rollup_id}")

    entries = store.get_entries(start_date=rollup.period_start, end_date=rollup.period_end)
    entry_ids = [e.id for e in entries if e.id is not None]

    store.snapshot(
        "rollup_summaries", rollup_id, {"summary": rollup.summary, "action": "approved"}
    )
    if entry_ids:
        store.archive_entries(entry_ids)
    store.set_rollup_status(rollup_id, "approved", reviewer_notes=reviewer_notes)


def reject_rollup(store: MemoryStore, rollup_id: int, reviewer_notes: str | None = None) -> None:
    rollup = store.get_rollup(rollup_id)
    if rollup is None:
        raise RollupNotFoundError(f"no such rollup: {rollup_id}")

    store.snapshot(
        "rollup_summaries", rollup_id, {"summary": rollup.summary, "action": "rejected"}
    )
    store.set_rollup_status(rollup_id, "needs_attention", reviewer_notes=reviewer_notes)
