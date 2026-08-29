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

## D7 — Gmail API for Production Transport
The production email transport layer uses Gmail API to send through the Brahmand Gmail account rather than third-party email services like Resend.

**Reason:** 
- Direct control over the institutional email identity.
- No additional email-service vendor or costs.
- Leverages existing institutional Gmail infrastructure.
- Flexibility for future bulk/scheduled transmission improvements.

**Security note:** OAuth is handled server-side and the authenticated sender identity is stored in the Flask session rather than in the frontend.

## D8 — MIME Builder for Message Construction
Before Gmail API integration, the MIME Builder module constructs standards-compliant RFC 2822 messages from the final approved HTML.

**Reason:**
- Separates transport-format construction from email provider integration.
- Enables provider-agnostic message preparation.
- Simplifies Gmail API integration later (just base64url-encode and send).
- Supports future multi-provider architecture if needed.
- Prevents header injection and other MIME format issues.

**MIME Builder responsibilities:**
- Convert approved HTML to multipart/alternative MIME format.
- Auto-generate plain-text alternative from HTML.
- Set RFC 2822 headers (From, To, Cc, BCC, Subject).
- Handle UTF-8 encoding properly.
- Validate inputs to prevent header injection.
- Optionally encode to base64url for Gmail API.

**MIME Builder does NOT:**
- Send email.
- Authenticate with Google.
- Manage OAuth.
- Decide recipients or authorization.
- Re-render or edit email HTML.
- Perform business logic.

## D9 — Light / Dark Email Themes
AUTO-MAIL provides controlled Light and Dark email themes. The application does not assume it can know the recipient's device theme.

## D10 — No Bulk Student Mailing
AUTO-MAIL sends the final message to IT/Admin. Institutional distribution remains outside the application.

## D11 — Flask as Orchestrator
Flask coordinates upload handling, external service calls, workflow state, rendering, preview, and sending.

## D12 — Jinja Templates
Approved context is injected into controlled email templates.

```text
Boilerplate + Approved Context
           ↓
       Template Renderer
           ↓
        Final HTML
```

## D13 — Stage 06 Executive Test Send
After Stage 05 email approval, a real email is sent via Gmail API to three executives (President, VP, Administrator) for real-inbox verification before final transmission.

**Reason:**
- Verifies correct rendering in actual email clients (not just browser preview).
- Catches device-specific issues early.
- Provides executive stakeholders visibility into the final message before institutional distribution.
- External approval via normal communication (chat, video, in-person) is sufficient authorization.
- Separates Stage 06 test approval from Stage 07 final IT Admin authorization.

**Important:** Stage 06 is NOT an in-app approval workflow. It is a real email sent to real inboxes with external confirmation of approval.

## D14 — In-Email Theme Toggle Deferred
An interactive Light/Dark control inside the received email is an experimental future feature because email-client support is inconsistent. It is not a guaranteed MVP feature.

## D15 — Backend-Owned Gmail Sender Identity
The authenticated Gmail account is the single source of truth for the sender identity and is not directly editable by the client.

**Reason:**
- Sender identity must remain consistent across Stage 06 and Stage 07.
- The app must never allow the frontend to override or spoof the From address.
- OAuth state and tokens are handled on the backend with minimal required Gmail scopes.
- The UI can present the account status to the user without exposing secrets or refresh tokens.
