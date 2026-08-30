# AUTO-MAIL

Automated Responsive Mail Generator for event-based institutional email.

## Architecture Overview

AUTO-MAIL implements a multi-stage workflow for generating and delivering event emails:

```
Stage 01 — Input & Assets
    ↓
Stage 02 — AI Context Generation (Sense Maker)
    ↓
Stage 03 — Context Review & Approval
    ↓
Stage 04 — Email Rendering (Email Maker)
    ↓
Stage 05 — Email Verification & Approval
    ↓
Stage 06 — Test Send (Executive Review)
    ↓
Stage 07 — Final Transmission (IT Admin)
    ↓
Recipients
```

## Key Modules

### 1. Sense Maker (`services/sense_maker.py`)
Calls Gemini AI to generate structured email context from:
- Event poster (image)
- Event message/description
- Manual event details

### 2. Email Maker (`services/email_maker.py`)
Renders final responsive HTML email from approved context using:
- Jinja templates
- Responsive CSS
- Light/Dark themes
- Organization logos
- Event-specific assets

### 3. MIME Builder (`services/mime_builder.py`)
Constructs standards-compliant RFC 2822 email messages from approved HTML:
- Multipart/alternative structure
- Auto-generated plain-text alternative
- UTF-8 encoding
- Header injection prevention
- Base64url encoding for Gmail API

### 4. Gmail Auth + Sender (`services/mail_sender.py`)
Authenticates and manages the active Gmail identity used for transmission:
- Google OAuth for the Brahmand Gmail account
- backend-owned sender identity and session state
- profile image, display name, and email surfaced to the frontend
- logout and credential expiry handling
- provider-specific Gmail sending through the authenticated account

## Documentation

- [ARCHITECTURE.md](Docs/ARCHITECTURE.md) — System design and module responsibilities
- [TECH_STACK.md](Docs/TECH_STACK.md) — Technology choices and rationale
- [DECISIONS.md](Docs/DECISIONS.md) — Architecture decisions and trade-offs
- [MIME_BUILDER.md](Docs/MIME_BUILDER.md) — MIME Builder module documentation
- [GMAIL_SENDER.md](Docs/GMAIL_SENDER.md) — Gmail OAuth, sender identity, and transport architecture
- [SPEC.md](Docs/SPEC.md) — Requirements and acceptance criteria

## Testing

Run the full test suite:

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Current test coverage:
- 110+ baseline tests (assets, email rendering, validation)
- 43 MIME builder tests (message construction, security, encoding)
- **Total: 153 tests**

## Deployment Roadmap

### ✓ Completed
- [x] Sense Maker (AI context generation)
- [x] Email Maker (HTML rendering)
- [x] Asset management (Cloudinary)
- [x] Stage 05 verification
- [x] MIME Builder (message construction)

### ✅ Implemented
- [x] Gmail OAuth integration
- [x] Gmail sender identity/session management
- [x] Stage 06 transport gating and Gmail delivery wrapper
- [x] Stage 07 final send flow enforcement

### 📋 Future
- [ ] Inbox read / Gmail management features
- [ ] Delivery reporting and analytics
- [ ] Multi-language support
- [ ] Attachment support

## Environment Setup

Create a `.env` file with:

```
GOOGLE_API_KEY=your_gemini_api_key
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.example.com/api/gmail/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/gmail.send
TEST_SEND_RECIPIENTS=president@example.com,vice-president@example.com,administrator@example.com
FLASK_SECRET_KEY=change-this-for-local-dev
```

**Email Transmission Configuration:**
- **Stage 06 (Test Send):** Uses `TEST_SEND_RECIPIENTS` from `.env` for executive test recipients
- **Stage 07 (Final Send):** Uses a custom recipient email address entered by the user in the frontend UI

Do not commit real client secrets or tokens. Use `.env` locally and keep OAuth credential material out of source control.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start Flask development server
python -m flask run --app app
```

## Project Structure

```
AutoMail/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── Docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── DECISIONS.md
│   ├── MIME_BUILDER.md
│   └── SPEC.md
├── services/               # Business logic modules
│   ├── asset_service.py    # Cloudinary integration
│   ├── sense_maker.py      # Gemini AI context generation
│   ├── email_maker.py      # Jinja template rendering
│   ├── mime_builder.py     # RFC 2822 message construction
│   └── mail_sender.py      # Gmail API (future)
├── models/                 # SQLAlchemy models
│   ├── email_job.py        # Workflow state machine
│   └── email_context.py    # Structured email data
├── templates/              # Jinja templates
│   ├── app/                # Application UI
│   └── emails/             # Email templates
├── tests/                  # Test suite
│   ├── test_asset_uploads.py
│   ├── test_email_maker.py
│   ├── test_mime_builder.py
│   ├── test_sense_maker.py
│   └── test_validation.py
└── static/                 # CSS, JS, images
```

## Architecture Highlights

### Stage-Based Workflow
Each stage is a discrete approval checkpoint. Changes to earlier stages invalidate later stages.

### Deterministic Email Rendering
Email HTML is generated from controlled templates, not arbitrary AI-generated markup.

### Real-Inbox Testing (Stage 06)
Before final transmission, test email is sent to executive stakeholders for verification in actual email clients.

### MIME Format
Final message follows RFC 2822 standard with multipart/alternative structure (HTML + plain-text).

### Security
- Header injection prevention in MIME Builder
- No embedded credentials
- HTTPS-only asset URLs
- OAuth for Gmail authentication (future)

## Current Backend Gmail Flow

1. **Google OAuth**
   - `/api/gmail/connect` starts the server-side OAuth flow.
   - `/api/gmail/callback` validates the state and exchanges the authorization code.
   - The authenticated sender identity is stored in the Flask session, not in the frontend.

2. **Sender Identity**
   - The backend resolves the authenticated account profile and caches:
     - email address
     - display name
     - profile image URL
     - OAuth token state

3. **Stage 06 / Stage 07**
   - The same authenticated Gmail account is used for both test send and final send.
   - No editable From field is exposed to the frontend.
   - The system blocks transmission when no Gmail sender is connected.

4. **MIME Builder integration**
   - `mail_sender.build_message_for_job()` prepares the final RFC 2822 MIME message.
   - The Gmail sender uses the MIME output as the transport payload.

## Support

For questions about the architecture or implementation, see the Docs/ directory for detailed documentation.

