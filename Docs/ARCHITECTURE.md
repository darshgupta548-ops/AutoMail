# AUTO-MAIL — Architecture

## 1. Architecture Principle
The term **Agent** refers to a software module/responsibility, not an autonomous AI agent.

> **AI interprets. The renderer decides. The mail service delivers. Humans approve.**

## 2. High-Level Architecture

```text
Input & UI
   │
   ├──────────────► Image Hosting (Cloudinary)
   │                         │
   ▼                         ├──────────► Sense Maker
Sense Maker ◄────────────────┘
   │
   │ Human Review
   ▼
Email Maker
   │
   │ Human Review (STAGE 05)
   ▼
MIME Builder
   │
   │ Test Transmission (STAGE 06)
   ▼
Gmail Sender
   │ (future implementation)
   │
   ▼
Executive Reviewers
   (President, VP, Me)
   │
   │ External Approval
   ▼
IT Admin
   │
   ▼
Final Transmission
   │
   ▼
Students
```

## 3. Low-Level Architecture

```text
Browser UI
   │ HTTP
   ▼
Flask Application
   ├── Input Controller
   ├── Workflow / State Manager
   ├── Asset Service ─────► Cloudinary
   ├── Sense Maker ────────► Gemini API
   ├── Context Validator
   ├── Email Maker
   │     ├── Template Loader
   │     ├── Theme System
   │     ├── Component Renderer
   │     └── Responsive Rules
   ├── Preview
   │     ├── Desktop
   │     └── Mobile
   ├── MIME Builder ────────► RFC 2822 Message
   │     ├── Header Construction
   │     ├── Multipart Assembly
   │     ├── Base64url Encoding
   │     └── Security Validation
   └── Mail Sender ───────► Gmail API
       (future implementation)
```

## 4. Module Responsibilities

### 4.1 Input & UI
Collect poster, message, manual details, theme, and recipient/test recipient.

### 4.2 Image Hosting
Validate uploads, upload assets, and return HTTPS URLs.

### 4.3 Sense Maker
Combine poster, message, and manual details. Extract facts, summarize, write concise copy, generate subject text, and optionally recommend visual treatment. It must not invent missing facts.

### 4.4 Context Review
Human verifies and corrects AI output before rendering.

### 4.5 Email Maker
Convert approved structured context into deterministic email-safe HTML using a controlled base template and reusable components.

The application generates **one final visual design for each event**. The body background image, color palette, font palette, accents, and other visual choices may change from event to event.

### 4.6 Responsive Layout
Define explicit desktop/mobile behavior for images, typography, columns, logos, spacing, and CTA.

### 4.7 Theme System
Maintain controlled Light and Dark email themes. The selected theme is a design choice, not a guarantee about the recipient's device theme.

### 4.8 Preview
Render the same generated email for desktop and mobile review.

### 4.9 Email Approval (STAGE 05)
Human verifies the final rendered email, including visual hierarchy, mobile presentation, and asset usage. The approved HTML becomes the source of truth for transmission.

### 4.10 MIME Builder
Construct a standards-compliant MIME/RFC 2822 email message from the final approved HTML, subject, and recipient information.

**Responsibilities:**
- Convert approved HTML body to MIME format
- Generate plain-text alternative from HTML
- Set proper headers (From, To, Cc, BCC, Subject)
- Handle UTF-8 encoding
- Prevent header injection
- Produce RFC 2822 compliant message
- Enable base64url encoding for Gmail API

**NOT responsible for:**
- Sending email
- OAuth or authentication
- Recipient list management
- Email provider integration
- UI logic
- Email regeneration or editing

### 4.11 Gmail Sender (Future)
Submit the MIME message through Gmail API to the Brahmand Gmail account and deliver to intended recipients.

### 4.12 Test Send (STAGE 06)
Send the formatted message to exactly three executive reviewers:
1. President
2. Vice President
3. Me (Administrator)

Executives inspect the actual received email to verify:
- Correct rendering in their email clients
- Proper formatting across devices
- Asset loading
- Link functionality
- Visual hierarchy

External confirmation (chat, video call, in-person) constitutes approval.

### 4.13 Final Send
After executive approval via external communication, IT Admin authorizes final transmission to the intended recipient list.

## 5. Data Contracts

```text
Input UI
   ↓ InputData

Image Hosting
   ↓ AssetData

Sense Maker
   ↓ EmailContext

Human Review
   ↓ ApprovedEmailContext

Email Maker
   ↓ RenderedEmail

Human Review (STAGE 05)
   ↓ ApprovedRenderedEmail

MIME Builder
   ↓ MIMEMessage / RFC 2822

Gmail Sender
   ↓ MessageSent

Test Send (STAGE 06)
   ↓ ExecutiveReview

IT Admin Authorization
   ↓ FinalTransmission

Students
```

## 6. Workflow State

```text
DRAFT
ASSETS_READY
CONTEXT_GENERATED
CONTEXT_APPROVED
EMAIL_RENDERED
EMAIL_APPROVED
TEST_SENT
TEST_APPROVED
FINAL_SENT
```

Changing context invalidates the rendered email. A failed real-inbox test returns to Email Maker.

## 7. Suggested Project Structure

```text
AutoMail/
├── app.py
├── requirements.txt
├── .env
├── README.md
├── docs/
│   ├── SPEC.md
│   ├── ARCHITECTURE.md
│   ├── WORKFLOW.md
│   └── DECISIONS.md
├── templates/
│   ├── app/
│   └── emails/
│       └── base.html
├── services/
│   ├── asset_service.py
│   ├── sense_maker.py
│   ├── email_maker.py
│   ├── mime_builder.py
│   └── mail_sender.py
├── models/
│   └── email_context.py
├── static/
├── uploads/
├── generated/
└── tests/
```

## 8. Database Layer

Flask-SQLAlchemy persists each email-generation workflow in SQLite's `email_jobs` table. The database is local to the Flask instance directory; it stores workflow state and generation artifacts without implementing external-service behavior.

## Asset Upload Flow

The asset API receives a user upload in Flask, validates it through the Asset Service, uploads it to Cloudinary, and persists only the returned HTTPS URL on the matching EmailJob (`event_poster` or `email_bg`).

```text
User upload → Flask → Asset Service → Cloudinary → HTTPS URL → EmailJob
```

## Sense Maker Output

Sense Maker receives persisted EmailJob facts and the optional hosted poster, calls Gemini, and stores only a structured email_context JSON object. It produces content only; it does not generate HTML, CSS, Markdown, or email templates. The generated context proceeds to human review before the Email Maker stage.

```text
EmailJob → Sense Maker → Gemini → Structured email_context → Human Review → Email Maker
```

## MIME Builder Input and Output

The MIME Builder consumes the final approved rendered HTML from Stage 05.

```text
ApprovedRenderedEmail
    ↓
MIME Builder
    ├── Validate headers (prevent injection)
    ├── Set From, To, Cc, BCC, Subject headers
    ├── Create multipart/alternative message
    ├── Attach plain-text alternative
    ├── Attach HTML with UTF-8 encoding
    ├── Convert to RFC 2822
    └── Optionally encode to base64url for Gmail API
    ↓
RFC 2822 Message
```

## Stage 06 — Executive Test Send

After Stage 05 approval, the formatted email is sent via Gmail API to three executive reviewers for real-inbox testing.

```text
STAGE 06
    ↓
Send to: President, VP, Administrator
    ↓
Real email client inspection
    ↓
External approval (chat/call/face-to-face)
    ↓
FINAL SEND
    ↓
IT Admin authorizes final transmission
    ↓
Send to final recipient list
```
