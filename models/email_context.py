"""Pydantic contract for structured Sense Maker output."""

from pydantic import BaseModel, ConfigDict, Field


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
    contact_details: list[str] = Field(default_factory=list)
    # Named organization assets are persisted with the email context, not template code.
    brahmand_logo_url: str | None = None
    snt_logo_url: str | None = None
    osail_logo_url: str | None = None
    # Legacy compatibility for contexts created before the named fields existed.
    logo_urls: dict[str, str] = Field(default_factory=dict)
