import pytest

from core.memory_store import MemoryStore
from core.migrate import migrate
from core.review import RollupNotFoundError, approve_rollup, reject_rollup


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    return MemoryStore(db_path)


def _seed_rollup(store):
    store.add_entry(date="2026-07-05", raw_text="leg day", structured={}, tags=["workout"])
    store.add_entry(date="2026-07-20", raw_text="out of window", structured={}, tags=["workout"])
    return store.add_rollup_draft(
        period_start="2026-07-01",
        period_end="2026-07-14",
        summary={"promoted": [], "dropped": [], "carried_forward": []},
    )


def test_approve_archives_only_entries_in_the_rollup_window(store):
    rollup_id = _seed_rollup(store)
    approve_rollup(store, rollup_id, reviewer_notes="looks right")

    entries = store.get_entries(include_archived=True)
    in_window = next(e for e in entries if e.date == "2026-07-05")
    out_of_window = next(e for e in entries if e.date == "2026-07-20")
    assert in_window.archived is True
    assert out_of_window.archived is False  # never touched — outside the rollup's period

    rollup = store.get_rollup(rollup_id)
    assert rollup.status == "approved"
    assert rollup.reviewer_notes == "looks right"


def test_approve_writes_audit_snapshot(store):
    rollup_id = _seed_rollup(store)
    approve_rollup(store, rollup_id)

    versions = store.get_versions("rollup_summaries", rollup_id)
    assert len(versions) == 1
    assert versions[0]["snapshot"]["action"] == "approved"


def test_reject_leaves_source_entries_untouched(store):
    rollup_id = _seed_rollup(store)
    reject_rollup(store, rollup_id, reviewer_notes="missed the milestone")

    entries = store.get_entries(include_archived=True)
    assert all(e.archived is False for e in entries)

    rollup = store.get_rollup(rollup_id)
    assert rollup.status == "needs_attention"
    assert rollup.reviewer_notes == "missed the milestone"


def test_approve_missing_rollup_raises(store):
    with pytest.raises(RollupNotFoundError):
        approve_rollup(store, 9999)


def test_reject_missing_rollup_raises(store):
    with pytest.raises(RollupNotFoundError):
        reject_rollup(store, 9999)
