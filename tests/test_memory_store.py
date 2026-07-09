import pytest

from core.memory_store import MemoryStore
from core.migrate import migrate
from core.models import Goal, percent_achieved


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    return MemoryStore(db_path)


# -- daily_entries -----------------------------------------------------------

def test_add_and_get_entry(store):
    entry_id = store.add_entry(
        date="2026-07-01",
        raw_text="chest and shoulders day, went hard",
        structured={"day_type": "push", "intensity": "high"},
        tags=["workout"],
    )
    entries = store.get_entries()
    assert len(entries) == 1
    assert entries[0].id == entry_id
    assert entries[0].tags == ["workout"]
    assert entries[0].structured["day_type"] == "push"
    assert entries[0].archived is False


def test_get_entries_filters_by_date_range(store):
    store.add_entry(date="2026-07-01", raw_text="a", structured={}, tags=[])
    store.add_entry(date="2026-07-05", raw_text="b", structured={}, tags=[])
    store.add_entry(date="2026-07-10", raw_text="c", structured={}, tags=[])

    entries = store.get_entries(start_date="2026-07-03", end_date="2026-07-07")
    assert len(entries) == 1
    assert entries[0].raw_text == "b"


def test_get_entries_excludes_archived_by_default(store):
    entry_id = store.add_entry(date="2026-07-01", raw_text="a", structured={}, tags=[])
    store.archive_entries([entry_id])

    assert store.get_entries() == []
    assert len(store.get_entries(include_archived=True)) == 1


def test_multi_label_tags_not_forced_exclusive(store):
    store.add_entry(
        date="2026-07-01",
        raw_text="skipped gym, slept badly, ate out",
        structured={},
        tags=["workout", "sleep", "nutrition"],
    )
    entries = store.get_entries()
    assert set(entries[0].tags) == {"workout", "sleep", "nutrition"}


# -- daily_metrics -------------------------------------------------------------

def test_add_and_query_metric_series(store):
    store.add_metric(date="2026-07-01", metric_name="weight_kg", value=83.5)
    store.add_metric(date="2026-07-02", metric_name="weight_kg", value=83.6)
    store.add_metric(date="2026-07-01", metric_name="steps", value=10000)

    series = store.get_metric_series("weight_kg")
    assert [p.value for p in series] == [83.5, 83.6]
    assert len(store.get_metric_series("steps")) == 1


# -- goals ------------------------------------------------------------------

def test_goal_crud_and_status_update(store):
    goal_id = store.add_goal(
        Goal(
            id=None,
            metric="weight_kg",
            start_value=83.5,
            start_date="2026-06-22",
            target_value=73.0,
            target_date="2026-09-20",
        )
    )
    goals = store.get_goals(status="active")
    assert len(goals) == 1
    assert goals[0].id == goal_id

    store.update_goal_status(goal_id, "achieved")
    assert store.get_goals(status="active") == []
    assert store.get_goals(status="achieved")[0].id == goal_id


def test_percent_achieved_handles_loss_and_gain_goals():
    # weight-loss goal: 83.5 -> 73, currently at 80
    assert percent_achieved(83.5, 73.0, 80.0) == pytest.approx(33.33, abs=0.1)
    # weight-gain goal: 60 -> 70, currently at 65
    assert percent_achieved(60.0, 70.0, 65.0) == pytest.approx(50.0)
    # clamps outside [0, 100] rather than going negative or over 100
    assert percent_achieved(83.5, 73.0, 90.0) == 0.0
    assert percent_achieved(83.5, 73.0, 70.0) == 100.0


# -- rollup_summaries -----------------------------------------------------------

def test_rollup_draft_lifecycle(store):
    rollup_id = store.add_rollup_draft(
        period_start="2026-07-01",
        period_end="2026-07-14",
        summary={"promoted": [], "dropped": [], "carried_forward": []},
    )
    rollup = store.get_rollup(rollup_id)
    assert rollup.status == "draft"

    store.set_rollup_status(rollup_id, "approved", reviewer_notes="looks right")
    rollup = store.get_rollup(rollup_id)
    assert rollup.status == "approved"
    assert rollup.reviewer_notes == "looks right"
    assert rollup.reviewed_at is not None


def test_list_rollups_filters_by_status(store):
    store.add_rollup_draft("2026-07-01", "2026-07-14", {})
    r2 = store.add_rollup_draft("2026-07-15", "2026-07-28", {})
    store.set_rollup_status(r2, "approved")

    drafts = store.list_rollups(status="draft")
    assert len(drafts) == 1


def test_get_rollup_missing_returns_none(store):
    assert store.get_rollup(9999) is None


# -- memory_versions (audit trail) ----------------------------------------------

def test_memory_version_snapshot_and_retrieval(store):
    entry_id = store.add_entry(date="2026-07-01", raw_text="a", structured={}, tags=[])
    store.snapshot("daily_entries", entry_id, {"archived": True})

    versions = store.get_versions("daily_entries", entry_id)
    assert len(versions) == 1
    assert versions[0]["entity_type"] == "daily_entries"
    assert versions[0]["snapshot"]["archived"] is True
