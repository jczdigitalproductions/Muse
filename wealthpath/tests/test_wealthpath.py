"""Focused tests for WealthPath AI: auth, gating, Stripe unlock."""
import json
import sys
import types

import pytest

from app import create_app
from db import SEED_EMAIL, SEED_PASSWORD, get_user_by_email


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("META_MODEL_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app, app.test_client()


def login(client, email=SEED_EMAIL, password=SEED_PASSWORD):
    return client.post(
        "/login", data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_seed_login_redirects_to_dashboard(app_client):
    app, client = app_client
    resp = login(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard")
    dash = client.get("/dashboard")
    assert dash.status_code == 200
    assert SEED_EMAIL.encode() in dash.data


def test_register_login_logout_roundtrip(app_client):
    app, client = app_client
    resp = client.post("/register",
                       data={"email": "new@example.com", "password": "password1"})
    assert resp.status_code == 302
    client.post("/logout")
    assert client.get("/dashboard").status_code == 302
    resp = login(client, "new@example.com", "password1")
    assert resp.status_code == 302
    dup = client.post("/register",
                      data={"email": "new@example.com", "password": "password1"})
    assert b"already registered" in dup.data


def test_generate_requires_login(app_client):
    app, client = app_client
    resp = client.post("/api/generate", json={"target_amount": 50000,
                                              "timeframe": "1Y",
                                              "effort": "all"})
    assert resp.status_code == 401


def test_generate_free_locks_premium(app_client):
    app, client = app_client
    login(client)
    resp = client.post("/api/generate", json={"target_amount": 50000,
                                              "timeframe": "1Y",
                                              "effort": "all"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "$50,000" in data["summary"]
    assert data["is_pro"] is False
    assert data["n_free"] > 0 and data["n_locked"] > 0
    assert [g["key"] for g in data["groups"]] == [
        "bonuses", "capital", "gigs", "startup",
    ]
    for group in data["groups"]:
        for item in group["items"]:
            if item["locked"]:
                assert "detail" not in item
                assert "next_steps" not in item
            else:
                assert item["detail"] and item["next_steps"]


def test_generate_validates_input(app_client):
    app, client = app_client
    login(client)
    bad_amount = client.post("/api/generate", json={"target_amount": 50,
                                                    "timeframe": "1Y",
                                                    "effort": "all"})
    assert bad_amount.status_code == 400
    bad_tf = client.post("/api/generate", json={"target_amount": 50000,
                                                "timeframe": "9Y",
                                                "effort": "all"})
    assert bad_tf.status_code == 400


def test_checkout_without_keys_fails_clearly(app_client):
    app, client = app_client
    login(client)
    resp = client.post("/api/checkout")
    assert resp.status_code == 503
    assert "STRIPE_SECRET_KEY" in resp.get_json()["error"]


def test_webhook_unlocks_pro_and_premium_content(app_client):
    app, client = app_client
    login(client)
    user = get_user_by_email(app.config["DB_PATH"], SEED_EMAIL)
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"user_id": str(user["id"])},
                            "customer": "cus_test123"}},
    }
    resp = client.post("/api/stripe/webhook", data=json.dumps(event),
                       content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json() == {"received": True}
    assert get_user_by_email(app.config["DB_PATH"], SEED_EMAIL)["is_pro"] == 1

    regen = client.post("/api/generate", json={"target_amount": 50000,
                                               "timeframe": "1Y",
                                               "effort": "all"})
    data = regen.get_json()
    assert data["is_pro"] is True
    assert data["n_locked"] == 0
    for group in data["groups"]:
        for item in group["items"]:
            assert item["locked"] is False
            assert item["detail"] and item["next_steps"]
    dash = client.get("/dashboard")
    assert b"PRO" in dash.data


def test_llm_summary_defaults_to_meta_model_api(monkeypatch):
    from strategies import _llm_summary

    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            msg = types.SimpleNamespace(content="AI path summary.")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class FakeOpenAI:
        def __init__(self, base_url=None, api_key=None):
            calls["base_url"] = base_url
            calls["api_key"] = api_key
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    monkeypatch.delenv("META_MODEL_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert _llm_summary(50000, "1 Year", "All effort levels") == "AI path summary."
    assert calls["base_url"] == "https://api.meta.ai/v1"
    assert calls["api_key"] == "test-key"
    assert calls["model"] == "muse-spark-1.3"


def test_llm_summary_absent_without_key(monkeypatch):
    from strategies import _llm_summary

    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert _llm_summary(50000, "1 Year", "All effort levels") is None
