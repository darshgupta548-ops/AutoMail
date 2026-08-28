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
