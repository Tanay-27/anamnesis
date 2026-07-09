import pytest

from core.memory_store import MemoryStore
from core.migrate import migrate
from core.rollup import RollupReasoningError, audit_and_retain_rollup


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    return MemoryStore(db_path)


def test_reasoner_exception_never_persists_a_draft(store):
    def broken_reasoner(entries_summary, numeric_summary):
        raise RuntimeError("provider timeout")

    with pytest.raises(RollupReasoningError, match="provider timeout"):
        audit_and_retain_rollup(store, "2026-07-01", "2026-07-14", [], reasoner=broken_reasoner)

    assert store.list_rollups() == []


def test_reasoner_returning_non_dict_raises(store):
    def bad_reasoner(entries_summary, numeric_summary):
        return "not a dict"

    with pytest.raises(RollupReasoningError, match="expected dict"):
        audit_and_retain_rollup(store, "2026-07-01", "2026-07-14", [], reasoner=bad_reasoner)

    assert store.list_rollups() == []


def test_reasoner_returning_wrong_field_type_raises(store):
    def bad_reasoner(entries_summary, numeric_summary):
        return {"promoted": "should have been a list"}

    with pytest.raises(RollupReasoningError, match="must be a list"):
        audit_and_retain_rollup(store, "2026-07-01", "2026-07-14", [], reasoner=bad_reasoner)

    assert store.list_rollups() == []
