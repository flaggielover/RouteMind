# ADR-0040: Gmail API supersedes AWS SES for active email notifications

Date: 2026-08-29
Status: Accepted for offline implementation; live validation pending

## Context

R4-422 defines provider-neutral notification intent, consent, Outbox,
idempotency, delivery truth, and failure recovery. The historical SES candidate
was exercised under three bounded contracts and ended in a preserved
`FAILED_PROVIDER_REJECTED` result with no production claim. Repeating SES would
not add justified evidence, so the active email candidate must change without
rewriting that history.

## Decision

Treat R4-422 as provider-neutral and retire AWS SES from active runtime wiring.
Use `GoogleGmailNotificationProvider` behind the existing
`NotificationProvider` boundary. The adapter calls Gmail API v1
`users.messages.send` only after explicit injection of an OAuth initializer and
is disabled by default. OAuth uses only
`https://www.googleapis.com/auth/gmail.send`; consent/bootstrap, token loading,
and provider invocation are separate operations. No startup flow performs
interactive consent or network I/O.

The first Gmail validation is a separate exact contract limited to one
synthetic recipient, one send request, zero retries/fallback, 15 minutes, and
USD 0.10. Google-managed processing is not represented as Tokyo-region pinned.

## Consequences

SES contracts, execution evidence, IAM audit, and support package remain
append-only historical evidence and are not counted as Gmail validation. The
active Java build no longer contains SES dependencies or configuration. Gmail
outcomes are normalized into provider-neutral accepted, retryable, and terminal
failure states with sanitized metadata only. A new Human Gate is required
before OAuth consent or any Gmail API call.
