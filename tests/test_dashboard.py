"""Smoke tests only — ECharts rendering, scroll, and zoom feel need a
real browser and can't be verified headlessly from here. This confirms
the page loads, references the right chart containers/scripts, and
that the underlying data endpoints return series shaped the way
charts.js expects.
"""
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


def test_dashboard_page_loads_with_chart_containers(client):
    resp = client.get("/dashboard.html")
    assert resp.status_code == 200
    assert "chart-weight" in resp.text
    assert "chart-steps" in resp.text
    assert "goal-list" in resp.text


def test_charts_js_is_served(client):
    assert client.get("/js/charts.js").status_code == 200


def test_metric_series_shape_matches_what_charts_js_expects(client):
    client.post("/api/metrics", json={"date": "2026-07-01", "metric_name": "weight_kg", "value": 83.5})
    resp = client.get("/api/metrics/weight_kg")
    points = resp.json()
    assert points and set(points[0].keys()) == {"date", "value"}
