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
   │ Human Review
   ▼
Mail Sender
   │
   │ Test Email
   ▼
Mail Tester (Human)
   │
   │ Approved
   ▼
IT Admin
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
   └── Mail Sender ───────► Resend API
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

### 4.9 Mail Sender
Submit the approved HTML, subject, recipient, and sender information to Resend. AUTO-MAIL does not manually implement MIME construction when the delivery provider accepts HTML directly.

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

Mail Sender
   ↓ DeliveryResult
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
