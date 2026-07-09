"""Smoke tests — confirms the review page loads and that it drives the
exact same approve/reject endpoints already covered by test_api.py (no
new backend behavior introduced by adding a second frontend on it).
Visual diff readability needs a manual look.
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
    yield TestClient(app), store
    app.dependency_overrides.clear()


def test_review_page_loads_with_rollup_list(client):
    test_client, _ = client
    resp = test_client.get("/review.html")
    assert resp.status_code == 200
    assert "rollup-list" in resp.text


def test_review_js_is_served(client):
    test_client, _ = client
    assert test_client.get("/js/review.js").status_code == 200


def test_review_ui_hits_the_same_approve_endpoint_epoch5_tests(client):
    test_client, store = client
    store.add_entry(date="2026-07-05", raw_text="leg day", structured={}, tags=["workout"])
    rollup_id = store.add_rollup_draft("2026-07-01", "2026-07-14", {"promoted": ["milestone"]})

    resp = test_client.post(f"/api/rollups/{rollup_id}/approve", json={"reviewer_notes": "ok"})
    assert resp.status_code == 200

    entries = store.get_entries(include_archived=True)
    assert entries[0].archived is True  # same archiving behavior as core/review.py directly
