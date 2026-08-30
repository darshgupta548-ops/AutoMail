# AUTO-MAIL

## Project Information

- Project title: AUTO-MAIL
- Student name: Darsh
- GitHub username: darshgupta548-ops
- edX username: TBD
- City, Country: TBD

#### Video Demo: <URL HERE>

This project is being prepared for the CS50x final project submission and will require a recorded demo video before final submission to edX.

## Overview

AUTO-MAIL is an automated responsive mail generator for event-based institutional email. It is designed for communities such as college clubs, event organizers, and student organizations that need polished communication quickly without manually rewriting the same announcements from scratch. The core problem is that event planning already creates a lot of communication work: posters, WhatsApp announcements, venue details, registration links, and last-minute schedule updates. Turning all of that into a clean email still takes time, and if the messaging is not carefully maintained it can feel inconsistent, rushed, or low quality.

This application tackles that problem by taking raw event signals and turning them into a structured email campaign through a guided seven-stage workflow. The user provides the event details, uploads a poster and optional background asset, and the app uses Gemini to generate the email narrative and structure. From there, the workflow moves through review, rendering, verification, test sending, and human-approved final send. The system is not fully autonomous: it relies on human oversight at the key checkpoints where institutional communication quality matters. That is a good fit for a CS50 project because it combines practical problem solving with web application design, database design, API integration, validation, and iterative user-facing workflows.

AUTO-MAIL does not replace the organizer; it helps them move from a rough event brief to a finished email with clear review stages. The result is a tool that is especially useful in a college organization or community setting, where organizers often have to communicate to large audiences with limited time and limited marketing experience. For an event like a technical workshop, club announcement, public talk, or student gathering, the system helps convert the same information into a responsive email ready for real audiences.

## Seven-Stage Workflow

The application follows a strict seven-stage process:

1. Stage 01: Event input and asset upload
2. Stage 02: AI-generated email context from the supplied event data and poster
3. Stage 03: Context review and editing approval
4. Stage 04: Email generation and HTML rendering
5. Stage 05: Email verification and approval
6. Stage 06: Test send to designated review recipients
7. Stage 07: Final send to the user-entered custom recipient

This staged design matters because email communication is a high-trust action. A person can review the generated copy before it is sent, and each stage acts as a checkpoint. The product is therefore closer to a structured communication assistant than a black-box email sender.

The role of AI is central but intentionally bounded. Gemini is used at runtime in the Sense Maker layer to convert event information into a structured email context: subject, preheader, headline, intro, content sections, event details, CTA, and closing statement. The AI does not directly output the final HTML email; instead, it produces structured content that is validated, reviewed, and then rendered deterministically through Jinja templates. That separation keeps the project grounded in CS50 concepts of validation, schema design, and controlled data flow rather than allowing unstructured model output to be injected directly into final emails.

Human approval remains essential. Before any email is sent, the generated context and final HTML are reviewed by a user. Stage 06 and Stage 07 are intentionally distinct: Stage 06 uses a controlled set of test recipients defined in the environment for executive review, while Stage 07 requires a final recipient email entered by the user in the frontend. This protects the workflow from accidental broad sending and keeps the final step explicit and intentional.

## Design Choices

### Flask
Flask is used because the project needs a lightweight web framework that can manage routes, templates, session state, and a small API surface without unnecessary infrastructure. For a CS50-style project, Flask provides the right level of complexity: we can build a web app and maintain state in a straightforward way while still learning key concepts around server endpoints, validation, and request/response handling.

### SQLite and SQLAlchemy
SQLite was chosen because the project is local, lightweight, and easy to reason about for a final project. It allows AutoMail to persist job state, event data, and generated email content without introducing a separate database service. SQLAlchemy makes that persistence clean: the project uses model classes for `EmailJob` and `EmailContext`, maintaining the seven-stage workflow in a structured way instead of keeping everything in ephemeral browser state.

### JavaScript SPA/front-end
The front-end is implemented as a JavaScript-driven single-page workflow because the user experience is a multi-step process with staged transitions, form state, previews, and approval actions. A plain static HTML interface would become cumbersome. The JavaScript layer handles navigation, updates, and rendering state while still relying on the backend for actual business logic and persistence.

### Jinja templates
Jinja is used for the final HTML email rendering because it provides structured, deterministic templating while keeping content modular and maintainable. The project does not want raw AI output to become the final email markup; instead, Jinja assembles approved content and event-specific data into a consistent style and layout. This keeps the output predictable and easier for testing.

### Gemini
Gemini is a runtime feature of AutoMail: it analyzes the event poster, description, and other fields to generate a JSON email context that matches an explicit schema. This is useful because it reduces the time needed to turn rough event information into polished copy while still requiring human review. The important tradeoff is that Gemini is used as an assistant to the workflow, not as an uncontested source of truth.

### Cloudinary
Cloudinary is used for poster and background asset uploads because event communication depends on images and branding. The service supports secure URLs, image hosting, and easy asset reuse without storing large files in the Flask app itself. This keeps the app focused on email generation logic instead of local asset storage management.

### Gmail OAuth and Gmail API
Gmail OAuth is used so the application can authenticate as a real Gmail sender without storing user-provided credentials in the browser. The Gmail API then sends the final message through that authenticated identity. This is important for real-world functionality: the application can send through a legitimate Gmail account while still enforcing server-side control over the sender and token handling.

### Separate MIME builder
The MIME builder exists because raw HTML alone is not enough for email transport. It validates headers, builds a standards-compliant multipart/alternative message, auto-generates a plain-text alternative, and guards against header injection. This is a key CS50-style systems decision: the project separates business logic from transport details, which makes it easier to reason about correctness and test edge cases.

### Seven-stage workflow
The seven stages reflect the reality that event email creation is an approval-heavy process. They provide a workflow model that is easy to reason about, easier to test, and more reliable in practice. This also allows the project to demonstrate state management and system design without abandoning usability.

### Human approval before sending
Human approval is built into the product because email is a public-facing communication channel. The user reviews the generated context and the final HTML before test or final transmission. This reduces the chance of incorrect content, wrong links, or inappropriate tone going out to real recipients.

### Separate Stage 06 and Stage 07 sending
Stage 06 and Stage 07 are intentionally separated to support safe validation before high-consequence delivery. Stage 06 tests the message against real email delivery while keeping the recipients controlled, while Stage 07 requires a final recipient chosen by the user. This distinction addresses the practical issue that sending a final email should be explicit and deliberate rather than casually routed through the same process as a test.

### Server-side recipient validation
Server-side validation prevents malformed recipients, injection attempts, or accidental sending errors. The builder checks email addresses and rejects invalid patterns before the message is created. This is both a good engineering practice and a clear example of security-driven design in a web app.

## Files

The project is organized around a few core modules:

- `app.py` — Flask application factory, routes, and the primary application entry point.
- `extensions.py` — Shared SQLAlchemy database instance used across the app.
- `models/email_job.py` — SQLAlchemy model for the email workflow state and job data.
- `models/email_context.py` — Pydantic model that defines the structure returned by Gemini for email content.
- `services/asset_service.py` — Cloudinary upload and validation logic for event posters and backgrounds.
- `services/sense_maker.py` — Gemini-backed email context generator and request validation layer.
- `services/email_maker.py` — Jinja-based rendering of the approved context into final responsive HTML.
- `services/mime_builder.py` — Standards-compliant MIME message creation and header validation.
- `services/mail_sender.py` — Gmail OAuth, sender identity management, and email transmission through the Gmail API.
- `static/js/app.js` — Client-side workflow logic, state transitions, approval flows, and API calls.
- `static/css/style.css` — Styling for the mission-control interface and review screens.
- `templates/app/index.html` — Main UI shell for the seven-stage AutoMail workflow.
- `templates/app/context_review.html` — Context review page for editing AI-generated email content.
- `templates/app/email_review.html` — Final email preview and approval page.
- `templates/emails/base.html` — Final responsive HTML email template used for actual campaign delivery.
- `tests/` — Automated validation suite covering uploads, email rendering, MIME building, Gmail sending, and workflow validation.

The test files in this folder include the project’s automated checks for assets, email generation, MIME output, the Gmail sender wrapper, and validation logic.

## Documentation and Setup

Additional project documentation is stored in the `Docs/` directory and covers the architecture, stack decisions, decisions log, MIME builder, Gmail sender, and specification details.

A local `.env` file should define the project configuration, including Gemini, Cloudinary, Gmail OAuth, and the stage-06 test recipient list. Example keys include:

```bash
GOOGLE_API_KEY=your_gemini_api_key
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.example.com/api/gmail/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/gmail.send
TEST_SEND_RECIPIENTS=review1@example.com,review2@example.com
FLASK_SECRET_KEY=change-this-for-local-dev
```

- Stage 06 uses `TEST_SEND_RECIPIENTS` for controlled reviewer delivery.
- Stage 07 requires a custom recipient email entered by the user at runtime.
- Gmail API transmission is implemented and used in the production workflow, not just planned for the future.

The repository `.gitignore` includes the expected local exclusions for `.env`, Python caches, SQLite databases, `.venv`, and editor artifacts.

## Testing

The current project test suite is being verified on the `cs50-final` branch. The project is expected to have 167 tests; this number will only be reported if it is confirmed by the current `pytest` run.

## Notes on AI usage

Gemini is an intentional runtime feature of AUTO-MAIL used for email context generation and structured analysis of input data. That use is part of the application itself. Any AI coding assistance used during development is disclosed separately in the code comment at the top of `app.py` and is not presented as though the core implementation was built without AI support.

## References

- `Docs/ARCHITECTURE.md`
- `Docs/TECH_STACK.md`
- `Docs/DECISIONS.md`
- `Docs/MIME_BUILDER.md`
- `Docs/GMAIL_SENDER.md`
- `Docs/SPEC.md`