"""Smoke tests for the static frontend mount — confirms the HTML is
served and API routes still resolve correctly once the catch-all static
mount is registered. Visual/interactive behavior (does the form actually
submit correctly in a browser, does the list render right) needs a
manual click-through — not something this can verify.
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


def test_root_serves_index_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Anamnesis" in resp.text
    assert "entry-form" in resp.text


def test_static_assets_are_served(client):
    assert client.get("/css/style.css").status_code == 200
    assert client.get("/js/api.js").status_code == 200
    assert client.get("/js/entries.js").status_code == 200


def test_api_routes_still_work_after_static_mount(client):
    resp = client.post("/api/entries", json={"date": "2026-07-01", "raw_text": "leg day"})
    assert resp.status_code == 200
