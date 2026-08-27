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


def test_create_and_retrieve_job(client, job_payload):
    created = client.post("/api/jobs", json=job_payload)
    assert created.status_code == 201
    created_job = created.get_json()["job"]
    assert created_job["id"]
    assert created_job["status"] == "DRAFT"

    fetched = client.get(f"/api/jobs/{created_job['id']}")
    assert fetched.status_code == 200
    job = fetched.get_json()["job"]
    assert job["event_name"] == job_payload["event_name"]
    assert job["event_date"] == "2026-10-11"
    assert job["event_start_time"] == "10:00:00"


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