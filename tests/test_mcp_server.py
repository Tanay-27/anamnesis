import pytest

from adapters.claude_code.mcp_server import _get_eager_index, _log_update, _search_memory
from core.memory_store import MemoryStore
from core.migrate import migrate


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    return MemoryStore(db_path)


def test_log_update_persists_caller_supplied_classification(store):
    result = _log_update(
        store,
        date="2026-07-01",
        raw_text="skipped gym, slept badly, ate out",
        tags=["workout", "sleep", "nutrition"],
        structured={"note": "disrupted day"},
    )
    assert "entry_id" in result
    entries = store.get_entries()
    assert set(entries[0].tags) == {"workout", "sleep", "nutrition"}
    assert entries[0].structured["note"] == "disrupted day"


def test_get_eager_index_returns_recent_window(store):
    for i in range(20):
        store.add_entry(date=f"2026-07-{i + 1:02d}", raw_text=f"day {i}", structured={}, tags=[])

    index = _get_eager_index(store, days=15)
    assert len(index) == 15
    assert index[-1]["date"] == "2026-07-20"  # most recent day is last (chronological order)


def test_get_eager_index_excludes_archived(store):
    entry_id = store.add_entry(date="2026-07-01", raw_text="old", structured={}, tags=[])
    store.archive_entries([entry_id])
    store.add_entry(date="2026-07-02", raw_text="recent", structured={}, tags=[])

    index = _get_eager_index(store, days=15)
    assert len(index) == 1
    assert index[0]["date"] == "2026-07-02"


def test_search_memory_finds_archived_too(store):
    entry_id = store.add_entry(date="2026-07-01", raw_text="205kg leg press", structured={}, tags=[])
    store.archive_entries([entry_id])

    results = _search_memory(store, "leg press")
    assert len(results) == 1
    assert results[0]["archived"] is True
