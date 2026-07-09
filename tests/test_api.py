import pytest
from fastapi.testclient import TestClient

from api.deps import get_store
from api.main import app
from core.memory_store import MemoryStore
from core.migrate import migrate


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    migrate(db_path)
    store = MemoryStore(db_path)

    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


# -- entries -----------------------------------------------------------------

def test_create_entry_without_classification_falls_back_to_stub(client):
    resp = client.post(
        "/api/entries", json={"date": "2026-07-01", "raw_text": "chest and shoulders day"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "workout" in body["tags"]


def test_create_entry_with_explicit_classification(client):
    resp = client.post(
        "/api/entries",
        json={
            "date": "2026-07-01",
            "raw_text": "205kg leg press",
            "tags": ["workout"],
            "structured": {"weight_kg": 205},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["structured"]["weight_kg"] == 205


def test_list_entries_filters_by_date(client):
    client.post("/api/entries", json={"date": "2026-07-01", "raw_text": "a"})
    client.post("/api/entries", json={"date": "2026-07-10", "raw_text": "b"})

    resp = client.get("/api/entries", params={"start_date": "2026-07-05"})
    assert len(resp.json()) == 1


# -- metrics -------------------------------------------------------------------

def test_add_and_fetch_metric_series(client):
    client.post("/api/metrics", json={"date": "2026-07-01", "metric_name": "weight_kg", "value": 83.5})
    client.post("/api/metrics", json={"date": "2026-07-02", "metric_name": "weight_kg", "value": 83.6})

    resp = client.get("/api/metrics/weight_kg")
    assert resp.status_code == 200
    assert [p["value"] for p in resp.json()] == [83.5, 83.6]


# -- goals --------------------------------------------------------------------

def test_create_goal_and_percent_achieved(client):
    client.post("/api/metrics", json={"date": "2026-07-14", "metric_name": "weight_kg", "value": 80.0})
    resp = client.post(
        "/api/goals",
        json={
            "metric": "weight_kg",
            "start_value": 83.5,
            "start_date": "2026-06-22",
            "target_value": 73.0,
            "target_date": "2026-09-20",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["percent_achieved"] == pytest.approx(33.33, abs=0.1)


def test_goal_percent_achieved_none_without_metric_data(client):
    resp = client.post(
        "/api/goals",
        json={
            "metric": "steps",
            "start_value": 5000,
            "start_date": "2026-06-22",
            "target_value": 10000,
            "target_date": "2026-09-20",
        },
    )
    assert resp.json()["percent_achieved"] is None


# -- rollups -------------------------------------------------------------------

def test_rollup_not_found_returns_404(client):
    assert client.get("/api/rollups/9999").status_code == 404
    assert client.post("/api/rollups/9999/approve", json={}).status_code == 404


def test_approve_rollup_via_api(client):
    client.post("/api/entries", json={"date": "2026-07-05", "raw_text": "leg day"})
    store = MemoryStore(app.dependency_overrides[get_store]().db_path)
    rollup_id = store.add_rollup_draft("2026-07-01", "2026-07-14", {"promoted": []})

    resp = client.post(f"/api/rollups/{rollup_id}/approve", json={"reviewer_notes": "good"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    rollup = client.get(f"/api/rollups/{rollup_id}").json()
    assert rollup["status"] == "approved"
    assert rollup["reviewer_notes"] == "good"
