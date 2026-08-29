# R4-422 Google Gmail V2 Exactly-One Synthetic Send Preparation

Date: 2026-08-30  
Status: `PREPARED_GOOGLE_GMAIL_SINGLE_SEND_V2_HUMAN_GATE`

The independent contract `contracts/provider/r4-422-google-gmail-single-send-validation-v2.json`
freezes exactly one Gmail API v1 `users.messages.send` request to one synthetic
recipient using the existing repository-external Windows OAuth token store.
Canonical SHA-256: `033bd4e5e3c92b65d94191a30fcae7d852dc92ae7441ef18c8bf8f959cba371f`.
The only OAuth scope is `gmail.send`; credential refresh, OAuth sessions, token
exchanges, browser login, SSH, retries, fallback, reads, batch operations,
attachments, CC, BCC, and Google/account/resource mutations are all zero in this
send contract.

The previously approved refresh-only contract was consumed successfully before
this preparation. The send contract therefore requires the stored credential to
be available and current without another refresh; if refresh is required, the
execution must fail closed without issuing a request. The adapter remains
disabled by default, MIME construction and the one-recipient boundary are
covered offline, and historical SES/Gmail contracts remain immutable.

Preparation is offline-only. No Gmail API, OAuth, browser, SSH, account, or
resource operation occurred. Evidence records only booleans, counts, contract
digests, and redacted configuration status. No raw address, token, credential,
message body, or provider response is retained. This preparation establishes no
Gmail provider, delivery, or production claim.

Execution remains blocked at the new Human Gate and requires exact digest
validation before any future request.
