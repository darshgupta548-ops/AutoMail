# AUTO-MAIL — Technology Stack

## 1. Stack Overview

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | HTML | Application structure and forms |
| Frontend | CSS | Application styling and responsive UI |
| Frontend | JavaScript | Client-side interaction, previews, workflow controls |
| Backend | Python | Application logic and service integration |
| Backend Framework | Flask | HTTP server, routing, orchestration, template rendering |
| Templating | Jinja | Controlled HTML/email templates with dynamic data |
| AI / Sense Maker | Gemini API | Understand poster/message/details and generate structured email context |
| Image Hosting | Cloudinary | Host posters/logos and provide HTTPS asset URLs |
| Email Maker | HTML + CSS + Jinja | Generate email-safe responsive HTML from approved context |
| MIME Builder | Python email module | Construct RFC 2822 messages with MIME/multipart structure |
| Email Transport | Gmail API | Deliver formatted messages through Brahmand Gmail account |
| Documentation | Markdown | Specification, architecture, workflow, decisions, README |
| Version Control | Git + GitHub | Source control and project history |
| Testing | Python test framework + real inbox testing | Automated checks plus real email-client verification |

---

## 2. Frontend

### HTML
Used for:
- input forms;
- poster upload;
- message/details input;
- context review;
- email preview;
- theme toggle;
- send/test controls.

### CSS
Used for:
- application UI;
- desktop/mobile application layout;
- preview framing;
- visual hierarchy;
- Light/Dark application themes.

The CSS used by the application UI is separate from the CSS embedded/generated for the final email.

### JavaScript
Used for:
- asynchronous requests to Flask;
- upload handling;
- preview updates;
- theme switching;
- form validation;
- workflow state updates;
- send/test actions.

---

## 3. Backend — Python + Flask

Flask acts as the application orchestrator.

Responsibilities include:
- receiving user input;
- validating requests;
- managing workflow state;
- calling Cloudinary;
- calling Gemini;
- passing structured data to the Email Maker;
- rendering application pages;
- returning previews;
- calling MIME Builder to format messages;
- calling Gmail API for delivery (future).

Flask keeps the external services behind application-specific modules rather than exposing provider-specific logic throughout the frontend.

---

## 4. AI — Gemini API

Gemini is used only by the **Sense Maker** module.

### Input

- event poster;
- pasted event/WhatsApp message;
- manually entered event details;
- hosted asset information where relevant.

### Output

A structured `EmailContext`.

Example:

```json
{
  "event": {
    "name": "Example Event",
    "date": "28 August",
    "time": "7:00 PM",
    "venue": "PDEU"
  },
  "content": {
    "greeting": "Hello, Space Explorers!",
    "headline": "Explore the Cosmos",
    "description": "A concise event description.",
    "highlights": [
      "Activity 1",
      "Activity 2"
    ]
  },
  "cta": {
    "text": "Register Now",
    "url": "https://example.com"
  },
  "subject": "Join Example Event"
}
```

### Constraint

Gemini does **not** generate the final HTML/CSS.

The AI provides meaning/content; the application's renderer controls the final structure.

---

## 5. Image Hosting — Cloudinary

Cloudinary handles image assets needed by the final email.

### Flow

```text
Browser
   ↓
Flask
   ↓
Cloudinary
   ↓
HTTPS image URL
```

The application automatically uploads the poster rather than requiring the user to manually host an image.

The returned HTTPS URL is then available to the Sense Maker and Email Maker.

Example:

```text
https://.../poster.jpg
```

The final HTML uses this URL in image elements.

---

## 6. Email Maker — Jinja + Email-Safe HTML/CSS

The Email Maker is a deterministic rendering layer.

### Core principle

> **The AI fills the data; the renderer controls the design.**

The system uses controlled boilerplates/templates rather than generating arbitrary HTML each time.

Suggested structure:

```text
templates/
└── emails/
    └── base.html
```

Jinja inserts the approved `EmailContext` into these templates.

Conceptually:

```text
Approved EmailContext
        +
Selected Theme
        +
Email Boilerplate
        ↓
      Jinja
        ↓
Final Email HTML
```

The generated email uses email-compatible structures and styling, including:
- table-based layout where appropriate;
- inline styles;
- responsive media-query rules where supported;
- fluid images;
- controlled typography;
- mobile stacking;
- CTA styling.

---

## 7. Email Visual System

AUTO-MAIL generates **one email design per event** rather than maintaining separate Light and Dark email templates.

The visual design is generated/selected for each event and may change every time.

The generated email may vary in:

- body background image;
- color palette;
- font palette;
- accent colors;
- supporting visual styling.

The important constraint is that the generated design remains responsive and email-safe.

The application does not assume it can know the recipient's device theme at send time. Recipient-side dark-mode transformation remains an external email-client behavior and is validated through actual email delivery.

---

## 8. Preview System

The Email Maker output should be previewed in:

```text
Desktop
Mobile
```

The preview is generated from the same final email HTML that is intended for sending.

This reduces the chance of having a browser preview that differs substantially from the artifact sent through Resend.

The preview is still not considered a substitute for real inbox testing.

---

## 9. Email Delivery — Resend API

Resend is used as the mail delivery layer.

### Input

```text
Sender
Recipient
Subject
Final HTML
```

### Flow

```text
Final HTML
    ↓
Mail Sender
    ↓
HTTPS request to Resend API
    ↓
Email delivery
    ↓
Recipient inbox
```

AUTO-MAIL does not manually implement an SMTP server or a MIME-construction layer for the MVP.

Resend accepts the HTML email body through its API and handles the lower-level delivery infrastructure.

---

## 10. Development Environment

Recommended:

- **VS Code** as the primary IDE.
- Python environment/virtual environment for Flask and supporting packages.
- Git for version control.
- GitHub for repository hosting and project history.

AI-assisted development tools may be used as helpers, while architecture and final implementation decisions remain controlled by the project author.

---

## 11. Configuration and Secrets

External credentials should be stored as environment variables.

Example:

```text
GEMINI_API_KEY=...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
RESEND_API_KEY=...
```

These values must not be hard-coded into source files or exposed to browser-side JavaScript.

A local `.env` file may be used during development and must not be committed to Git.

---

## 12. Testing Strategy

### Unit / Automated Testing
Test:
- input validation;
- EmailContext validation;
- renderer output;
- template selection;
- theme selection;
- error handling.

### Integration Testing
Test:
- Flask → Gemini;
- Flask → Cloudinary;
- Flask → Resend.

### Real Email Testing
Use a real mailbox/device to verify:
- desktop layout;
- mobile layout;
- image loading;
- typography;
- CTA behavior;
- Light/Dark theme behavior;
- email-client-specific rendering.

The real-inbox test is a required human QA gate before final institutional delivery.

---

## 13. Technology Boundaries

### Frontend handles
**Interaction and presentation.**

### Flask handles
**Orchestration and application logic.**

### Gemini handles
**Interpretation and content generation.**

### Cloudinary handles
**Hosted image delivery.**

### Jinja/Email Maker handles
**Deterministic email HTML generation.**

### Resend handles
**Email delivery infrastructure.**

### Human reviewer handles
**Final semantic, visual, and real-client approval.**

---

## 14. Final Technology Flow

```text
HTML / CSS / JS
       ↓
     Flask
       │
       ├──────► Cloudinary
       │
       ├──────► Gemini
       │
       └──────► Jinja Email Maker
                       ↓
                 Responsive HTML
                       ↓
                  Resend API
                       ↓
                 IT/Admin Inbox
                       ↓
                    Students
```

## 15. Core Technology Principle

AUTO-MAIL uses external services for infrastructure that is not the purpose of the project, while keeping the central intelligence and rendering workflow under application control.

> **Use APIs for infrastructure. Build the product logic yourself.**

## Persistence

AUTO-MAIL persists email-generation jobs with Flask-SQLAlchemy and SQLite. The local database is created in Flask's instance/automail.db path and is not committed to Git.

### Cloudinary Asset Uploads

Flask routes poster and background image uploads through the Asset Service. The service uses Cloudinary and stores only its secure HTTPS URLs in the corresponding EmailJob fields.
