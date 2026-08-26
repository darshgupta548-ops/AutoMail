# AUTO-MAIL — Architecture Decisions

## D1 — Controlled Boilerplate
The Email Maker uses predefined email-safe templates/components rather than arbitrary AI-generated HTML.

**Reason:** predictable structure, responsive behavior, maintainability, testing, and visual uniformity.

## D2 — Separate Sense Making from Email Making
AI produces structured context; the renderer produces HTML.

```text
Source Material
   ↓
Sense Maker
   ↓
Email Context
   ↓
Human Review
   ↓
Email Maker
   ↓
HTML
```

## D3 — Human Context Review
AI-generated content must be reviewed before rendering.

**Reason:** semantic errors are cheaper to correct before layout generation.

## D4 — Human Email Review
Generated HTML must be previewed and approved before delivery.

**Reason:** correct content can still produce poor visual hierarchy or mobile presentation.

## D5 — Real Inbox Testing
A test email is delivered to a human tester before final institutional delivery.

**Reason:** browser previews cannot guarantee identical behavior in actual email clients.

## D6 — Cloudinary for Email Images
Uploaded images are hosted externally and referenced using HTTPS URLs. The user should not have to manually host images.

## D7 — Resend for Delivery
The Mail Sender delegates delivery to Resend rather than reimplementing email infrastructure.

The project focuses on event-email automation, not mail-server implementation.

## D8 — Light / Dark Email Themes
AUTO-MAIL provides controlled Light and Dark email themes. The application does not assume it can know the recipient's device theme.

## D9 — No Bulk Student Mailing
AUTO-MAIL sends the final message to IT/Admin. Institutional distribution remains outside the application.

## D10 — Flask as Orchestrator
Flask coordinates upload handling, external service calls, workflow state, rendering, preview, and sending.

## D11 — Jinja Templates
Approved context is injected into controlled email templates.

```text
Boilerplate + Approved Context
           ↓
       Template Renderer
           ↓
        Final HTML
```

## D12 — In-Email Theme Toggle Deferred
An interactive Light/Dark control inside the received email is an experimental future feature because email-client support is inconsistent. It is not a guaranteed MVP feature.
