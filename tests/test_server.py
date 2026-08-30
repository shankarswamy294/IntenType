import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from pathlib import Path


@pytest.fixture
def client(tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        from daemon import server
        import importlib; importlib.reload(server)
        yield TestClient(server.app)


def test_get_settings_returns_defaults(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["whisper_model"] == "small.en"
    assert data["openai_api_key"] == ""


def test_post_settings_saves_model(client, tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        resp = client.post("/api/settings", json={"whisper_model": "medium.en"})
    assert resp.status_code == 200
    resp2 = client.get("/api/settings")
    assert resp2.json()["whisper_model"] == "medium.en"


def test_api_key_is_masked_in_get(client, tmp_path):
    with patch("daemon.settings.SETTINGS_PATH", tmp_path / "settings.json"), \
         patch("daemon.settings.APP_SUPPORT", tmp_path):
        client.post("/api/settings", json={"openai_api_key": "sk-realkey123"})
        resp = client.get("/api/settings")
    assert "sk-realkey123" not in resp.json()["openai_api_key"]


def test_history_starts_empty(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_and_retrieve_history_entry(client):
    from daemon import server
    server.add_history_entry({
        "timestamp": "2026-08-30T10:00:00",
        "app": "Slack",
        "tone": "Casual",
        "raw": "um hello",
        "polished": "Hello.",
    })
    resp = client.get("/api/history")
    assert len(resp.json()) == 1
    assert resp.json()[0]["app"] == "Slack"


def test_clear_history(client):
    from daemon import server
    server.add_history_entry({"timestamp": "t", "app": "A", "tone": "Casual",
                               "raw": "r", "polished": "p"})
    client.post("/api/history/clear")
    assert client.get("/api/history").json() == []


def test_get_tones_returns_all_builtins(client):
    resp = client.get("/api/tones")
    data = resp.json()
    assert "Formal" in data
    assert "Casual" in data
    assert "Terse" in data
