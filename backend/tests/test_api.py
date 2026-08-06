import pytest
from fastapi.testclient import TestClient

from app.main import app

RESPONSE_KEYS = {
    "verdict", "confidence", "reflected", "message_type", "redactions",
    "red_flags", "explanation", "next_steps", "contacts", "similar_scams",
    "kb_freshness", "model_id",
}


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


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
            "/api/analyze", json={"text": "hello", "language": "en"}
        ).json()
        assert 0.0 <= body["confidence"] <= 1.0

    def test_verdict_is_never_safe(self, client):
        body = client.post(
            "/api/analyze", json={"text": "hello", "language": "en"}
        ).json()
        assert body["verdict"] in {"SCAM", "LIKELY_SCAM", "UNCLEAR", "LIKELY_LEGIT"}

    def test_red_flag_shape(self, client):
        body = client.post(
            "/api/analyze", json={"text": "test", "language": "en"}
        ).json()
        for flag in body["red_flags"]:
            assert set(flag) == {"label", "detail", "chunk_id"}

    def test_contact_shape(self, client):
        body = client.post(
            "/api/analyze", json={"text": "test", "language": "en"}
        ).json()
        for contact in body["contacts"]:
            assert set(contact) == {"organisation", "hotline", "url"}

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
        assert "123456" not in body["explanation"]
