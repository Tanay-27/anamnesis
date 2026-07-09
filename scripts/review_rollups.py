#!/usr/bin/env python3
"""Interactive CLI for reviewing draft rollups. Prints the promoted /
dropped / carried-forward diff and prompts approve / reject / skip.

Usage: .venv/bin/python scripts/review_rollups.py [db_path]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory_store import MemoryStore
from core.review import approve_rollup, reject_rollup


def print_diff(rollup) -> None:
    print(f"\n--- Rollup #{rollup.id} ({rollup.period_start} to {rollup.period_end}) ---")
    print(f"Entries covered: {rollup.summary.get('entry_count', '?')}")
    print("\nNumeric metrics:")
    for name, stats in rollup.summary.get("numeric_metrics", {}).items():
        print(f"  {name}: {stats['start']} -> {stats['end']} (trend {stats['trend']:+.2f})")
    print("\nPromoted (permanent changes):")
    for item in rollup.summary.get("promoted", []):
        print(f"  + {item}")
    print("\nCarried forward (still open):")
    for item in rollup.summary.get("carried_forward", []):
        print(f"  ~ {item}")
    print("\nDropped:")
    for item in rollup.summary.get("dropped", []):
        print(f"  - {item}")


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ANAMNESIS_DB_PATH", "anamnesis.db")
    store = MemoryStore(db_path)

    drafts = store.list_rollups(status="draft")
    if not drafts:
        print("No draft rollups awaiting review.")
        return

    for rollup in drafts:
        print_diff(rollup)
        choice = input("\n[a]pprove / [r]eject / [s]kip? ").strip().lower()
        if choice == "a":
            notes = input("Reviewer notes (optional): ").strip() or None
            approve_rollup(store, rollup.id, reviewer_notes=notes)
            print(f"Rollup #{rollup.id} approved — source entries archived.")
        elif choice == "r":
            notes = input("Reviewer notes (optional): ").strip() or None
            reject_rollup(store, rollup.id, reviewer_notes=notes)
            print(f"Rollup #{rollup.id} rejected — source entries untouched.")
        else:
            print(f"Rollup #{rollup.id} skipped.")


if __name__ == "__main__":
    main()
