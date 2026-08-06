import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import app.main as main
from app.graph.build import build_graph
from app.main import app
from app.retrieval.store import ChunkStore

RESPONSE_KEYS = {
    "verdict", "confidence", "reflected", "message_type", "redactions",
    "redacted_text", "red_flags", "explanation", "next_steps", "contacts",
    "similar_scams", "kb_freshness", "model_id",
}

CONCEPTS = json.dumps(["claims account suspended", "urgency deadline"])
DETECT = json.dumps({
    "verdict": "SCAM",
    "confidence": 0.91,
    "red_flags": [
        {"label": "Claims your account is on hold",
         "detail": "Real suspensions appear when you log in.",
         "chunk_id": "lure-account-suspended"}
    ],
    "low_confidence_reason": None,
})
ADVISE = json.dumps({
    "explanation": "Scam po ito.",
    "next_steps": ["Huwag i-click ang link.", "I-block ang sender."],
})


@pytest.fixture
def client(kb_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("KB_PATH", str(kb_path))
    get_settings.cache_clear()

    def fake_graph():
        model = FakeListChatModel(responses=[CONCEPTS, DETECT, ADVISE] * 10)
        return build_graph(model, ChunkStore(kb_path))

    monkeypatch.setattr(main, "get_graph", fake_graph)
    yield TestClient(app, raise_server_exceptions=False)
    get_settings.cache_clear()


class TestHealth:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMeta:
    def test_meta_shape(self, client):
        response = client.get("/api/meta")
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"kb_freshness", "model_id", "chunk_count"}
        assert body["chunk_count"] > 0


class TestAnalyze:
    def test_response_has_every_documented_key(self, client):
        response = client.post(
            "/api/analyze",
            json={"text": "BDO ALERT: Your account is on hold", "language": "tl"},
        )
        assert response.status_code == 200
        assert set(response.json()) == RESPONSE_KEYS

    def test_confidence_within_bounds(self, client):
        body = client.post(
            "/api/analyze", json={"text": "hello there", "language": "en"}
        ).json()
        assert 0.0 <= body["confidence"] <= 1.0

    def test_verdict_is_a_documented_value(self, client):
        body = client.post(
            "/api/analyze", json={"text": "hello there", "language": "en"}
        ).json()
        assert body["verdict"] in {"SCAM", "LIKELY_SCAM", "UNCLEAR", "LIKELY_LEGIT"}

    def test_red_flag_shape(self, client):
        body = client.post(
            "/api/analyze", json={"text": "test message", "language": "en"}
        ).json()
        assert body["red_flags"]
        for flag in body["red_flags"]:
            assert set(flag) == {"label", "detail", "chunk_id"}

    def test_contacts_from_keyed_lookup(self, client):
        body = client.post(
            "/api/analyze", json={"text": "test message", "language": "en"}
        ).json()
        orgs = [c["organisation"] for c in body["contacts"]]
        assert "Inter-Agency Response Center (I-ARC)" in orgs
        for contact in body["contacts"]:
            assert set(contact) == {"organisation", "hotline", "url"}

    def test_similar_scams_are_message_examples(self, client):
        body = client.post(
            "/api/analyze",
            json={"text": "Deposit now and win jackpot free bonus casino", "language": "en"},
        ).json()
        assert len(body["similar_scams"]) <= 3
        for scam in body["similar_scams"]:
            assert set(scam) == {"text", "scam_type"}

    def test_empty_text_rejected_without_echo(self, client):
        response = client.post("/api/analyze", json={"text": "", "language": "en"})
        assert response.status_code == 422
        body = response.json()
        assert set(body) == {"error"}
        assert set(body["error"]) == {"code", "message"}

    def test_missing_body_rejected(self, client):
        response = client.post("/api/analyze", json={})
        assert response.status_code == 422
        assert "error" in response.json()

    def test_invalid_language_rejected(self, client):
        response = client.post(
            "/api/analyze", json={"text": "test", "language": "fr"}
        )
        assert response.status_code == 422

    def test_redactions_reported_as_labels_only(self, client):
        body = client.post(
            "/api/analyze",
            json={"text": "Your OTP is 123456", "language": "en"},
        ).json()
        assert body["redactions"] == ["OTP"]

    def test_redacted_text_never_contains_the_value(self, client):
        body = client.post(
            "/api/analyze",
            json={"text": "Your OTP is 123456", "language": "en"},
        ).json()
        assert "123456" not in body["redacted_text"]
        assert "[OTP]" in body["redacted_text"]

    def test_pipeline_failure_never_echoes_input(self, client, monkeypatch):
        secret = "my OTP is 987654 do not tell anyone"

        def broken_graph():
            raise RuntimeError(f"provider error echoing {secret}")

        monkeypatch.setattr(main, "get_graph", broken_graph)
        response = client.post(
            "/api/analyze", json={"text": secret, "language": "en"}
        )
        assert response.status_code == 500
        assert secret not in response.text
        assert "987654" not in response.text
