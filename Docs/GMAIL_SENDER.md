# Gmail Sender & OAuth

This document describes the backend Gmail sender identity and transport boundary used by AUTO-MAIL.

## Architecture

```text
EmailMaker
    ↓
Final approved HTML
    ↓
MIME Builder
    ↓
Authenticated Gmail Sender Identity
    ↓
Gmail Sender Service
    ↓
Gmail API
    ↓
Brahmand Gmail Account
```

The Gmail transport layer does not render email, modify the approved HTML, or expose user-controlled From fields.

## Sender Identity Model

The authenticated Gmail account is the single source of truth for the sender identity used by both Stage 06 and Stage 07. The backend stores the resolved sender state in the Flask session:

- email address
- display name
- profile image URL
- OAuth token state
- connection status

The frontend reads a safe session summary only. It does not receive OAuth refresh tokens, client secrets, or raw credentials.

## OAuth Flow

1. The user clicks Connect Gmail in the frontend.
2. The backend calls Google OAuth with the configured client ID / redirect URI.
3. The redirect URI validates against the configured env value.
4. The backend exchanges the code for tokens.
5. The backend calls Google profile APIs and resolves the authenticated Gmail email and avatar.
6. The sender identity is cached in server-side session state.

Required minimum OAuth scopes:

- openid
- email
- profile
- https://www.googleapis.com/auth/gmail.send

No service-account or delegated-sender flow is used for the sender identity.

## Logout

Logout clears the backend sender state and removes any stored authenticated session data. After logout:

- the frontend returns to the Connect Gmail state
- Stage 05 approval is blocked until a new sender is connected
- test/final send routes require a valid authenticated account

## Stage 05 semantics

Stage 05 is still the human review step for the final rendered email. Before an approved email can continue to transmission stages, the backend verifies that a Gmail sender is authenticated.

This ensures that the app is explicitly validating:

- which Gmail sender is currently authorized
- that the sender can be used for sending
- that the approval is tied to a real backend-managed sender identity

## Stage 06: Executive Test Send

Stage 06 sends the final approved HTML to the configured executive test recipients through the authenticated Gmail account.

Recipients are configured via environment variables and are not hardcoded in source code.

Configuration examples:

- TEST_SEND_RECIPIENTS
- FINAL_SEND_RECIPIENTS

The same authenticated Gmail sender is reused for Stage 06 and Stage 07.

## Stage 07: Final Send

Stage 07 remains the final authorized transmission. It is distinct from the executive test send and uses the same Gmail sender identity but the configured final recipient list.

The final IT Admin stage remains the authorization checkpoint for real transmission. It does not alter the sender identity.

## MIME Builder Integration

The Gmail sender does not regenerate email HTML. Instead, it uses the final approved HTML and the current sender identity to build a MIME object using the provider-agnostic MIME Builder, then passes that payload to the Gmail API.

This keeps the boundary intact:

```text
EmailMaker -> Final Approved HTML -> MIME Builder -> Gmail Sender -> Gmail API
```

## Security model

- No OAuth client secrets are exposed to JavaScript.
- No refresh tokens are returned to the frontend.
- No secrets are committed to the repository.
- Header injection is blocked by the MIME Builder.
- OAuth callback state is checked before accepting the authorization code.
- The frontend cannot override the From address or bypass send authorization.

## Local development

Configure these environment variables before running the app locally:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:5000/api/gmail/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/gmail.send
TEST_SEND_RECIPIENTS=president@example.com,vice-president@example.com,administrator@example.com
FINAL_SEND_RECIPIENTS=it-admin@example.com
FLASK_SECRET_KEY=local-dev-secret
```

## Intentionally not implemented yet

- Gmail inbox reading
- mailbox management
- arbitrary Gmail account switching
- multiple concurrent sender accounts
- billing or delivery analytics
- Resend fallback
