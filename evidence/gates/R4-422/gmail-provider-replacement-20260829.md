# R4-422 Gmail API Provider Replacement

Date: 2026-08-29
Status: `IMPLEMENTED_OFFLINE / LIVE_VALIDATION_PENDING / NO_PRODUCTION_CLAIM`

## Decision

R4-422's acceptance criteria are provider-neutral notification semantics. The
historical AWS SES candidate is retired from the active runtime after three
preserved attempts ended in `FAILED_PROVIDER_REJECTED`; that result is not
converted into a pass. Google Gmail API is the active email-provider candidate
behind the same provider-neutral `NotificationProvider` boundary.

## Active architecture

`NotificationService -> NotificationProvider -> GoogleGmailNotificationProvider -> Gmail API users.messages.send`

The adapter is disabled by default. OAuth bootstrap, token loading, and runtime
invocation are separate steps. The only requested scope is
`https://www.googleapis.com/auth/gmail.send`; interactive consent never runs at
application startup. Gmail request construction uses a UTF-8 RFC 2822 MIME
message encoded with URL-safe Base64. Exactly one configured recipient is
allowed, with no CC/BCC, attachment, bulk operation, retry, or automatic
provider fallback. Provider errors are normalized to sanitized status/reason
categories and never retain raw payloads, tokens, or message content.

Google-managed processing is not claimed to be Tokyo-region pinned. A live
validation remains blocked behind a new exact contract and Human Gate.

## Retired SES boundary

All historical SES contracts, execution records, IAM audits, and support-package
artifacts remain append-only evidence. No historical digest or result was
modified. AWS SES dependencies and active Java wiring are removed from the
business-api build; historical Python validators and evidence are retained for
audit only.

## Offline result

The Gmail configuration, MIME builder, OAuth scope boundary, success/error
normalization, no-retry/no-fallback behavior, and disabled-by-default behavior
are covered by `GoogleGmailNotificationTests`. No AWS or Google API call, OAuth
consent, credential-store mutation, or email send occurred in this checkpoint.
The Java 17 build uses the aligned Google HTTP JSON runtime dependency
`google-http-client-jackson2:1.46.3`; the full Java suite (126 tests), control
plane gates, and repository `verify.ps1` gate passed locally.
The pushed implementation commit `c35306bc3fef51a0d624c55a36fa7a7fbc0b296a`
passed real GitHub Actions run `33244023747` with all five required jobs green.

Future bounded contract:
`contracts/provider/r4-422-google-gmail-live-validation-v1.json`.
