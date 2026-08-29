# R4-422 Google Gmail Exactly-One Synthetic Send Preparation

Date: 2026-08-29
Status: `PREPARED_GOOGLE_GMAIL_SINGLE_SEND_HUMAN_GATE`

The independent contract `contracts/provider/r4-422-google-gmail-single-send-validation-v1.json`
freezes exactly one Gmail API v1 `users.messages.send` request to one synthetic
recipient using the existing repository-external Windows OAuth token store.
Canonical SHA-256: `16e6f9dd68fd261f28047b0e7ea8e2f19e186ba3c04dd68c7c8a7d3606dea663`.
The only OAuth scope is `gmail.send`; OAuth sessions, token exchanges, browser
login, SSH, retries, fallback, reads, batch operations, attachments, CC, BCC,
and Google/account/resource mutations are all zero.

Preparation is offline-only. The adapter remains disabled by default, MIME
construction and the one-recipient boundary are locally covered, and a second
send is rejected by the bounded contract. The known repository-external token
store is present, but the current Codex process and User scope do not expose its
environment reference; stored-credential resolution therefore remains a
fail-closed execution precondition. Evidence records only booleans, counts, and
redacted configuration status. No raw address, token, credential, message body,
or provider response is retained.

Historical AWS SES contracts and evidence are preserved unchanged. This
preparation establishes no Gmail provider, delivery, or production claim.
No Gmail API, OAuth, browser, SSH, or account/resource operation occurred.

The exact contract digest is recorded in the companion JSON and must be
validated again before any future request. Execution remains blocked at the
new Human Gate.
