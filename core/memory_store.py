"""SQLite wrapper — the only module in this project with raw SQL. Every
method here is a pure data operation: no classification, no rollup
reasoning, no provider calls. That logic lives in classify.py / rollup.py
and calls into this store, not the other way around.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from core.models import Entry, Goal, MetricPoint, RollupSummary


class MemoryStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- daily_entries --------------------------------------------------

    def add_entry(
        self, date: str, raw_text: str, structured: dict[str, Any], tags: list[str]
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO daily_entries (date, raw_text, structured_json) "
                "VALUES (?, ?, ?)",
                (date, raw_text, json.dumps(structured)),
            )
            entry_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO entry_tags (entry_id, tag) VALUES (?, ?)",
                [(entry_id, tag) for tag in tags],
            )
            return entry_id

    def get_entries(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        include_archived: bool = False,
    ) -> list[Entry]:
        query = "SELECT * FROM daily_entries WHERE 1=1"
        params: list[Any] = []
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if not include_archived:
            query += " AND archived = 0"
        query += " ORDER BY date ASC"

        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            entries = []
            for row in rows:
                tags = [
                    r["tag"]
                    for r in conn.execute(
                        "SELECT tag FROM entry_tags WHERE entry_id = ?", (row["id"],)
                    ).fetchall()
                ]
                entries.append(
                    Entry(
                        id=row["id"],
                        date=row["date"],
                        raw_text=row["raw_text"],
                        structured=json.loads(row["structured_json"]),
                        tags=tags,
                        archived=bool(row["archived"]),
                        created_at=row["created_at"],
                    )
                )
            return entries

    def archive_entries(self, entry_ids: list[int]) -> None:
        with self._conn() as conn:
            conn.executemany(
                "UPDATE daily_entries SET archived = 1 WHERE id = ?",
                [(eid,) for eid in entry_ids],
            )

    # -- daily_metrics ----------------------------------------------------

    def add_metric(self, date: str, metric_name: str, value: float) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO daily_metrics (date, metric_name, value) VALUES (?, ?, ?)",
                (date, metric_name, value),
            )

    def get_metric_series(
        self,
        metric_name: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[MetricPoint]:
        query = "SELECT date, metric_name, value FROM daily_metrics WHERE metric_name = ?"
        params: list[Any] = [metric_name]
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        query += " ORDER BY date ASC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                MetricPoint(date=r["date"], metric_name=r["metric_name"], value=r["value"])
                for r in rows
            ]

    # -- goals --------------------------------------------------------------

    def add_goal(self, goal: Goal) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO goals (metric, start_value, start_date, target_value, "
                "target_date, status) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    goal.metric,
                    goal.start_value,
                    goal.start_date,
                    goal.target_value,
                    goal.target_date,
                    goal.status,
                ),
            )
            return cur.lastrowid

    def get_goals(self, status: str | None = None) -> list[Goal]:
        query = "SELECT * FROM goals"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                Goal(
                    id=r["id"],
                    metric=r["metric"],
                    start_value=r["start_value"],
                    start_date=r["start_date"],
                    target_value=r["target_value"],
                    target_date=r["target_date"],
                    status=r["status"],
                )
                for r in rows
            ]

    def update_goal_status(self, goal_id: int, status: str) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE goals SET status = ? WHERE id = ?", (status, goal_id))

    # -- rollup_summaries -----------------------------------------------------

    def add_rollup_draft(
        self, period_start: str, period_end: str, summary: dict[str, Any]
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO rollup_summaries (period_start, period_end, summary_json, status) "
                "VALUES (?, ?, ?, 'draft')",
                (period_start, period_end, json.dumps(summary)),
            )
            return cur.lastrowid

    def get_rollup(self, rollup_id: int) -> RollupSummary | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM rollup_summaries WHERE id = ?", (rollup_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_rollup(row)

    def list_rollups(self, status: str | None = None) -> list[RollupSummary]:
        query = "SELECT * FROM rollup_summaries"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_rollup(r) for r in rows]

    def set_rollup_status(
        self, rollup_id: int, status: str, reviewer_notes: str | None = None
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE rollup_summaries SET status = ?, reviewed_at = datetime('now'), "
                "reviewer_notes = ? WHERE id = ?",
                (status, reviewer_notes, rollup_id),
            )

    @staticmethod
    def _row_to_rollup(row: sqlite3.Row) -> RollupSummary:
        return RollupSummary(
            id=row["id"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            summary=json.loads(row["summary_json"]),
            status=row["status"],
            created_at=row["created_at"],
            reviewed_at=row["reviewed_at"],
            reviewer_notes=row["reviewer_notes"],
        )

    # -- memory_versions (audit trail) ---------------------------------------

    def snapshot(self, entity_type: str, entity_id: int, data: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO memory_versions (entity_type, entity_id, snapshot_json) "
                "VALUES (?, ?, ?)",
                (entity_type, entity_id, json.dumps(data)),
            )

    def get_versions(self, entity_type: str, entity_id: int) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_versions WHERE entity_type = ? AND entity_id = ? "
                "ORDER BY created_at ASC",
                (entity_type, entity_id),
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["snapshot"] = json.loads(d.pop("snapshot_json"))
                results.append(d)
            return results
