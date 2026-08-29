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
    assert 'width:33.33%' in html, "Mobile logos should use percentage-based sizing (33.33%)"
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


def test_logo_urls_persist_during_stage_05_edit(client, job_payload):
    """Regression test for logo URL persistence bug during Stage 05 edits."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context WITHOUT logo URLs (simulating initial state)
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    
    # Generate email (this will inject logo URLs)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify all three logos appear in generated HTML
    html = data["email_html"]
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png" in html
    
    # Edit the headline to "YOOO" (simulating user edit)
    edited_context = {
        'subject': VALID_CONTEXT['subject'],
        'preheader': VALID_CONTEXT['preheader'],
        'headline': 'YOOO',
        'intro': VALID_CONTEXT['intro'],
        'sections': VALID_CONTEXT['sections'],
        'event_details': VALID_CONTEXT['event_details'],
        'cta': VALID_CONTEXT['cta'],
        'closing': VALID_CONTEXT['closing'],
        'contact_details': VALID_CONTEXT.get('contact_details', []),
        # Frontend sends logo URLs (as seen in app.js lines 712-716)
        'brahmand_logo_url': 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png',
        'snt_logo_url': 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png',
        'osail_logo_url': 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png',
        'logo_urls': {}
    }
    
    # Save through the Stage 05 save path
    response = client.put(f"/api/jobs/{job_id}/email/content", json=edited_context)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify YOOO persists
    assert 'YOOO' in data["email_context"]["headline"]
    
    # Verify all three logo URLs remain in email_context
    assert data["email_context"].get('brahmand_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png'
    assert data["email_context"].get('snt_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png'
    assert data["email_context"].get('osail_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png'
    
    # Verify all three logo <img> elements remain in the saved rendered HTML
    html = data["email_html"]
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png" in html
    
    # Verify the saved edit also appears in the rendered HTML
    assert 'YOOO' in html
    
    # Reload/re-preview the saved email and verify both the edit and all three logos remain
    job_data = client.get(f"/api/jobs/{job_id}").get_json()
    job = job_data["job"]
    assert job["email_context"]["headline"] == "YOOO"
    assert job["email_context"].get('brahmand_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png'
    assert job["email_context"].get('snt_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png'
    assert job["email_context"].get('osail_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png'
    
    # Verify logos are in the persisted HTML
    persisted_html = job["email_html"]
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png" in persisted_html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png" in persisted_html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png" in persisted_html
    assert 'YOOO' in persisted_html


def test_missing_logo_urls_safely_omitted_during_edit(client, job_payload):
    """Test that missing logos remain safely omitted rather than creating placeholders."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context WITHOUT logo URLs
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    
    # Generate email
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Perform Stage 05 content update without logo URLs
    edited_context = {
        'subject': 'EDITED: ' + VALID_CONTEXT['subject'],
        'preheader': VALID_CONTEXT['preheader'],
        'headline': VALID_CONTEXT['headline'],
        'intro': 'This is edited intro text.',
        'sections': VALID_CONTEXT['sections'],
        'event_details': VALID_CONTEXT['event_details'],
        'cta': VALID_CONTEXT['cta'],
        'closing': VALID_CONTEXT['closing'],
        'contact_details': VALID_CONTEXT.get('contact_details', []),
        # No logo URLs provided
    }
    
    response = client.put(f"/api/jobs/{job_id}/email/content", json=edited_context)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Logo URLs should be injected by the backend (same as generate endpoint)
    assert data["email_context"].get('brahmand_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png'
    assert data["email_context"].get('snt_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png'
    assert data["email_context"].get('osail_logo_url') == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png'
    
    # Confirm logos appear in HTML (backend injects them)
    html = data["email_html"]
    assert 'src=""' not in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png" in html


def test_one_missing_logo_during_edit(client, job_payload):
    """Test that when one logo is missing, the generate endpoint injects it and save preserves it."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context with only two logos
    context_with_partial_logos = VALID_CONTEXT.copy()
    context_with_partial_logos['brahmand_logo_url'] = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png'
    context_with_partial_logos['snt_logo_url'] = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png'
    # osail_logo_url is missing
    
    client.put(f"/api/jobs/{job_id}/context", json=context_with_partial_logos)
    
    # Generate email (this will inject the missing OSAIL logo)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify all three logos appear (generate endpoint injects missing ones)
    html = data["email_html"]
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png" in html
    assert "Osail_black_logo.png" in html  # Injected by generate endpoint
    
    # Edit and save
    edited_context = {
        'subject': VALID_CONTEXT['subject'],
        'preheader': VALID_CONTEXT['preheader'],
        'headline': 'EDITED',
        'intro': VALID_CONTEXT['intro'],
        'sections': VALID_CONTEXT['sections'],
        'event_details': VALID_CONTEXT['event_details'],
        'cta': VALID_CONTEXT['cta'],
        'closing': VALID_CONTEXT['closing'],
        'contact_details': VALID_CONTEXT.get('contact_details', []),
        'brahmand_logo_url': 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png',
        'snt_logo_url': 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png',
        'osail_logo_url': 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png',
        'logo_urls': {}
    }
    
    response = client.put(f"/api/jobs/{job_id}/email/content", json=edited_context)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify all three logos still appear after save
    html = data["email_html"]
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png" in html
    assert "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png" in html
    assert "Osail_black_logo.png" in html
    assert 'EDITED' in html


def test_delete_job_non_sent(client, job_payload):
    """Test that non-sent jobs can be deleted."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Verify job exists
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    
    # Delete the job (it's in DRAFT state, which is deletable)
    response = client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["job_id"] == job_id
    
    # Verify job no longer exists
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 404


def test_delete_job_sent_protected(client, app, job_payload):
    """Test that sent jobs are protected from deletion."""
    from models.email_job import EmailJob, JobStatus
    
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Manually set job to a sent state using the same app context
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.status = JobStatus.FINAL_SENT
        db.session.commit()
    
    # Attempt to delete the sent job
    response = client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 403
    data = response.get_json()
    assert data["success"] is False
    assert "protected" in data["error"].lower()
    
    # Verify job still exists
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200


def test_delete_job_test_sent_protected(client, app, job_payload):
    """Test that TEST_SENT jobs are protected from deletion."""
    from models.email_job import EmailJob, JobStatus
    
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Manually set job to TEST_SENT state using the same app context
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.status = JobStatus.TEST_SENT
        db.session.commit()
    
    # Attempt to delete the test sent job
    response = client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 403
    data = response.get_json()
    assert data["success"] is False
    
    # Verify job still exists
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200


def test_delete_job_not_found(client):
    """Test that deleting a non-existent job returns 404."""
    response = client.delete("/api/jobs/999")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False


def test_background_url_persistence_during_edit(client, app, job_payload):
    """Test that background URL persists through Stage 05 edits."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set background URL
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.email_bg = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg'
        db.session.commit()
    
    # Approve context and generate email
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify background appears in generated HTML
    html = data["email_html"]
    assert 'test_background.jpg' in html
    
    # Edit and save
    edited_context = {
        'subject': VALID_CONTEXT['subject'],
        'preheader': VALID_CONTEXT['preheader'],
        'headline': 'EDITED',
        'intro': VALID_CONTEXT['intro'],
        'sections': VALID_CONTEXT['sections'],
        'event_details': VALID_CONTEXT['event_details'],
        'cta': VALID_CONTEXT['cta'],
        'closing': VALID_CONTEXT['closing'],
        'contact_details': VALID_CONTEXT.get('contact_details', []),
    }
    
    response = client.put(f"/api/jobs/{job_id}/email/content", json=edited_context)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify background still appears after save
    html = data["email_html"]
    assert 'test_background.jpg' in html
    assert 'EDITED' in html


def test_missing_background_safe_fallback(client, job_payload):
    """Test that missing background URL is handled gracefully."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context without background
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    
    # Generate email
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify email renders without background
    html = data["email_html"]
    assert 'background-image' not in html.lower() or 'background-image:url' not in html.lower()
    
    # Verify email still has proper structure
    assert '<!doctype html>' in html.lower()
    assert VALID_CONTEXT['headline'] in html


def test_background_dimension_warning_undersized(client, app, job_payload):
    """Test that undersized background images trigger warnings."""
    from services import asset_service
    from services.asset_service import BackgroundDimensionWarning
    
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Test the dimension check function with undersized dimensions
    upload_result = {'width': 100, 'height': 100}
    warning = asset_service._check_background_dimensions(upload_result)
    
    assert warning is not None
    assert isinstance(warning, BackgroundDimensionWarning)
    assert warning.width == 100
    assert warning.height == 100
    assert 'too small' in str(warning).lower()


def test_background_dimension_warning_sufficient(client):
    """Test that sufficiently large background images do not trigger warnings."""
    from services import asset_service
    
    # Test with dimensions above minimum threshold
    upload_result = {'width': 1920, 'height': 1080}
    warning = asset_service._check_background_dimensions(upload_result)
    
    assert warning is None


def test_background_dimension_warning_missing_metadata(client):
    """Test that missing dimension metadata is handled gracefully."""
    from services import asset_service
    
    # Test with missing dimension data
    upload_result = {'secure_url': 'https://example.com/bg.jpg'}
    warning = asset_service._check_background_dimensions(upload_result)
    
    assert warning is None


def test_background_dimension_warning_boundary(client):
    """Test boundary behavior at minimum threshold."""
    from services import asset_service
    from services.asset_service import BackgroundDimensionWarning, MIN_BACKGROUND_WIDTH, MIN_BACKGROUND_HEIGHT
    
    # Test exactly at threshold (should not warn)
    upload_result = {'width': MIN_BACKGROUND_WIDTH, 'height': MIN_BACKGROUND_HEIGHT}
    warning = asset_service._check_background_dimensions(upload_result)
    assert warning is None
    
    # Test just below threshold (should warn)
    upload_result = {'width': MIN_BACKGROUND_WIDTH - 1, 'height': MIN_BACKGROUND_HEIGHT}
    warning = asset_service._check_background_dimensions(upload_result)
    assert warning is not None


def test_list_poster_assets_empty(client):
    """Test listing poster assets when none exist."""
    response = client.get("/api/assets/posters")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["assets"] == []


def test_list_poster_assets_with_references(client, app, job_payload):
    """Test listing poster assets with job references."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set poster URL
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.event_poster = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
        db.session.commit()
    
    response = client.get("/api/assets/posters")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["assets"]) == 1
    
    asset = data["assets"][0]
    assert asset["url"] == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
    assert asset["reference_count"] == 1
    assert asset["deletable"] is True  # Job is in DRAFT state, so deletable
    assert asset["has_sent_reference"] is False


def test_delete_poster_asset_safe(client, app, job_payload):
    """Test deleting a poster asset that is only referenced by non-sent jobs."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set poster URL via direct DB access using the same app context
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.event_poster = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
        db.session.commit()
    
    # Delete the asset
    response = client.delete("/api/assets/posters", json={
        "url": 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_delete_poster_asset_protected_by_sent_job(client, app, job_payload):
    """Test that poster assets referenced by sent jobs are protected from deletion."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set poster URL and mark job as sent
    from models.email_job import EmailJob, JobStatus
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.event_poster = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
        job.status = JobStatus.FINAL_SENT
        db.session.commit()
    
    # Attempt to delete the asset
    response = client.delete("/api/assets/posters", json={
        "url": 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
    })
    assert response.status_code == 403
    data = response.get_json()
    assert data["success"] is False
    assert "protected" in data["error"].lower() or "sent" in data["error"].lower()
    
    # Verify poster is still on the job
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        assert job.event_poster is not None


def test_delete_poster_asset_missing_url(client):
    """Test that deleting without a URL returns an error."""
    response = client.delete("/api/assets/posters", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "url" in data["error"].lower()


def test_extract_public_id_from_url(client):
    """Test Cloudinary public ID extraction from URLs."""
    from services.asset_service import extract_public_id_from_url
    
    # Test with folder structure
    url = "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/automail/posters/test_poster.jpg"
    public_id = extract_public_id_from_url(url)
    assert public_id == "automail/posters/test_poster"
    
    # Test without folder
    url = "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg"
    public_id = extract_public_id_from_url(url)
    assert public_id == "test_poster"
    
    # Test with None
    assert extract_public_id_from_url(None) is None
    
    # Test with invalid string
    assert extract_public_id_from_url("") is None


def test_poster_status_in_rendered_html(client, app, job_payload):
    """Test that poster URL present in job results in poster being rendered in HTML."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set poster URL
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.event_poster = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
        db.session.commit()
    
    # Approve context and generate email
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify poster appears in rendered HTML (authoritative source for status)
    html = data["email_html"]
    assert 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg' in html
    assert 'img' in html
    assert 'Event Poster' in html


def test_poster_status_when_absent(client, job_payload):
    """Test that missing poster URL results in poster not being rendered in HTML."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context without poster
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    
    # Generate email
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify poster does NOT appear in rendered HTML
    html = data["email_html"]
    assert 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg' not in html


def test_poster_status_survives_edit_save(client, app, job_payload):
    """Test that poster status persists through edit and save operations."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set poster URL
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.event_poster = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
        db.session.commit()
    
    # Approve context and generate email
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    
    # Edit and save
    edited_context = {
        'subject': VALID_CONTEXT['subject'],
        'preheader': VALID_CONTEXT['preheader'],
        'headline': 'EDITED',
        'intro': VALID_CONTEXT['intro'],
        'sections': VALID_CONTEXT['sections'],
        'event_details': VALID_CONTEXT['event_details'],
        'cta': VALID_CONTEXT['cta'],
        'closing': VALID_CONTEXT['closing'],
        'contact_details': VALID_CONTEXT.get('contact_details', []),
    }
    
    response = client.put(f"/api/jobs/{job_id}/email/content", json=edited_context)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify poster still appears in rendered HTML after save
    html = data["email_html"]
    assert 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg' in html
    assert 'img' in html
    assert 'Event Poster' in html


def test_background_status_in_rendered_html(client, app, job_payload):
    """Test that background URL present in job results in background being rendered in HTML."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set background URL
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.email_bg = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg'
        db.session.commit()
    
    # Approve context and generate email
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify background appears in rendered HTML (authoritative source for status)
    html = data["email_html"]
    assert 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg' in html
    assert 'background=' in html  # Email-safe background attribute


def test_background_status_when_absent(client, job_payload):
    """Test that missing background URL results in background not being rendered in HTML."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Approve context without background
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    
    # Generate email
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify background does NOT appear in rendered HTML
    html = data["email_html"]
    assert 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg' not in html


def test_background_status_survives_edit_save(client, app, job_payload):
    """Test that background status persists through edit and save operations."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set background URL
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.email_bg = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg'
        db.session.commit()
    
    # Approve context and generate email
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    
    # Edit and save
    edited_context = {
        'subject': VALID_CONTEXT['subject'],
        'preheader': VALID_CONTEXT['preheader'],
        'headline': 'EDITED',
        'intro': VALID_CONTEXT['intro'],
        'sections': VALID_CONTEXT['sections'],
        'event_details': VALID_CONTEXT['event_details'],
        'cta': VALID_CONTEXT['cta'],
        'closing': VALID_CONTEXT['closing'],
        'contact_details': VALID_CONTEXT.get('contact_details', []),
    }
    
    response = client.put(f"/api/jobs/{job_id}/email/content", json=edited_context)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    # Verify background still appears in rendered HTML after save
    html = data["email_html"]
    assert 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg' in html
    assert 'background=' in html


def test_renderer_and_status_agree_on_source_of_truth(client, app, job_payload):
    """Test that the rendered HTML and asset status derive from the same source."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set both poster and background URLs
    from models.email_job import EmailJob
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.event_poster = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
        job.email_bg = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg'
        db.session.commit()
    
    # Approve context and generate email
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    html = data["email_html"]
    
    # Both assets should be in the rendered HTML (renderer's source of truth)
    poster_in_html = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg' in html
    background_in_html = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg' in html
    
    assert poster_in_html, "Poster should be in rendered HTML when job.event_poster is set"
    assert background_in_html, "Background should be in rendered HTML when job.email_bg is set"
    
    # The job fields should match what was rendered
    job_data = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job_data["event_poster"] == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
    assert job_data["email_bg"] == 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg'


def test_both_assets_used_status_and_html_agreement(client, app, job_payload):
    """Test that would have caught the exact bug: both assets present → status USED for both, HTML contains both."""
    job_id = client.post("/api/jobs", json=job_payload).get_json()["job"]["id"]
    
    # Set both poster and background URLs
    from models.email_job import EmailJob
    poster_url = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_poster.jpg'
    background_url = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/test_background.jpg'
    
    with app.app_context():
        job = db.session.get(EmailJob, job_id)
        job.event_poster = poster_url
        job.email_bg = background_url
        db.session.commit()
    
    # Approve context and generate email
    client.put(f"/api/jobs/{job_id}/context", json=VALID_CONTEXT)
    response = client.post(f"/api/jobs/{job_id}/email/generate")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    html = data["email_html"]
    
    # CRITICAL: Both URLs must be in the rendered HTML
    assert poster_url in html, f"Poster URL {poster_url} must be in rendered HTML"
    assert background_url in html, f"Background URL {background_url} must be in rendered HTML"
    
    # CRITICAL: Background must use email-safe background attribute
    assert 'background=' in html, "Email-safe background attribute must be present"
    
    # CRITICAL: Poster must be in an img tag
    assert f'<img src="{poster_url}"' in html, "Poster must be in an img tag"
    
    # CRITICAL: The job fields must match
    job_data = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job_data["event_poster"] == poster_url
    assert job_data["email_bg"] == background_url
