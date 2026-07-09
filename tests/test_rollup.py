import pytest

from core.memory_store import MemoryStore
from core.migrate import migrate
from core.rollup import aggregate_numeric_metrics, audit_and_retain_rollup


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    return MemoryStore(db_path)


def stub_reasoner(entries_summary, numeric_summary):
    return {
        "promoted": ["205kg leg press milestone"],
        "dropped": [],
        "carried_forward": ["sleep still swings 4.5-8hrs"],
    }


def test_aggregate_numeric_metrics_computes_stats_deterministically(store):
    store.add_metric("2026-07-01", "weight_kg", 83.5)
    store.add_metric("2026-07-08", "weight_kg", 84.3)
    store.add_metric("2026-07-14", "weight_kg", 82.0)

    result = aggregate_numeric_metrics(store, ["weight_kg"], "2026-07-01", "2026-07-14")
    assert result["weight_kg"]["start"] == 83.5
    assert result["weight_kg"]["end"] == 82.0
    assert result["weight_kg"]["min"] == 82.0
    assert result["weight_kg"]["max"] == 84.3
    assert result["weight_kg"]["avg"] == pytest.approx((83.5 + 84.3 + 82.0) / 3)
    assert result["weight_kg"]["trend"] == pytest.approx(82.0 - 83.5)


def test_aggregate_numeric_metrics_skips_metrics_with_no_data(store):
    result = aggregate_numeric_metrics(store, ["weight_kg", "steps"], "2026-07-01", "2026-07-14")
    assert result == {}


def test_audit_and_retain_rollup_aggregates_and_calls_reasoner(store):
    store.add_metric("2026-07-01", "weight_kg", 83.5)
    store.add_metric("2026-07-14", "weight_kg", 82.0)
    store.add_entry(
        date="2026-07-05", raw_text="205kg leg press day", structured={}, tags=["workout"]
    )

    rollup_id = audit_and_retain_rollup(
        store, "2026-07-01", "2026-07-14", ["weight_kg"], reasoner=stub_reasoner
    )
    rollup = store.get_rollup(rollup_id)

    assert rollup.status == "draft"
    assert rollup.summary["numeric_metrics"]["weight_kg"]["trend"] == pytest.approx(-1.5)
    assert rollup.summary["promoted"] == ["205kg leg press milestone"]
    assert rollup.summary["carried_forward"] == ["sleep still swings 4.5-8hrs"]
    assert rollup.summary["entry_count"] == 1


def test_audit_and_retain_rollup_never_archives_source_entries(store):
    store.add_entry(date="2026-07-05", raw_text="leg day", structured={}, tags=["workout"])

    audit_and_retain_rollup(store, "2026-07-01", "2026-07-14", [], reasoner=stub_reasoner)

    entries = store.get_entries(include_archived=True)
    assert entries[0].archived is False
