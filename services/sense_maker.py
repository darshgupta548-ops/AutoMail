"""Structured Gemini content generation for AUTO-MAIL email jobs."""

import json
import os
from urllib.parse import urlparse

import requests
from google import genai
from google.genai import types

from models.email_context import EmailContext


GEMINI_MODEL = "gemini-3.6-flash"

DEFAULT_ORGANIZATION_LOGOS = {
    "brahmand_logo_url": "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png",
    "snt_logo_url": "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png",
    "osail_logo_url": "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png",
}
CLOUDINARY_HOST = "res.cloudinary.com"
GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "required": [
        "subject", "preheader", "headline", "intro", "sections",
        "event_details", "cta", "closing",
    ],
    "properties": {
        "subject": {"type": "string"},
        "preheader": {"type": "string"},
        "headline": {"type": "string"},
        "intro": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["heading", "body", "bullets"],
                "properties": {
                    "heading": {"type": "string"},
                    "body": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "event_details": {
            "type": "object",
            "required": ["date", "time", "venue", "registration_url"],
            "properties": {
                "date": {"type": "string"},
                "time": {"type": "string"},
                "venue": {"type": ["string", "null"]},
                "registration_url": {"type": ["string", "null"]},
            },
        },
        "cta": {
            "type": "object",
            "required": ["label", "url"],
            "properties": {
                "label": {"type": "string"},
                "url": {"type": ["string", "null"]},
            },
        },
        "closing": {"type": "string"},
    },
}


class SenseMakerError(Exception):
    """Raised when Gemini cannot generate a usable email context."""


class SenseMakerValidationError(SenseMakerError):
    """Raised when a job does not contain the required input data."""


def _validate_job(job):
    required_fields = ("event_name", "event_date", "event_start_time", "event_description")
    if any(not getattr(job, field, None) for field in required_fields):
        raise SenseMakerValidationError("Job is missing required event information.")


def _is_cloudinary_url(url):
    parsed = urlparse(url or "")
    return parsed.scheme == "https" and parsed.hostname == CLOUDINARY_HOST


def _fetch_poster_part(poster_url):
    """Fetch only a stored Cloudinary poster and convert it to Gemini image input."""
    if not _is_cloudinary_url(poster_url):
        return None

    try:
        response = requests.get(poster_url, timeout=10)
        response.raise_for_status()
        mime_type = response.headers.get("Content-Type", "").split(";", 1)[0]
        if not mime_type.startswith("image/") or not response.content:
            return None
        return types.Part.from_bytes(data=response.content, mime_type=mime_type)
    except requests.RequestException:
        return None


def _job_prompt(job):
    job_data = {
        "event_name": job.event_name,
        "event_date": job.event_date.isoformat(),
        "event_start_time": job.event_start_time.isoformat(),
        "event_end_time": job.event_end_time.isoformat() if job.event_end_time else None,
        "event_venue": job.event_venue,
        "registration_url": job.registration_url,
        "event_description": job.event_description,
        "event_whatsapp_message": job.event_whatsapp_message,
    }
    return (
        "You are writing email content for a university astronomy or technology club event. "
        "Treat the event description, WhatsApp message, and poster as the primary sources of truth. "
        "Carefully extract and combine useful details from ALL available sources before writing. "
        "Prefer specific information from the supplied material over generic promotional language. "
        "Write like a strong human event copywriter, not like an AI-generated institutional announcement. "
        "Avoid repetitive phrases such as: 'exciting opportunity', 'delve into', 'join us for an exciting', "
        "'offers participants an opportunity', 'don't miss this opportunity', etc. "
        "Make the headline and introduction attention-grabbing without becoming clickbait. "
        "The introduction should create curiosity and communicate WHY the event is worth attending. "
        "Sections should have meaningful, event-specific headings rather than generic headings like 'Event Overview'. "
        "Bullets should contain useful concrete information, not filler or repetition. "
        "Vary sentence structure and vocabulary naturally. Keep the tone enthusiastic, polished, and appropriate "
        "for a university/club event. Do not make the copy unnecessarily long. "
        "Never alter, reinterpret, calculate, or substitute factual event details. When multiple sources contain "
        "conflicting values, prefer the explicitly structured event fields, then the WhatsApp message, then the poster. "
        "Never invent missing information. Never invent speakers, activities, claims, benefits, audience details, or facts "
        "that are not supported by the supplied sources. If information is missing, leave the corresponding field null or "
        "use only information that is actually available. Preserve important wording, terminology, names, dates, and "
        "event-specific phrases from the source material where appropriate. The final content should feel like it was "
        "written specifically for THIS event, not like a reusable template. "
        "Do not generate HTML, CSS, Markdown, or formatting instructions. Return only the requested "
        "JSON object with the exact schema specified.\n\n"
        f"Job data:\n{json.dumps(job_data, ensure_ascii=False)}"
    )


def generate_email_context(job):
    """Generate and strictly validate the structured email context for one EmailJob."""
    _validate_job(job)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SenseMakerError("Gemini is not configured.")

    contents = [_job_prompt(job)]
    poster_part = _fetch_poster_part(job.event_poster)
    if poster_part is not None:
        contents.append(poster_part)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": GEMINI_RESPONSE_SCHEMA,
            },
        )
        generated = response.parsed if response.parsed is not None else json.loads(response.text)
        generated = dict(generated)
        for field_name, url in DEFAULT_ORGANIZATION_LOGOS.items():
            generated.setdefault(field_name, url)
        return EmailContext.model_validate(generated).model_dump(mode="json", exclude_defaults=True)
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise SenseMakerError("Gemini returned an invalid email context.") from error
    except Exception as error:
        raise SenseMakerError("Gemini context generation failed.") from error
