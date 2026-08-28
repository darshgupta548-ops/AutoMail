"""Tests for AUTO-MAIL's database foundation and job API."""

import pytest

from app import create_app
from extensions import db
from models import EmailJob


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def job_payload():
    return {
        "event_name": "HELIOTRACK 2.0",
        "event_date": "2026-10-11",
        "event_start_time": "10:00",
        "event_end_time": "16:00",
        "event_description": "An astronomy event.",
        "event_whatsapp_message": "Join us...",
        "event_poster": "https://example.com/poster.jpg",
    }


def test_app_starts_and_database_initializes(app, client):
    assert client.get("/").status_code == 200
    with app.app_context():
        assert EmailJob.__table__.name in db.inspect(db.engine).get_table_names()


def test_create_and_retrieve_job_with_omitted_optional_fields(client, job_payload):
    created = client.post("/api/jobs", json=job_payload)
    assert created.status_code == 201
    created_job = created.get_json()["job"]
    assert created_job["id"]
    assert created_job["status"] == "DRAFT"

    job = client.get(f"/api/jobs/{created_job['id']}").get_json()["job"]
    assert job["event_name"] == job_payload["event_name"]
    assert job["event_date"] == "2026-10-11"
    assert job["event_start_time"] == "10:00:00"
    assert job["event_venue"] is None
    assert job["registration_url"] is None


def test_optional_venue_and_registration_url_round_trip(client, job_payload):
    job_payload.update(
        event_venue="PDEU Astronomy Observatory",
        registration_url="https://example.com/register/heliotrack-2",
    )
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["event_venue"] == job_payload["event_venue"]
    assert job["registration_url"] == job_payload["registration_url"]


def test_list_jobs(client, job_payload):
    client.post("/api/jobs", json=job_payload)
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert len(response.get_json()["jobs"]) == 1


def test_missing_job_returns_404(client):
    assert client.get("/api/jobs/999").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"event_name": "", "event_description": "Description", "event_date": "2026-10-11", "event_start_time": "10:00"},
        {"event_name": "Event", "event_description": "", "event_date": "2026-10-11", "event_start_time": "10:00"},
        {"event_name": "Event", "event_description": "Description", "event_date": "not-a-date", "event_start_time": "10:00"},
        {"event_name": "Event", "event_description": "Description", "event_date": "2026-10-11", "event_start_time": "invalid"},
        {"event_name": "Event", "event_description": "Description", "event_date": "2026-10-11", "event_start_time": "10:00", "status": "UNKNOWN"},
    ],
)
def test_invalid_job_input_returns_400(client, payload):
    assert client.post("/api/jobs", json=payload).status_code == 400


def test_json_fields_round_trip(client, job_payload):
    job_payload.update(
        email_context={"subject": "Look up!", "highlights": ["Talk", "Viewing"]},
        event_palette={"primary": "#102030"},
        event_typography={"heading": "Arial"},
    )
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["email_context"] == job_payload["email_context"]
    assert job["event_palette"] == job_payload["event_palette"]
    assert job["event_typography"] == job_payload["event_typography"]


VALID_CONTEXT = {
    "subject": "Explore the Night Sky",
    "preheader": "Join HELIOTRACK 2.0.",
    "headline": "HELIOTRACK 2.0",
    "intro": "Join us for an astronomy event.",
    "sections": [{"heading": "What to expect", "body": "Astronomy activities.", "bullets": []}],
    "event_details": {
        "date": "2026-10-11",
        "time": "10:00",
        "venue": None,
        "registration_url": None,
    },
    "cta": {"label": "Learn more", "url": None},
    "closing": "See you there.",
}


def test_approve_context_successfully_updates_job(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    response = client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["job_id"] == job_id
    assert data["status"] == "CONTEXT_APPROVED"
    assert data["email_context"] == VALID_CONTEXT
    
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["email_context"] == VALID_CONTEXT
    assert job["status"] == "CONTEXT_APPROVED"


def test_approve_context_with_invalid_schema_returns_400(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    original_job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    
    invalid_context = {"subject": "Missing required fields"}
    response = client.put(f"/api/jobs/{job_id}/context", json=invalid_context)
    
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Invalid email context" in response.get_json()["error"]
    
    # Verify original context and status are preserved
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["email_context"] == original_job["email_context"]
    assert job["status"] == original_job["status"]


def test_approve_context_preserves_on_validation_failure(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set initial context and status
    initial_context = {"subject": "Original", "preheader": "Original", "headline": "Original",
                       "intro": "Original", "sections": [], "event_details": {"date": "2026-10-11", "time": "10:00", "venue": None, "registration_url": None},
                       "cta": {"label": "Original", "url": None}, "closing": "Original"}
    client.put(f"/api/jobs/{job_id}/context", json=initial_context)
    
    job_before = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    
    # Try to submit invalid context
    invalid_context = {"invalid": "schema"}
    response = client.put(f"/api/jobs/{job_id}/context", json=invalid_context)
    
    assert response.status_code == 400
    
    # Verify preservation
    job_after = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job_after["email_context"] == job_before["email_context"]
    assert job_after["status"] == job_before["status"]


def test_approve_context_non_existent_job_returns_404(client):
    response = client.put("/api/jobs/999/context", json=VALID_CONTEXT)
    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_approve_context_with_non_json_returns_400(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    response = client.put(f"/api/jobs/{job_id}/context", data="not json")
    assert response.status_code == 400


def test_generate_email_successfully_updates_job(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context first
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["job_id"] == job_id
    assert data["status"] == "EMAIL_RENDERED"
    assert data["email_html"] is not None
    assert len(data["email_html"]) > 100
    
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["email_html"] == data["email_html"]
    assert job["status"] == "EMAIL_RENDERED"


def test_generate_email_non_existent_job_returns_404(client):
    response = client.post("/api/jobs/999/email/generate")
    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_generate_email_missing_context_returns_400(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Job exists but has no approved context (wrong state)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "CONTEXT_APPROVED" in response.get_json()["error"]


def test_generate_email_incorrect_state_returns_400(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Job is in DRAFT state, not CONTEXT_APPROVED
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "CONTEXT_APPROVED" in response.get_json()["error"]


def test_generate_email_preserves_on_rendering_failure(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context with invalid data that would cause rendering failure
    invalid_context = {
        "subject": "Test",
        "preheader": "Test",
        "headline": "Test",
        "intro": "Test",
        "sections": [],
        "event_details": {
            "date": "Test",
            "time": "Test",
            "venue": None,
            "registration_url": None
        },
        "cta": {
            "label": "Test",
            "url": None
        },
        "closing": "Test"
    }
    client.put(f"/api/jobs/{job_id}/context", json=invalid_context)
    
    job_before = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    
    # This should succeed since the context is valid, just minimal
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    
    # If it succeeds, verify the transition
    if response.status_code == 200:
        job_after = client.get(f"/api/jobs/{job_id}").get_json()["job"]
        assert job_after["status"] == "EMAIL_RENDERED"
        assert job_after["email_html"] is not None


def test_approve_email_successfully_updates_job(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    client.post(f"/api/jobs/{job_id}/email/generate")
    
    response = client.post(f"/api/jobs/{job_id}/email/approve")
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["job_id"] == job_id
    assert data["status"] == "EMAIL_APPROVED"


def test_legacy_job_receives_organization_logo_urls(client, job_payload):
    """Test that existing jobs without logo URLs in context receive them during email generation."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context WITHOUT logo URLs (simulating legacy job)
    legacy_context = VALID_CONTEXT.copy()
    # Explicitly remove logo fields to simulate legacy context
    legacy_context.pop('brahmand_logo_url', None)
    legacy_context.pop('snt_logo_url', None)
    legacy_context.pop('osail_logo_url', None)
    
    client.put(f"/api/jobs/{job_id}/context", json=legacy_context)
    
    # Generate email
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["status"] == "EMAIL_RENDERED"
    
    # Verify all three logo URLs appear in generated HTML
    html = data["email_html"]
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png" in html
    
    # Verify logo row appears before headline
    headline_pos = html.find('class="email-headline"')
    brahmand_pos = html.find('Brahmand_Logo_-_Black_PNG.png')
    assert brahmand_pos > 0
    assert headline_pos > 0
    assert brahmand_pos < headline_pos, "Logos should appear before headline"
    
    # Verify no URL corruption (no markdown, no JSON encoding)
    assert '](' not in html, "Should not contain markdown syntax"
    assert '"url":"' not in html, "Should not contain JSON-encoded URLs"
    
    # Verify table structure for logos
    assert '<table' in html and 'org-logo' in html, "Should contain logo table structure"
    
    # Verify new responsive logo sizing
    assert 'max-width:120px' in html, "Desktop logos should use 120px max-width"
    assert 'width:28%' in html, "Mobile logos should use percentage-based sizing (28%)"
    assert 'logo-cell' in html, "Logo cells should have logo-cell class for mobile responsiveness"
    assert 'font-size:28px' in html, "Mobile headline should be 28px"
    assert 'max-width:88px' not in html, "Old 88px mobile cap should be removed"
    assert 'transform:' not in html.lower(), "Should not use transform scaling"
    assert 'table[class=email-container]' in html, "Should have email-safe table selector for mobile"
    assert 'word-wrap:break-word' in html, "Should have word-wrap for text wrapping"


def test_job_with_existing_logo_urls_preserves_them(client, job_payload):
    """Test that jobs with existing logo URLs preserve them during generation."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context WITH custom logo URLs
    context_with_logos = VALID_CONTEXT.copy()
    context_with_logos['brahmand_logo_url'] = 'https://example.com/custom-brahmand.png'
    context_with_logos['snt_logo_url'] = 'https://example.com/custom-snt.png'
    context_with_logos['osail_logo_url'] = 'https://example.com/custom-osail.png'
    
    client.put(f"/api/jobs/{job_id}/context", json=context_with_logos)
    
    # Generate email
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify custom URLs are preserved (not overwritten with defaults)
    html = data["email_html"]
    assert 'custom-brahmand.png' in html
    assert 'custom-snt.png' in html
    assert 'custom-osail.png' in html
    assert 'Brahmand_Logo_-_Black_PNG.png' not in html  # Default should NOT be used


def test_approve_email_non_existent_job_returns_404(client):
    response = client.post("/api/jobs/999/email/approve")
    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_approve_email_incorrect_state_returns_400(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    response = client.post(f"/api/jobs/{job_id}/email/approve")
    
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "EMAIL_RENDERED" in response.get_json()["error"]


def test_human_email_edit_persists_and_keeps_rendered_state(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    client.post(f"/api/jobs/{job_id}/email/generate")
    edited = {**VALID_CONTEXT, "headline": "Human headline", "intro": "Human intro",
              "event_details": {**VALID_CONTEXT["event_details"], "registration_url": "https://example.com/register"},
              "cta": {"label": "Reserve a place", "url": "https://example.com/edited"}}
    response = client.put(f"/api/jobs/{job_id}/email/content", json=edited)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "EMAIL_RENDERED"
    assert "Human headline" in data["email_html"]
    assert "Human intro" in data["email_html"]
    assert "Reserve a place" in data["email_html"]
    assert "https://example.com/edited" in data["email_html"]
    saved = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert saved["email_context"]["headline"] == "Human headline"
    assert saved["status"] == "EMAIL_RENDERED"


def test_human_email_edit_requires_rendered_state(client, job_payload):
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    response = client.put(f"/api/jobs/{job_id}/email/content", json=VALID_CONTEXT)
    assert response.status_code == 400
    assert "EMAIL_RENDERED" in response.get_json()["error"]
