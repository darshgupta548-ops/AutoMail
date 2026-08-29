# MIME Builder Module

The MIME Builder module (`services/mime_builder.py`) constructs standards-compliant MIME/RFC 2822 email messages from final approved HTML content.

## Overview

```text
Approved Email HTML
    ↓
MIME Builder
    ├── Validate inputs
    ├── Create multipart/alternative message
    ├── Attach plain-text alternative
    ├── Attach HTML body
    ├── Set headers (From, To, Cc, BCC, Subject)
    ├── Handle UTF-8 encoding
    └── Output RFC 2822 format
    ↓
MIME Message
    ↓
(Optional) Base64url encode for Gmail API
    ↓
Gmail Sender
```

## Key Responsibilities

✓ **MIME Builder DOES:**
- Construct standards-compliant RFC 2822 messages
- Create multipart/alternative structure
- Generate plain-text alternative from HTML
- Handle UTF-8 encoding
- Set proper headers
- Prevent header injection
- Produce Gmail API-compatible output

✗ **MIME Builder DOES NOT:**
- Send email
- Authenticate with Google
- Manage OAuth or credentials
- Decide authorization or recipients
- Regenerate or edit HTML
- Make business logic decisions
- Access the database

## Interface

### `build_mime_message()`

Constructs a MIME message from email components.

```python
from services.mime_builder import build_mime_message

msg = build_mime_message(
    sender="events@brahmand.com",
    recipients=["student@example.com"],  # str or list
    subject="You're Invited to Our Event",
    html_body="<html><body><h1>Welcome</h1></body></html>",
    text_body=None,  # optional; auto-generated if not provided
    cc=["admin@brahmand.com"],  # optional
    bcc=None  # optional
)
```

**Parameters:**
- `sender` (str): Sender email address
- `recipients` (str | list): Recipient email address(es)
- `subject` (str): Email subject
- `html_body` (str): HTML email body
- `text_body` (str, optional): Plain-text alternative. If None, auto-generated.
- `cc` (list, optional): CC recipient email addresses
- `bcc` (list, optional): BCC recipient email addresses

**Returns:** `email.message.Message` object

**Raises:**
- `MIMEBuilderValidationError`: If inputs are invalid or contain injection attempts
- `MIMEBuilderError`: If message construction fails

### `message_to_string()`

Convert a MIME message to RFC 2822 string format.

```python
from services.mime_builder import message_to_string

rfc_message = message_to_string(msg)
print(rfc_message)  # RFC 2822 formatted email
```

**Returns:** str (RFC 2822 format)

### `message_to_base64url()`

Convert a MIME message to base64url encoding for Gmail API.

```python
from services.mime_builder import message_to_base64url

b64url = message_to_base64url(msg)

# Send to Gmail API
# POST https://www.googleapis.com/gmail/v1/users/me/messages/send
# {
#   "raw": "b64url_here"
# }
```

**Returns:** str (base64url-encoded message without padding)

**Note:** Gmail API expects `messages.send` requests with the message body base64url-encoded in the `raw` field.

### `message_recipients_list()`

Extract all recipients from message headers (To + Cc; BCC not included).

```python
from services.mime_builder import message_recipients_list

all_recipients = message_recipients_list(msg)
# ['student@example.com', 'admin@brahmand.com']
```

**Returns:** list of email addresses

**Important:** BCC recipients are intentionally NOT extractable from message headers (by design). The caller must track BCC addresses separately when providing them to the Gmail API.

## Workflow Integration

### Typical usage in Flask endpoint:

```python
from flask import jsonify
from services.mime_builder import build_mime_message, message_to_base64url

@app.post("/api/jobs/<int:job_id>/email/send-test")
def send_test_email(job_id):
    job = db.session.get(EmailJob, job_id)
    if not job:
        return jsonify(error="Job not found"), 404
    
    if job.status != JobStatus.EMAIL_APPROVED:
        return jsonify(error="Email must be approved before sending"), 400
    
    # Get sender from config
    sender = os.getenv("BRAHMAND_EMAIL_ADDRESS")
    
    # Test recipients: President, VP, Administrator
    test_recipients = [
        os.getenv("PRESIDENT_EMAIL"),
        os.getenv("VP_EMAIL"),
        os.getenv("ADMIN_EMAIL")
    ]
    
    try:
        # Build MIME message from approved HTML
        msg = build_mime_message(
            sender=sender,
            recipients=test_recipients,
            subject=job.email_context.get("subject"),
            html_body=job.email_html
        )
        
        # Convert to base64url for Gmail API
        raw_message = message_to_base64url(msg)
        
        # Send through Gmail API (not yet implemented)
        # result = gmail_sender.send_message(raw_message)
        
        # Update job status
        job.status = JobStatus.TEST_SENT
        db.session.commit()
        
        return jsonify(success=True, message="Test email sent to executives")
    
    except MIMEBuilderValidationError as e:
        return jsonify(error=f"Invalid email data: {str(e)}"), 400
    except MIMEBuilderError as e:
        return jsonify(error=f"Failed to build message: {str(e)}"), 500
```

## Security Features

### Header Injection Prevention

The MIME Builder validates all header fields to prevent injection attacks:

```python
# These will be rejected:
build_mime_message(
    sender="sender@example.com\nBcc: attacker@example.com",  # ❌ Rejected
    recipients="recipient@example.com",
    subject="Test",
    html_body="<p>Body</p>"
)

build_mime_message(
    sender="sender@example.com",
    recipients="recipient@example.com",
    subject="Test\nCc: attacker@example.com",  # ❌ Rejected
    html_body="<p>Body</p>"
)
```

**Validation checks:**
- Reject newlines (`\n`), carriage returns (`\r`), null bytes (`\x00`) in headers
- Reject invalid email formats
- Reject multiple `@` signs in single email address
- Reject comma-separated addresses in single recipient field
- Allow newlines in body text (for HTML and plain-text content)

## MIME Structure

The generated message uses the following structure:

```
multipart/alternative
├── text/plain (UTF-8)
│   └── Auto-generated plain-text alternative
└── text/html (UTF-8)
    └── Approved HTML body
```

This structure follows RFC 2046 (MIME Part Two: Media Types). Email clients will display the HTML version and fall back to plain-text if HTML is not supported.

## Gmail API Compatibility

The MIME messages produced by the MIME Builder are compatible with Gmail API's `messages.send` method:

```python
# Python Gmail API example (future implementation)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

credentials = Credentials.from_service_account_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/gmail.send']
)

gmail = build('gmail', 'v1', credentials=credentials)

# msg is the result of build_mime_message()
raw = message_to_base64url(msg)

result = gmail.users().messages().send(
    userId='me',
    body={'raw': raw}
).execute()
```

## Testing

The MIME Builder includes comprehensive tests covering:

- Basic message construction
- Multiple recipients and CC/BCC
- Unicode in subject and body
- HTML preservation
- MIME structure validation
- Encoding and RFC 2822 compliance
- Header injection security
- Input validation
- Base64url conversion
- Complex real-world scenarios

Run tests with:

```bash
pytest tests/test_mime_builder.py -v
```

## Limitations and Future Enhancements

### Current Limitations
- Attachment support not implemented (emails are text-only with HTML alternative)
- Single plain-text alternative (not multiple languages)
- No delivery confirmation tracking in MIME Builder (delegated to transport layer)

### Future Enhancements
- Attachment support (for logos, posters embedded as inline images)
- Multiple plain-text alternatives (different languages)
- Support for custom headers (Reply-To, Priority, etc.)
- DKIM signing integration with transport layer

## Error Handling

### MIMEBuilderValidationError
Raised when input validation fails (invalid email, injection attempt, etc.).

```python
try:
    msg = build_mime_message(...)
except MIMEBuilderValidationError as e:
    logger.error(f"Invalid email data: {e}")
    return jsonify(error=str(e)), 400
```

### MIMEBuilderError
Raised when message construction fails (unexpected error).

```python
try:
    msg = build_mime_message(...)
except MIMEBuilderError as e:
    logger.error(f"Failed to build MIME message: {e}")
    return jsonify(error="Internal server error"), 500
```

## Configuration

The MIME Builder does not require configuration. It uses Python's built-in `email` module.

Email addresses and credentials are provided by the caller (e.g., from environment variables or configuration).

Example Flask configuration:

```python
# .env
BRAHMAND_EMAIL_ADDRESS=events@brahmand.edu
PRESIDENT_EMAIL=president@brahmand.edu
VP_EMAIL=vp@brahmand.edu
ADMIN_EMAIL=admin@brahmand.edu
```

Example Flask code:

```python
import os
from services.mime_builder import build_mime_message

sender = os.getenv("BRAHMAND_EMAIL_ADDRESS")
recipients = [
    os.getenv("PRESIDENT_EMAIL"),
    os.getenv("VP_EMAIL"),
    os.getenv("ADMIN_EMAIL")
]

msg = build_mime_message(
    sender=sender,
    recipients=recipients,
    subject="Test Email",
    html_body="<p>Test</p>"
)
```

## References

- [RFC 2822: Internet Message Format](https://tools.ietf.org/html/rfc2822)
- [RFC 2046: MIME Part Two: Media Types](https://tools.ietf.org/html/rfc2046)
- [RFC 4648: Base64 Data Encodings](https://tools.ietf.org/html/rfc4648)
- [Gmail API: Send Messages](https://developers.google.com/gmail/api/reference/rest/v1/users.messages/send)
- [Python email module](https://docs.python.org/3/library/email.html)
