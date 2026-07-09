"""classify_and_compress: turns raw daily-log text into a structured
record and a set of tags.

This is a rule-based stub — it proves the plumbing (log_entry -> tags +
structured fields -> MemoryStore) before Epoch 3 swaps in real
prompt-driven classification via the Claude Code adapter. Multi-label by
design: an entry can carry more than one tag, since "skipped gym, slept
badly, ate out" is workout + sleep + nutrition in one note, not one
category forced to win.
"""
from __future__ import annotations

from typing import Any

from core.memory_store import MemoryStore

KEYWORDS: dict[str, list[str]] = {
    "workout": [
        "gym", "workout", "leg day", "chest", "shoulders", "arms", "push", "pull",
        "squat", "bench", "deadlift", "cardio", "run", "walk", "steps", "leg press",
    ],
    "sleep": ["sleep", "slept", "insomnia", "nap", "magnesium", "woke up", "bedtime"],
    "nutrition": [
        "ate", "meal", "protein", "calorie", "kcal", "diet", "breakfast",
        "lunch", "dinner", "snack", "carb",
    ],
}


def classify_and_compress(raw_text: str) -> tuple[dict[str, Any], list[str]]:
    text_lower = raw_text.lower()
    tags = [
        tag for tag, keywords in KEYWORDS.items() if any(kw in text_lower for kw in keywords)
    ]
    if not tags:
        tags = ["general"]
    structured = {"summary": raw_text.strip()}
    return structured, tags


def log_entry(store: MemoryStore, date: str, raw_text: str) -> int:
    """Single entry point both a CLI and the future MCP tool call into —
    keeps classification logic in one place regardless of caller."""
    structured, tags = classify_and_compress(raw_text)
    return store.add_entry(date=date, raw_text=raw_text, structured=structured, tags=tags)
