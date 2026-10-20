import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.database import (
    get_contact_submissions,
    init_db,
    save_contact_submission,
)
from src.backend.main import app
from src.backend.security import (
    InMemoryRateLimiter,
    anonymize_ip,
    contact_rate_limiter,
    verify_cloudflare_turnstile,
)


def test_database_save_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_contacts.db"
        init_db(test_db)

        sub_id = save_contact_submission(
            email="jan.kowalski@example.com",
            category="sugestia",
            message="Fajny serwis, proszę dodać więcej partii!",
            rodo_consent=True,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 Test",
            custom_path=test_db,
        )
        assert sub_id == 1

        submissions = get_contact_submissions(custom_path=test_db)
        assert len(submissions) == 1
        item = submissions[0]
        assert item["email"] == "jan.kowalski@example.com"
        assert item["category"] == "sugestia"
        assert item["message"] == "Fajny serwis, proszę dodać więcej partii!"
        assert item["rodo_consent"] == 1
        assert item["ip_address"] == "192.168.1.1"


def test_rate_limiter():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    client_ip = "10.0.0.1"

    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is False

    # Another IP should still be allowed
    assert limiter.is_allowed("10.0.0.2") is True


def test_anonymize_ip():
    anon1 = anonymize_ip("192.168.1.50")
    anon2 = anonymize_ip("192.168.1.50")
    anon3 = anonymize_ip("192.168.1.51")

    assert anon1 == anon2
    assert anon1 != anon3
    assert anon1.startswith("anon_")
    assert anonymize_ip(None) == "anonymous"


def test_turnstile_dev_bypass():
    # When no secret is configured, should pass in dev/test
    ok, msg = verify_cloudflare_turnstile("dummy-token", remote_ip="127.0.0.1")
    assert ok is True


def test_contact_api_success():
    client = TestClient(app)
    contact_rate_limiter.reset()

    payload = {
        "email": "kontakt@obywatel.pl",
        "category": "nowa_funkcja",
        "message": "Czy planujecie dodać statystyki frekwencji posłów?",
        "rodo_consent": True,
        "turnstile_token": "token-test",
    }

    response = client.post("/api/contact", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "submission_id" in data
    assert data["submission_id"] is not None


def test_contact_api_validation_error():
    client = TestClient(app)
    contact_rate_limiter.reset()

    # Missing RODO consent or invalid message length
    payload = {
        "email": "kontakt@obywatel.pl",
        "category": "pytanie",
        "message": "Krótko",  # min_length is 10
        "rodo_consent": False,
    }

    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422  # Pydantic validation failure on min_length


def test_contact_api_honeypot_drops_spam_silently():
    client = TestClient(app)
    contact_rate_limiter.reset()

    payload = {
        "email": "bot@spammer.com",
        "category": "pytanie",
        "message": "Kup tanie leki i kliknij w ten podejrzany link!",
        "rodo_consent": True,
        "honeypot": "http://spam-link.com",  # Honeypot filled by bot
    }

    response = client.post("/api/contact", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    # Notice: submission_id is None because it was not stored in the database!
    assert data.get("submission_id") is None


def test_contact_api_rate_limiting():
    client = TestClient(app)
    contact_rate_limiter.reset()

    payload = {
        "email": "user@example.com",
        "category": "pytanie",
        "message": "Pytanie numer 12345 do serwisu.",
        "rodo_consent": True,
    }

    # Simulate 5 allowed requests
    for _ in range(5):
        resp = client.post(
            "/api/contact", json=payload, headers={"x-forwarded-for": "198.51.100.1"}
        )
        assert resp.status_code == 200

    # 6th request from the same IP must be rejected with 429
    resp = client.post(
        "/api/contact", json=payload, headers={"x-forwarded-for": "198.51.100.1"}
    )
    assert resp.status_code == 429
    assert "Zbyt wiele zapytań" in resp.json()["detail"]
