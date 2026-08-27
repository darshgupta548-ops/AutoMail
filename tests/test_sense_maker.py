"""Tests for Gemini-backed Sense Maker generation."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from extensions import db
from services import sense_maker


VALID_CONTEXT = {
    "subject": "Explore the Night Sky",
    "preheader": "Join HELIOTRACK 2.0.",
    "headline": "HELIOTRACK 2.0",
    "intro": "Join us for an astronomy event.",
    "sections": [{"heading": "What to expect", "body": "Astronomy activities.", "bullets": []}],
    "event_details": {
        "date": "2026-10-11",
        "time": "10:00:00",
        "venue": None,
        "registration_url": None,
    },
    "cta": {"label": "Learn more", "url": None},
    "closing": "See you there.",
}


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


def create_job(client, poster=None, email_context=None):
    payload = {
        "event_name": "HELIOTRACK 2.0",
        "event_date": "2026-10-11",
        "event_start_time": "10:00",
        "event_description": "An astronomy event.",
        "event_poster": poster,
        "email_context": email_context,
    }
    return client.post("/api/jobs", json=payload).get_json()["job"]["id"]


@patch("services.sense_maker.generate_email_context", return_value=VALID_CONTEXT)
def test_valid_job_generates_and_saves_context(mock_generate, client):
    job_id = create_job(client)

    response = client.post(f"/api/jobs/{job_id}/context/generate")

    assert response.status_code == 200
    assert response.get_json()["status"] == "CONTEXT_GENERATED"
    assert response.get_json()["email_context"] == VALID_CONTEXT
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["email_context"] == VALID_CONTEXT
    assert job["status"] == "CONTEXT_GENERATED"
    mock_generate.assert_called_once()


@patch("services.sense_maker.generate_email_context", return_value=VALID_CONTEXT)
def test_poster_present_job_is_passed_to_sense_maker(mock_generate, client):
    poster = "https://res.cloudinary.com/demo/image/upload/automail/posters/poster.png"
    job_id = create_job(client, poster=poster)

    assert client.post(f"/api/jobs/{job_id}/context/generate").status_code == 200
    assert mock_generate.call_args.args[0].event_poster == poster


@patch("services.sense_maker.generate_email_context", return_value=VALID_CONTEXT)
def test_missing_poster_is_handled(mock_generate, client):
    job_id = create_job(client)

    assert client.post(f"/api/jobs/{job_id}/context/generate").status_code == 200
    assert mock_generate.call_args.args[0].event_poster is None


def test_cloudinary_poster_is_converted_to_gemini_image_part():
    response = MagicMock()
    response.headers = {"Content-Type": "image/png"}
    response.content = b"poster-image"
    with patch("services.sense_maker.requests.get", return_value=response) as mock_get, patch(
        "services.sense_maker.types.Part.from_bytes", return_value="image-part"
    ) as mock_part:
        part = sense_maker._fetch_poster_part(
            "https://res.cloudinary.com/demo/image/upload/automail/posters/poster.png"
        )

    assert part == "image-part"
    mock_get.assert_called_once()
    mock_part.assert_called_once_with(data=b"poster-image", mime_type="image/png")


def test_missing_poster_uses_text_only_gemini_input(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    job = SimpleNamespace(
        event_name="HELIOTRACK 2.0",
        event_date=__import__("datetime").date(2026, 10, 11),
        event_start_time=__import__("datetime").time(10, 0),
        event_end_time=None,
        event_venue=None,
        registration_url=None,
        event_description="An astronomy event.",
        event_whatsapp_message=None,
        event_poster=None,
    )
    response = SimpleNamespace(parsed=VALID_CONTEXT, text=None)
    with patch("services.sense_maker.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = response
        assert sense_maker.generate_email_context(job) == VALID_CONTEXT

    contents = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
    assert len(contents) == 1


def test_gemini_failure_returns_502_without_overwriting_context(client):
    old_context = {"subject": "Existing approved draft"}
    job_id = create_job(client, email_context=old_context)
    with patch(
        "services.sense_maker.generate_email_context",
        side_effect=sense_maker.SenseMakerError("Gemini context generation failed."),
    ):
        response = client.post(f"/api/jobs/{job_id}/context/generate")

    assert response.status_code == 502
    job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
    assert job["email_context"] == old_context
    assert job["status"] == "DRAFT"


def test_non_existent_job_returns_404(client):
    assert client.post("/api/jobs/999/context/generate").status_code == 404


def test_gemini_uses_api_compatible_json_schema(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    job = SimpleNamespace(
        event_name="HELIOTRACK 2.0",
        event_date=__import__("datetime").date(2026, 10, 11),
        event_start_time=__import__("datetime").time(10, 0),
        event_end_time=None,
        event_venue=None,
        registration_url=None,
        event_description="An astronomy event.",
        event_whatsapp_message=None,
        event_poster=None,
    )
    response = SimpleNamespace(parsed=VALID_CONTEXT, text=None)
    with patch("services.sense_maker.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = response
        sense_maker.generate_email_context(job)

    config = mock_client.return_value.models.generate_content.call_args.kwargs["config"]
    assert mock_client.return_value.models.generate_content.call_args.kwargs["model"] == "gemini-3.6-flash"
    assert config["response_mime_type"] == "application/json"
    assert "response_json_schema" in config
    assert "additionalProperties" not in str(config["response_json_schema"])


def test_prompt_instructs_primary_sources_and_detail_extraction(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    job = SimpleNamespace(
        event_name="HELIOTRACK 2.0",
        event_date=__import__("datetime").date(2026, 10, 11),
        event_start_time=__import__("datetime").time(10, 0),
        event_end_time=None,
        event_venue=None,
        registration_url=None,
        event_description="An astronomy event.",
        event_whatsapp_message=None,
        event_poster=None,
    )
    response = SimpleNamespace(parsed=VALID_CONTEXT, text=None)
    with patch("services.sense_maker.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = response
        sense_maker.generate_email_context(job)

    contents = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
    prompt = contents[0]
    assert "Treat the event description, WhatsApp message, and poster as the primary sources of truth" in prompt
    assert "Carefully extract and combine useful details from ALL available sources" in prompt
    assert "Prefer specific information from the supplied material over generic promotional language" in prompt


def test_prompt_instructs_human_copywriting_style(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    job = SimpleNamespace(
        event_name="HELIOTRACK 2.0",
        event_date=__import__("datetime").date(2026, 10, 11),
        event_start_time=__import__("datetime").time(10, 0),
        event_end_time=None,
        event_venue=None,
        registration_url=None,
        event_description="An astronomy event.",
        event_whatsapp_message=None,
        event_poster=None,
    )
    response = SimpleNamespace(parsed=VALID_CONTEXT, text=None)
    with patch("services.sense_maker.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = response
        sense_maker.generate_email_context(job)

    contents = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
    prompt = contents[0]
    assert "Write like a strong human event copywriter" in prompt
    assert "not like an AI-generated institutional announcement" in prompt
    assert "exciting opportunity" in prompt
    assert "delve into" in prompt
    assert "don't miss this opportunity" in prompt


def test_prompt_instructs_no_fact_invention(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    job = SimpleNamespace(
        event_name="HELIOTRACK 2.0",
        event_date=__import__("datetime").date(2026, 10, 11),
        event_start_time=__import__("datetime").time(10, 0),
        event_end_time=None,
        event_venue=None,
        registration_url=None,
        event_description="An astronomy event.",
        event_whatsapp_message=None,
        event_poster=None,
    )
    response = SimpleNamespace(parsed=VALID_CONTEXT, text=None)
    with patch("services.sense_maker.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = response
        sense_maker.generate_email_context(job)

    contents = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
    prompt = contents[0]
    assert "Never alter, reinterpret, calculate, or substitute factual event details" in prompt
    assert "When multiple sources contain conflicting values" in prompt
    assert "prefer the explicitly structured event fields, then the WhatsApp message, then the poster" in prompt
    assert "Never invent missing information" in prompt
    assert "Never invent speakers, activities, claims, benefits, audience details, or facts" in prompt
    assert "not supported by the supplied sources" in prompt
    assert "leave the corresponding field null" in prompt


def test_prompt_instructs_event_specific_content(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    job = SimpleNamespace(
        event_name="HELIOTRACK 2.0",
        event_date=__import__("datetime").date(2026, 10, 11),
        event_start_time=__import__("datetime").time(10, 0),
        event_end_time=None,
        event_venue=None,
        registration_url=None,
        event_description="An astronomy event.",
        event_whatsapp_message=None,
        event_poster=None,
    )
    response = SimpleNamespace(parsed=VALID_CONTEXT, text=None)
    with patch("services.sense_maker.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = response
        sense_maker.generate_email_context(job)

    contents = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
    prompt = contents[0]
    assert "Sections should have meaningful, event-specific headings" in prompt
    assert "Event Overview" in prompt
    assert "Bullets should contain useful concrete information" in prompt
    assert "written specifically for THIS event" in prompt
    assert "not like a reusable template" in prompt


def test_prompt_instructs_tone_and_length(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    job = SimpleNamespace(
        event_name="HELIOTRACK 2.0",
        event_date=__import__("datetime").date(2026, 10, 11),
        event_start_time=__import__("datetime").time(10, 0),
        event_end_time=None,
        event_venue=None,
        registration_url=None,
        event_description="An astronomy event.",
        event_whatsapp_message=None,
        event_poster=None,
    )
    response = SimpleNamespace(parsed=VALID_CONTEXT, text=None)
    with patch("services.sense_maker.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.return_value = response
        sense_maker.generate_email_context(job)

    contents = mock_client.return_value.models.generate_content.call_args.kwargs["contents"]
    prompt = contents[0]
    assert "Vary sentence structure and vocabulary naturally" in prompt
    assert "enthusiastic, polished, and appropriate for a university/club event" in prompt
    assert "Do not make the copy unnecessarily long" in prompt
