"""End-to-end "week in the life" walkthrough — the Epoch 10 test gate
from PLAN.md. Logs a week of entries (including a disrupted day),
triggers a rollup, approves it via the API, and checks the dashboard-
backing endpoints reflect everything correctly afterward.
"""
import pytest
from fastapi.testclient import TestClient

from api.deps import get_store
from api.main import app
from core.memory_store import MemoryStore
from core.migrate import migrate
from core.rollup import audit_and_retain_rollup


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    store = MemoryStore(db_path)
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app), store
    app.dependency_overrides.clear()


def realistic_reasoner(entries_summary, numeric_summary):
    """Stands in for the real Claude Code reasoning pass — a live LLM
    call isn't available in this automated test, so this stub exercises
    the same audit-and-retain shape (promoted/dropped/carried_forward)
    a real one would produce."""
    return {
        "promoted": ["205kg leg press milestone", "hit 90g protein on a low-cal day"],
        "dropped": [],
        "carried_forward": ["sleep still swings 4.5-8hrs night to night"],
    }


def test_week_in_the_life(client):
    test_client, store = client

    # Day 1: goal set
    goal_resp = test_client.post(
        "/api/goals",
        json={
            "metric": "weight_kg",
            "start_value": 83.5,
            "start_date": "2026-07-01",
            "target_value": 73.0,
            "target_date": "2026-09-20",
        },
    )
    assert goal_resp.status_code == 200

    week = [
        ("2026-07-01", 83.5, 9800, "chest and shoulders day, went hard"),
        ("2026-07-02", 83.6, 10200, "arms day, biceps and triceps"),
        ("2026-07-03", 83.4, 7200, "legs day, 205kg leg press, felt strong"),
        ("2026-07-04", 83.8, 4100, "rained out, skipped gym, slept badly, ate out"),
        ("2026-07-05", 83.2, 11000, "back on track, pull day, hit 90g protein"),
        ("2026-07-06", 82.9, 9500, "rest day, magnesium before bed, slept great"),
        ("2026-07-07", 82.5, 10500, "legs pickup day, felt good"),
    ]
    for date, weight, steps, text in week:
        entry_resp = test_client.post("/api/entries", json={"date": date, "raw_text": text})
        assert entry_resp.status_code == 200
        test_client.post(
            "/api/metrics", json={"date": date, "metric_name": "weight_kg", "value": weight}
        )
        test_client.post("/api/metrics", json={"date": date, "metric_name": "steps", "value": steps})

    # The disrupted day should still be classified sanely, not dropped
    disrupted = test_client.get("/api/entries", params={"start_date": "2026-07-04", "end_date": "2026-07-04"})
    assert set(disrupted.json()[0]["tags"]) >= {"workout", "sleep", "nutrition"}

    # Trigger the rollup (core-level — no user-facing "create rollup" API;
    # a real deployment has an adapter, e.g. Claude Code, drive this)
    rollup_id = audit_and_retain_rollup(
        store, "2026-07-01", "2026-07-07", ["weight_kg", "steps"], reasoner=realistic_reasoner
    )

    rollup_before = test_client.get(f"/api/rollups/{rollup_id}").json()
    assert rollup_before["status"] == "draft"
    assert rollup_before["summary"]["entry_count"] == 7
    assert rollup_before["summary"]["numeric_metrics"]["weight_kg"]["trend"] == pytest.approx(-1.0)

    # Human approves
    approve_resp = test_client.post(f"/api/rollups/{rollup_id}/approve", json={"reviewer_notes": "good week"})
    assert approve_resp.status_code == 200

    # Source entries archived, no longer in the default (non-archived) view
    assert test_client.get("/api/entries").json() == []
    # ...but still recoverable — nothing was deleted, only archived
    archived = test_client.get("/api/entries", params={"include_archived": True})
    assert len(archived.json()) == 7

    # Metrics are independent of entry archiving — full history stays
    # available for the dashboard regardless of rollup status
    weight_series = test_client.get("/api/metrics/weight_kg").json()
    assert len(weight_series) == 7
    assert weight_series[-1]["value"] == 82.5

    # Goal reflects the latest weight, not the rollup
    goals = test_client.get("/api/goals", params={"status": "active"}).json()
    assert goals[0]["percent_achieved"] == pytest.approx(
        (83.5 - 82.5) / (83.5 - 73.0) * 100, abs=0.01
    )

    # Rollup itself reflects the approval
    rollup_after = test_client.get(f"/api/rollups/{rollup_id}").json()
    assert rollup_after["status"] == "approved"
    assert rollup_after["reviewer_notes"] == "good week"
