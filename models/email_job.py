"""Persistence model for an AUTO-MAIL email-generation workflow."""

from datetime import UTC, datetime

from extensions import db


def _utcnow():
    """Return the current UTC time for persistence timestamps."""
    return datetime.now(UTC)


class JobStatus:
    """Database values allowed for an email job's workflow status."""

    DRAFT = "DRAFT"
    ASSETS_READY = "ASSETS_READY"
    CONTEXT_GENERATED = "CONTEXT_GENERATED"
    CONTEXT_APPROVED = "CONTEXT_APPROVED"
    EMAIL_RENDERED = "EMAIL_RENDERED"
    EMAIL_APPROVED = "EMAIL_APPROVED"
    TEST_SENT = "TEST_SENT"
    TEST_APPROVED = "TEST_APPROVED"
    FINAL_SENT = "FINAL_SENT"

    ALL = (
        DRAFT, ASSETS_READY, CONTEXT_GENERATED, CONTEXT_APPROVED,
        EMAIL_RENDERED, EMAIL_APPROVED, TEST_SENT, TEST_APPROVED, FINAL_SENT,
    )


class EmailJob(db.Model):
    """One persisted AUTO-MAIL email-generation workflow."""

    __tablename__ = "email_jobs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_name = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_start_time = db.Column(db.Time, nullable=False)
    event_end_time = db.Column(db.Time, nullable=True)
    event_venue = db.Column(db.String(300), nullable=True)
    registration_url = db.Column(db.String(1000), nullable=True)
    event_description = db.Column(db.Text, nullable=False)
    event_whatsapp_message = db.Column(db.Text, nullable=True)
    email_context = db.Column(db.JSON, nullable=True)
    event_poster = db.Column(db.String(500), nullable=True)
    email_bg = db.Column(db.String(500), nullable=True)
    event_palette = db.Column(db.JSON, nullable=True)
    event_typography = db.Column(db.JSON, nullable=True)
    email_html = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default=JobStatus.DRAFT)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        """Return a JSON-ready representation of this job."""
        return {
            "id": self.id,
            "event_name": self.event_name,
            "event_date": self.event_date.isoformat(),
            "event_start_time": self.event_start_time.isoformat(),
            "event_end_time": self.event_end_time.isoformat() if self.event_end_time else None,
            "event_venue": self.event_venue,
            "registration_url": self.registration_url,
            "event_description": self.event_description,
            "event_whatsapp_message": self.event_whatsapp_message,
            "email_context": self.email_context,
            "event_poster": self.event_poster,
            "email_bg": self.email_bg,
            "event_palette": self.event_palette,
            "event_typography": self.event_typography,
            "email_html": self.email_html,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
