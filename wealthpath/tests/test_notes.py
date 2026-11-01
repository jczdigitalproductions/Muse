"""Structured-notes feature: page, analysis API, validation."""
import pytest

from app import create_app
from db import SEED_EMAIL, SEED_PASSWORD


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app, app.test_client()


def login(client):
    return client.post("/login", data={"email": SEED_EMAIL,
                                       "password": SEED_PASSWORD})


def test_notes_page_requires_login(app_client):
    app, client = app_client
    assert client.get("/notes").status_code == 302
    login(client)
    resp = client.get("/notes")
    assert resp.status_code == 200
    assert b"Structured Notes" in resp.data
    assert b"WealthPath" in resp.data  # integrated nav shows both features


def test_analyze_api_requires_login(app_client):
    app, client = app_client
    resp = client.post("/api/notes/analyze", json={"use_sample": True})
    assert resp.status_code == 401


def test_analyze_sample_end_to_end(app_client):
    app, client = app_client
    login(client)
    resp = client.post("/api/notes/analyze", json={
        "use_sample": True, "n_paths": 500, "heat_n": 2, "heat_paths": 200,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["extraction"] == "regex"
    assert data["terms"]["underlyings"] == ["SPX", "NDX", "RTY"]
    assert data["terms"]["coupon_rate"] == pytest.approx(0.095)
    assert 500 < data["metrics"]["price"] < 1300
    assert 0 <= data["metrics"]["p_autocall"] <= 1
    assert len(data["stress"]) == 6
    assert {r["regime"] for r in data["stress"]} >= {"GFC 2008", "Base (2024)"}
    assert data["verification"]["passed"] is True
    assert len(data["charts"]["payoff"]) > 1000
    assert len(data["charts"]["heatmap"]) > 1000


def test_analyze_validates_input(app_client):
    app, client = app_client
    login(client)
    short = client.post("/api/notes/analyze", json={"text": "tiny"})
    assert short.status_code == 400
    bad_paths = client.post("/api/notes/analyze",
                            json={"use_sample": True, "n_paths": 10})
    assert bad_paths.status_code == 400
    bad_heat = client.post("/api/notes/analyze",
                           json={"use_sample": True, "heat_n": 50})
    assert bad_heat.status_code == 400
