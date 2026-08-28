"""Deterministic Jinja-based, event-focused email renderer."""

from copy import deepcopy
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape


class EmailMakerError(Exception):
    """Raised when email rendering fails."""


_CONTACT_LINE = re.compile(
    r"^\s*[^:\n]{1,80}:\s*(?:\+?[\d][\d\s().-]{5,}|\S+@\S+)\s*$"
)
_LOGO_FIELDS = (
    ("Brahmand", "brahmand_logo_url"),
    ("OSAIl", "osail_logo_url"),
    ("S&T", "snt_logo_url"),
)


def _get_template_env():
    """Create and configure Jinja environment for email templates."""
    from markupsafe import Markup, escape

    env = Environment(
        loader=FileSystemLoader("templates/emails"),
        autoescape=select_autoescape(["html", "xml"]),
        auto_reload=False,
    )

    def nl2br(text):
        if not text:
            return ""
        escaped = escape(text)
        return Markup(escaped.replace("\n", "<br>"))

    env.filters["nl2br"] = nl2br
    return env


def _prepare_context(email_context: dict) -> dict:
    """Add defaults and migrate legacy inline contact lines without mutating input."""
    context = deepcopy(email_context)
    contacts = list(context.get("contact_details") or [])
    cleaned_sections = []

    for section in context.get("sections") or []:
        section = deepcopy(section)
        body_lines = (section.get("body") or "").splitlines()
        kept_body = []
        for line in body_lines:
            if _CONTACT_LINE.match(line):
                contacts.append(line.strip())
            else:
                kept_body.append(line)
        section["body"] = "\n".join(kept_body)

        kept_bullets = []
        for bullet in section.get("bullets") or []:
            if _CONTACT_LINE.match(bullet):
                contacts.append(bullet.strip())
            else:
                kept_bullets.append(bullet)
        section["bullets"] = kept_bullets

        # A legacy contacts-only section becomes the dedicated final block.
        if section.get("heading", "").strip().lower() in {"contact", "contacts", "contact details"} and not section["body"] and not section["bullets"]:
            continue
        cleaned_sections.append(section)

    context["sections"] = cleaned_sections
    context["contact_details"] = list(dict.fromkeys(contact for contact in contacts if contact))
    logo_urls = context.get("logo_urls") or {}
    legacy_names = {"Brahmand": "Brahmand", "OSAIl": "SAIIL", "S&T": "S&T"}
    context["header_logos"] = [
        {"name": name, "url": context.get(field_name) or logo_urls.get(legacy_names[name])}
        for name, field_name in _LOGO_FIELDS
        if context.get(field_name) or logo_urls.get(legacy_names[name])
    ]
    return context


def render_email(email_context: dict, poster_url: str = None, background_url: str = None) -> str:
    """Render complete email HTML from validated structured email data."""
    try:
        env = _get_template_env()
        template = env.get_template("base.html")
        html = template.render(
            **_prepare_context(email_context),
            poster_url=poster_url,
            background_url=background_url,
        )
        return html
    except Exception as error:
        raise EmailMakerError(f"Email rendering failed: {str(error)}") from error
