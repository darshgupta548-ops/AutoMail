"""Pydantic contract for structured Sense Maker output."""

from pydantic import BaseModel, ConfigDict


class EmailSection(BaseModel):
    """One concise content section in a generated email context."""

    model_config = ConfigDict(extra="forbid")

    heading: str
    body: str
    bullets: list[str]


class EventDetails(BaseModel):
    """Event facts formatted for the email context."""

    model_config = ConfigDict(extra="forbid")

    date: str
    time: str
    venue: str | None
    registration_url: str | None


class CallToAction(BaseModel):
    """Call-to-action content without rendering information."""

    model_config = ConfigDict(extra="forbid")

    label: str
    url: str | None


class EmailContext(BaseModel):
    """Exact JSON-only content contract produced by Sense Maker."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    preheader: str
    headline: str
    intro: str
    sections: list[EmailSection]
    event_details: EventDetails
    cta: CallToAction
    closing: str
