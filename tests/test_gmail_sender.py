"""Tests for Gmail OAuth sender identity and Gmail transport gating."""

from types import SimpleNamespace

import pytest

from app import create_app
from extensions import db
from services import mail_sender


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://example.com/oauth/callback")
    monkeypatch.setenv("TEST_SEND_RECIPIENTS", "president@example.com, vp@example.com, admin@example.com")
    monkeypatch.setenv("FINAL_SEND_RECIPIENTS", "it-admin@example.com")

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def job_data():
    return {
        "event_name": "HELIOTRACK 2.0",
        "event_date": "2026-10-11",
        "event_start_time": "10:00",
        "event_end_time": "16:00",
        "event_description": "A spring astronomy event.",
        "event_whatsapp_message": "Join us for astronomy talks.",
    }


def _create_rendered_job(client, job_data):
    job_id = client.post("/api/jobs", json=job_data).get_json()["job"]["id"]
    context = {
        "subject": "The Night Sky Awaits",
        "preheader": "Join the astronomy session.",
        "headline": "HELIOTRACK 2.0",
        "intro": "Discover the sky with us.",
        "sections": [{"heading": "What to expect", "body": "Telescope viewing and talks.", "bullets": ["Q&A", "Live viewing"]}],
        "event_details": {"date": "2026-10-11", "time": "10:00", "venue": "PDEU", "registration_url": "https://example.com/register"},
        "cta": {"label": "Register Now", "url": "https://example.com/register"},
        "closing": "See you there.",
    }
    client.put(f"/api/jobs/{job_id}/context", json=context)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    return job_id


def test_oauth_configuration_validation(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(mail_sender.GmailConfigError):
        mail_sender.build_authorization_url()


def test_oauth_authorization_url_includes_required_parameters(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://example.com/oauth/callback")

    url = mail_sender.build_authorization_url(state="test-state")
    assert "accounts.google.com/o/oauth2/v2/auth" in url
    assert "client_id=client-id" in url
    assert "state=test-state" in url
    assert "https%3A%2F%2Fexample.com%2Foauth%2Fcallback" in url


def test_unauthenticated_gmail_session_is_clear(client):
    response = client.get("/api/gmail/session")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["authenticated"] is False
    assert data["sender"] is None


def test_gmail_callback_sets_authenticated_sender(client, monkeypatch):
    sent = {"access_token": "abc", "refresh_token": "refresh", "expires_in": 3600}
    expected_sender = {"email": "brahmand@gmail.com", "display_name": "Brahmand Astronomy Club", "picture_url": "https://example.com/avatar.jpg", "token": sent}

    monkeypatch.setattr(mail_sender, "exchange_code_for_tokens", lambda code: sent)
    monkeypatch.setattr(mail_sender, "get_sender_identity_from_tokens", lambda token_data: expected_sender)

    with client.session_transaction() as session:
        session["gmail_oauth_state"] = "state-123"

    response = client.get("/api/gmail/callback?code=test-code&state=state-123")
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["gmail_sender"]["email"] == expected_sender["email"]


def test_logout_clears_sender_state(client):
    with client.session_transaction() as session:
        session["gmail_sender"] = {"email": "brahmand@gmail.com", "token": {"access_token": "abc"}}

    response = client.post("/api/gmail/logout")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["authenticated"] is False
    with client.session_transaction() as session:
        assert "gmail_sender" not in session


def test_stage_05_approval_requires_gmail_sender(client, job_data):
    job_id = client.post("/api/jobs", json=job_data).get_json()["job"]["id"]
    client.put(f"/api/jobs/{job_id}/context", json={
        "subject": "Hello",
        "preheader": "Welcome",
        "headline": "Headline",
        "intro": "Intro",
        "sections": [],
        "event_details": {"date": "2026-10-11", "time": "10:00", "venue": None, "registration_url": None},
        "cta": {"label": "Register", "url": None},
        "closing": "See you.",
    })
    client.post(f"/api/jobs/{job_id}/email/generate")

    response = client.post(f"/api/jobs/{job_id}/email/approve")
    assert response.status_code == 403
    assert "Gmail sender" in response.get_json()["error"]


def test_stage_06_test_send_requires_auth_and_configured_recipients(client, app, job_data, monkeypatch):
    job_id = _create_rendered_job(client, job_data)
    with app.app_context():
        from models.email_job import EmailJob
        job = db.session.get(EmailJob, job_id)
        job.status = "EMAIL_APPROVED"
        db.session.commit()

    with client.session_transaction() as session:
        session["gmail_sender"] = {"email": "brahmand@gmail.com", "token": {"access_token": "abc"}}

    monkeypatch.setattr(mail_sender, "get_test_recipient_emails", lambda: [])
    response = client.post(f"/api/jobs/{job_id}/test-send")
    assert response.status_code == 400
    assert "No Stage 06" in response.get_json()["error"]


def test_stage_07_final_send_requires_auth_and_configured_recipients(client, app, job_data, monkeypatch):
    job_id = _create_rendered_job(client, job_data)
    with app.app_context():
        from models.email_job import EmailJob
        job = db.session.get(EmailJob, job_id)
        job.status = "TEST_APPROVED"
        db.session.commit()

    with client.session_transaction() as session:
        session["gmail_sender"] = {"email": "brahmand@gmail.com", "token": {"access_token": "abc"}}

    monkeypatch.setattr(mail_sender, "get_final_recipient_emails", lambda: [])
    response = client.post(f"/api/jobs/{job_id}/final-send")
    assert response.status_code == 400
    assert "No final recipient" in response.get_json()["error"]


def test_mail_sender_builds_mime_for_job():
    sender = {"email": "brahmand@gmail.com", "display_name": "Brahmand Astronomy Club", "token": {"access_token": "abc"}}
    job = SimpleNamespace(email_html="<html><body><h1>Unicode — 星空</h1></body></html>", email_context={"subject": "Unicode subject"})

    message = mail_sender.build_message_for_job(sender, job, ["friend@example.com"])

    payload = message.as_string()
    assert "From: brahmand@gmail.com" in payload
    assert "To: friend@example.com" in payload
    assert str(message["Subject"]) == "Unicode subject"
    assert "Unicode" in payload


def test_send_mime_message_uses_base64url_payload(monkeypatch):
    sender = {"email": "brahmand@gmail.com", "token": {"access_token": "abc", "refresh_token": "refresh"}}

    class DummyCreds:
        valid = True
        expired = False
        refresh_token = "refresh"
        token = "abc"
        expiry = None

    class FakeSendCall:
        def __init__(self):
            self.body = None

        def execute(self):
            return {"id": "123", "threadId": "t-123"}

        def send(self, userId, body):
            self.body = body
            return self

        def users(self):
            return self

        def messages(self):
            return self

    service = FakeSendCall()
    monkeypatch.setattr(mail_sender, "_credentials_from_token_data", lambda token_data: DummyCreds())
    monkeypatch.setattr(mail_sender, "build", lambda *args, **kwargs: service)

    message = mail_sender.build_message_for_job(
        sender,
        SimpleNamespace(email_html="<html><body>Test</body></html>", email_context={"subject": "Hello"}),
        ["friend@example.com"],
    )

    result = mail_sender.send_mime_message(sender, message)
    assert result["success"] is True
    assert result["message_id"] == "123"
    assert service.body["raw"]
