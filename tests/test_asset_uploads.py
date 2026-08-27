"""Tests for the Cloudinary-backed asset upload endpoint."""

from io import BytesIO
from unittest.mock import patch

import pytest

from app import create_app
from extensions import db


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "demo")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_job(client):
    response = client.post(
        "/api/jobs",
        json={
            "event_name": "HELIOTRACK 2.0",
            "event_date": "2026-10-11",
            "event_start_time": "10:00",
            "event_description": "An astronomy event.",
        },
    )
    return response.get_json()["job"]["id"]


def image_file(name):
    return (BytesIO(b"image-bytes"), name, "image/png")


@patch("services.asset_service.cloudinary.uploader.upload")
def test_poster_upload_saves_event_poster(mock_upload, client):
    mock_upload.return_value = {"secure_url": "https://cdn.example/poster.png"}
    job_id = create_job(client)

    response = client.post(f"/api/jobs/{job_id}/assets", data={"poster": image_file("poster.png")})

    assert response.status_code == 200
    assert response.get_json()["assets"]["poster_url"] == "https://cdn.example/poster.png"
    assert client.get(f"/api/jobs/{job_id}").get_json()["job"]["event_poster"] == "https://cdn.example/poster.png"
    assert mock_upload.call_args.kwargs["folder"] == "automail/posters"


@patch("services.asset_service.cloudinary.uploader.upload")
def test_background_upload_saves_email_background(mock_upload, client):
    mock_upload.return_value = {"secure_url": "https://cdn.example/background.png"}
    job_id = create_job(client)

    response = client.post(f"/api/jobs/{job_id}/assets", data={"background": image_file("background.png")})

    assert response.status_code == 200
    assert response.get_json()["assets"]["background_url"] == "https://cdn.example/background.png"
    assert client.get(f"/api/jobs/{job_id}").get_json()["job"]["email_bg"] == "https://cdn.example/background.png"
    assert mock_upload.call_args.kwargs["folder"] == "automail/backgrounds"


@patch("services.asset_service.cloudinary.uploader.upload")
def test_both_assets_can_be_uploaded_together(mock_upload, client):
    mock_upload.side_effect = [
        {"secure_url": "https://cdn.example/poster.png"},
        {"secure_url": "https://cdn.example/background.png"},
    ]
    job_id = create_job(client)

    response = client.post(
        f"/api/jobs/{job_id}/assets",
        data={"poster": image_file("poster.png"), "background": image_file("background.png")},
    )

    assert response.status_code == 200
    assert response.get_json()["assets"] == {
        "poster_url": "https://cdn.example/poster.png",
        "background_url": "https://cdn.example/background.png",
    }
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["event_poster"] == "https://cdn.example/poster.png"
    assert job["email_bg"] == "https://cdn.example/background.png"


def test_missing_assets_returns_400(client):
    job_id = create_job(client)
    assert client.post(f"/api/jobs/{job_id}/assets", data={}).status_code == 400


def test_non_image_file_is_rejected(client):
    job_id = create_job(client)
    response = client.post(
        f"/api/jobs/{job_id}/assets",
        data={"poster": (BytesIO(b"not an image"), "notes.txt", "text/plain")},
    )
    assert response.status_code == 400


def test_non_existent_job_returns_404(client):
    response = client.post("/api/jobs/999/assets", data={"poster": image_file("poster.png")})
    assert response.status_code == 404
