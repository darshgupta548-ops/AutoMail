"""Provider-specific Gmail transport wrapper for authenticated sender identity."""

import base64
import os
import re
import secrets
import time
from datetime import datetime
from urllib.parse import urlencode

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from services.mime_builder import build_mime_message


DEFAULT_GMAIL_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailConfigError(RuntimeError):
    """Raised when required Gmail OAuth configuration is missing."""


class GmailOAuthError(RuntimeError):
    """Raised when an OAuth or token exchange step fails."""


class GmailSenderError(RuntimeError):
    """Raised when Gmail delivery fails or the sender is invalid."""


def _get_oauth_config():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        raise GmailConfigError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI."
        )

    scopes = os.getenv(
        "GOOGLE_OAUTH_SCOPES",
        " ".join(DEFAULT_GMAIL_SCOPES),
    )
    if not scopes or not scopes.strip():
        scopes = " ".join(DEFAULT_GMAIL_SCOPES)

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scopes": [scope.strip() for scope in scopes.split() if scope.strip()],
    }


def generate_oauth_state():
    """Create a secure OAuth CSRF state token."""
    return secrets.token_urlsafe(32)


def build_authorization_url(state=None, redirect_uri=None):
    """Build the Google OAuth consent URL for the authenticated Gmail sender."""
    config = _get_oauth_config()
    state_value = state or generate_oauth_state()
    auth_redirect = redirect_uri or config["redirect_uri"]
    params = {
        "client_id": config["client_id"],
        "redirect_uri": auth_redirect,
        "response_type": "code",
        "scope": " ".join(config["scopes"]),
        "access_type": "offline",
        "prompt": "consent",
        "state": state_value,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_tokens(code, redirect_uri=None):
    """Exchange the OAuth code for access and refresh tokens."""
    if not code or not str(code).strip():
        raise GmailOAuthError("Authorization code missing or empty.")

    config = _get_oauth_config()
    payload = {
        "code": code,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": redirect_uri or config["redirect_uri"],
        "grant_type": "authorization_code",
    }

    response = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=30)
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        detail = response.text.strip() or str(error)
        raise GmailOAuthError(f"Google OAuth exchange failed: {detail}") from error

    data = response.json()
    if "access_token" not in data:
        raise GmailOAuthError("Google OAuth did not return an access token.")

    if "expires_in" in data and data["expires_in"] is not None:
        data["expires_at"] = time.time() + int(data["expires_in"])

    return data


def _credentials_from_token_data(token_data):
    config = _get_oauth_config()
    token = dict(token_data or {})
    refresh_token = token.get("refresh_token")
    access_token = token.get("access_token")
    if not access_token and not refresh_token:
        raise GmailSenderError("No Google credentials are available for the current sender.")

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=config["scopes"],
    )
    if token.get("expires_at"):
        creds.expiry = datetime.fromtimestamp(float(token["expires_at"]))
    return creds


def get_sender_identity_from_tokens(token_data):
    """Load the authenticated Gmail account info for the current signed-in sender."""
    credentials = _credentials_from_token_data(token_data)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_data = {
            **dict(token_data or {}),
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.timestamp() if credentials.expiry else time.time() + 3600,
        }

    oauth_service = build("oauth2", "v2", credentials=credentials)
    profile = oauth_service.userinfo().get().execute()

    return {
        "email": profile.get("email"),
        "display_name": profile.get("name") or profile.get("given_name"),
        "picture_url": profile.get("picture"),
        "status": "connected",
        "token": token_data,
    }


def is_authenticated_sender(sender_identity):
    """Return true when the sender has a valid Gmail identity and usable token."""
    if not isinstance(sender_identity, dict):
        return False
    email = sender_identity.get("email")
    token_data = sender_identity.get("token") or {}
    return bool(email and token_data.get("access_token"))


def _refresh_sender_credentials(sender_identity):
    if not is_authenticated_sender(sender_identity):
        raise GmailSenderError("No authenticated Gmail sender is available.")

    token_data = dict(sender_identity.get("token") or {})
    credentials = _credentials_from_token_data(token_data)
    if not credentials.valid:
        if credentials.refresh_token:
            credentials.refresh(Request())
            sender_identity["token"] = {
                **token_data,
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry.timestamp() if credentials.expiry else time.time() + 3600,
            }
            return sender_identity
        raise GmailSenderError("The Gmail credentials are expired or invalid.")
    return sender_identity


def build_message_for_job(sender_identity, job, recipients, cc=None, bcc=None):
    """Construct the final MIME message from the approved HTML and authenticated sender."""
    if not is_authenticated_sender(sender_identity):
        raise GmailSenderError("A Gmail sender must be authenticated before building the transport-ready message.")

    if not job or not getattr(job, "email_html", None):
        raise GmailSenderError("The job does not contain approved email HTML to send.")

    context = getattr(job, "email_context", {}) or {}
    subject = context.get("subject") or "AUTO-MAIL Update"
    sender_email = sender_identity.get("email")

    message = build_mime_message(
        sender=sender_email,
        recipients=recipients,
        subject=subject,
        html_body=job.email_html,
        text_body=None,
        cc=cc,
        bcc=bcc,
    )
    return message


def send_mime_message(sender_identity, mime_message):
    """Send a prebuilt MIME message through the authenticated Gmail account."""
    if not is_authenticated_sender(sender_identity):
        raise GmailSenderError("The Gmail sender is not authenticated.")

    if mime_message is None:
        raise GmailSenderError("No MIME message supplied to the Gmail sender.")

    sender_identity = _refresh_sender_credentials(sender_identity)
    token_data = dict(sender_identity.get("token") or {})
    creds = _credentials_from_token_data(token_data)
    service = build("gmail", "v1", credentials=creds)

    try:
        raw_payload = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("ascii").rstrip("=")
        response = service.users().messages().send(userId="me", body={"raw": raw_payload}).execute()
        return {
            "success": True,
            "message_id": response.get("id"),
            "thread_id": response.get("threadId"),
            "status": "sent",
        }
    except Exception as exc:
        raise GmailSenderError(f"Gmail API rejected the transmission: {exc}") from exc


def _validate_recipient_email(value):
    candidate = str(value or "").strip()
    if not candidate:
        raise GmailSenderError("Recipient email is required.")
    if "\n" in candidate or "\r" in candidate:
        raise GmailSenderError("Recipient email contains invalid header characters.")
    if not re.fullmatch(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$", candidate):
        raise GmailSenderError(f"Invalid recipient email address: {candidate}")
    return candidate


def send_batch_to_recipients(sender_identity, job, recipients):
    """Send the approved email to the configured recipients and return per-recipient results."""
    clean_recipients = []
    for recipient in recipients or []:
        clean_recipients.append(_validate_recipient_email(recipient))

    if not clean_recipients:
        raise GmailSenderError("No valid recipients are configured for the transmission.")

    results = []
    for recipient in clean_recipients:
        try:
            mime_message = build_message_for_job(
                sender_identity=sender_identity,
                job=job,
                recipients=[recipient],
            )
            result = send_mime_message(sender_identity, mime_message)
            results.append({"recipient": recipient, "success": True, "message_id": result.get("message_id")})
        except GmailSenderError as exc:
            results.append({"recipient": recipient, "success": False, "error": str(exc)})

    success_count = sum(1 for result in results if result.get("success"))
    return {
        "success": success_count == len(clean_recipients),
        "sent_count": success_count,
        "total_count": len(clean_recipients),
        "results": results,
        "status": "partial_failure" if success_count and success_count != len(clean_recipients) else ("sent" if success_count else "failed"),
    }


def get_test_recipient_emails():
    """Return the configured recipients for the Stage 06 executive test send."""
    configured = os.getenv("TEST_SEND_RECIPIENTS", "")
    return _split_recipient_list(configured)


def _split_recipient_list(raw_value):
    if not raw_value:
        return []
    values = []
    for item in raw_value.replace(";", ",").split(","):
        value = item.strip()
        if value:
            try:
                values.append(_validate_recipient_email(value))
            except GmailSenderError:
                continue
    return values
