# Workflow

AUTO-MAIL progresses through seven stages: event details and assets, context generation, context review, HTML rendering, email verification, restricted test transmission, and final transmission. Context and email content are persisted on the existing job; returning to review does not create another job.

After a successful Stage 06 test, users may proceed to Stage 07 or reopen review at Stage 03, Stage 04, or Stage 05. Reopening is accepted only from `TEST_SENT` or `TEST_APPROVED`, and is not available after `FINAL_SENT`. Stage 03 returns the job to context review; Stage 04 re-renders the approved context; Stage 05 returns the current HTML to verification. Any changed context or email must pass the normal render and approval steps, and the revised version must be test-transmitted before final delivery.

## Approval and transmission integrity

The backend stores SHA-256 fingerprints for the email HTML approved at Stage 05 and test-transmitted at Stage 06. The test, Stage 07 transition, recipient-save, and final-send endpoints compare those fingerprints with the current stored HTML. Editing or re-rendering invalidates the Stage 05 approval fingerprint; reopening also exits the tested/approved workflow states. Final delivery requires `TEST_APPROVED`, an authenticated Gmail sender, and matching current approval and test fingerprints, in addition to server-side recipient validation.

Existing SQLite databases are upgraded additively at startup with `email_approved_hash` and `test_sent_hash`; existing records are retained. Existing approved/tested jobs with rendered HTML initialize their fingerprints from that stored HTML to preserve their current workflow state.

## Recipients and themes

Stage 07 accepts one To address and optional comma, semicolon, or newline-separated CC addresses. CC recipients are visible to To and to one another. Valid recipient choices autosave to the email job while reviewing Stage 07 and are stored again before delivery. Stage 06 remains restricted to `TEST_SEND_RECIPIENTS` and does not use Stage 07 CC values.

The application defaults to the light ink-and-paper palette and includes a persisted Light/Dark theme switch. Reduced-motion preferences disable stage, preview, and status entrance animations. Email theme/branding and delivered HTML remain independent of the application theme.

Rendered HTML is stored as the reviewed snapshot. Existing approved and sent messages are not automatically rewritten by template changes. The generated email header retains its required SnT → Tesseract → Brahmand → OSAIL logo order; application styling does not leak into the email document.
