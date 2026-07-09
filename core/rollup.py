"""audit_and_retain_rollup: consolidates a window of daily entries into a
long-term rollup draft.

Numeric fields (weight, protein, steps, ...) are aggregated
deterministically in plain Python — never re-summarized by an LLM, so
trend numbers can't drift or be silently dropped. Only the qualitative
narrative (what's a permanent change vs. daily noise, what milestone
happened) goes through a reasoner.

The reasoner is injected, not hardcoded, so this module is fully
unit-testable with a stub — the real implementation is an LLM call
(Claude Code, via the MCP adapter's audit-and-retain prompt), wired in
by whichever adapter drives it, not by this module.
"""
from __future__ import annotations

from typing import Any, Protocol

from core.memory_store import MemoryStore


class QualitativeReasoner(Protocol):
    def __call__(self, entries_summary: str, numeric_summary: dict[str, Any]) -> dict[str, Any]:
        """Returns {"promoted": [...], "dropped": [...], "carried_forward": [...]} —
        the audit-and-retain checklist output, not free-form prose."""
        ...


def aggregate_numeric_metrics(
    store: MemoryStore, metric_names: list[str], start_date: str, end_date: str
) -> dict[str, dict[str, float]]:
    """Deterministic start/end/min/max/avg/trend per metric — no LLM
    involved, so this can never hallucinate or drop a number."""
    result: dict[str, dict[str, float]] = {}
    for name in metric_names:
        series = store.get_metric_series(name, start_date=start_date, end_date=end_date)
        if not series:
            continue
        values = [p.value for p in series]
        result[name] = {
            "start": values[0],
            "end": values[-1],
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "trend": values[-1] - values[0],
        }
    return result


def _format_entries_for_reasoner(entries) -> str:
    return "\n".join(f"- [{e.date}] ({','.join(e.tags)}) {e.raw_text}" for e in entries)


def audit_and_retain_rollup(
    store: MemoryStore,
    start_date: str,
    end_date: str,
    metric_names: list[str],
    reasoner: QualitativeReasoner,
) -> int:
    """Returns the new rollup_summaries row id, written with status='draft'.
    Never archives source entries itself — that only happens on human
    approval, in core/review.py."""
    entries = store.get_entries(start_date=start_date, end_date=end_date)
    numeric = aggregate_numeric_metrics(store, metric_names, start_date, end_date)
    qualitative = reasoner(_format_entries_for_reasoner(entries), numeric)

    summary = {
        "numeric_metrics": numeric,
        "promoted": qualitative.get("promoted", []),
        "dropped": qualitative.get("dropped", []),
        "carried_forward": qualitative.get("carried_forward", []),
        "entry_count": len(entries),
    }
    return store.add_rollup_draft(period_start=start_date, period_end=end_date, summary=summary)
