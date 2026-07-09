import pytest

from core.classify import classify_and_compress, log_entry
from core.memory_store import MemoryStore
from core.migrate import migrate


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    return MemoryStore(db_path)


def test_classify_detects_workout():
    _, tags = classify_and_compress("chest and shoulders day, went hard")
    assert tags == ["workout"]


def test_classify_detects_sleep():
    _, tags = classify_and_compress("took magnesium, slept great, woke up early")
    assert tags == ["sleep"]


def test_classify_detects_nutrition():
    _, tags = classify_and_compress("hit 90g protein today with eggs and dal")
    assert tags == ["nutrition"]


def test_classify_is_multi_label_not_exclusive():
    _, tags = classify_and_compress("skipped gym because I slept badly and ate out")
    assert set(tags) == {"workout", "sleep", "nutrition"}


def test_classify_falls_back_to_general():
    _, tags = classify_and_compress("weird rainy day, nothing much happened")
    assert tags == ["general"]


def test_log_entry_persists_via_memory_store(store):
    entry_id = log_entry(store, date="2026-07-01", raw_text="205kg leg press, felt strong")
    entries = store.get_entries()
    assert len(entries) == 1
    assert entries[0].id == entry_id
    assert "workout" in entries[0].tags
    assert entries[0].structured["summary"] == "205kg leg press, felt strong"
