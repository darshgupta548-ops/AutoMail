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

### 3. MIME Builder (`services/mime_builder.py`) — **NEW**
Constructs standards-compliant RFC 2822 email messages from approved HTML:
- Multipart/alternative structure
- Auto-generated plain-text alternative
- UTF-8 encoding
- Header injection prevention
- Base64url encoding for Gmail API

### 4. Gmail Sender (`services/mail_sender.py`) — *Future Implementation*
Sends formatted messages through Gmail API:
- Brahmand Gmail account
- Production delivery
- Test send to executives
- Final transmission

## Documentation

- [ARCHITECTURE.md](Docs/ARCHITECTURE.md) — System design and module responsibilities
- [TECH_STACK.md](Docs/TECH_STACK.md) — Technology choices and rationale
- [DECISIONS.md](Docs/DECISIONS.md) — Architecture decisions and trade-offs
- [MIME_BUILDER.md](Docs/MIME_BUILDER.md) — MIME Builder module documentation
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

### 🔄 In Progress
- [ ] Gmail OAuth integration
- [ ] Gmail Sender implementation
- [ ] Stage 06 test send flow

### 📋 Future
- [ ] Stage 07 final transmission
- [ ] Delivery reporting
- [ ] Multi-language support
- [ ] Attachment support

## Environment Setup

Create a `.env` file with:

```
GOOGLE_API_KEY=your_gemini_api_key
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
BRAHMAND_EMAIL_ADDRESS=events@brahmand.edu
PRESIDENT_EMAIL=president@brahmand.edu
VP_EMAIL=vp@brahmand.edu
ADMIN_EMAIL=admin@brahmand.edu
```

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

## Next Steps for Development

1. **Gmail OAuth Integration**
   - Implement service account authentication
   - Configure OAuth scopes for sending emails
   - Test credential rotation

2. **Gmail Sender Module**
   - Implement `mail_sender.send_message(raw_mime)`
   - Handle API errors and retries
   - Log delivery status

3. **Stage 06 Test Send Endpoint**
   - Create `/api/jobs/<id>/email/send-test` endpoint
   - Send to President, VP, Administrator emails
   - Update job status to TEST_SENT

4. **Stage 07 Final Transmission**
   - Implement IT Admin authorization workflow
   - Implement final send endpoint
   - Track delivery confirmations

## Support

For questions about the architecture or implementation, see the Docs/ directory for detailed documentation.

