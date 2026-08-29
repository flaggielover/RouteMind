# Gmail OAuth Bootstrap V2 Execution

Status: `COMPLETED_OAUTH_BOOTSTRAP / NO_GMAIL_OPERATION / NO_PRODUCTION_CLAIM`

Contract: `contracts/provider/r4-422-google-gmail-oauth-bootstrap-v2.json`

Contract SHA-256: `e6fc0dec19ea96c2eaee337694e7a0a19716e5491ea4b50d9be09892391ca22e`

The approved session used one operator-managed strict-host-key SSH remote
forward from Windows to `suzhe@10.10.1.27`. The Windows listener was bound only
to `127.0.0.1:54348`; the Mac loopback endpoint was `127.0.0.1:52817`. One
preflight request returned `ROUTEMIND_GMAIL_OAUTH_TUNNEL_READY`, after which the
single OAuth URL was emitted. The operator completed one Desktop OAuth session
for exactly `https://www.googleapis.com/auth/gmail.send`, one callback was
consumed, and one token exchange completed.

No Gmail message operation, email send, retry, fallback, Google resource
mutation, account mutation, or OAuth client mutation occurred. Authorization
code and token values were never logged, persisted in the repository, or
included in evidence. Credentials remain only in the approved external Windows
token store; its contents were not read.

The listener stopped automatically after completion. The operator then closed
the SSH tunnel, completing teardown. Observed external cost is USD 0.00; the
contract conservative bound remains USD 0.10. This evidence proves only OAuth
bootstrap readiness and token persistence, not Gmail API message capability,
email delivery, or production readiness. Any future Gmail message operation
requires a new independent contract and Human Gate.

Observed completion: `2026-08-29T13:26:36Z`.
Teardown confirmation: `2026-08-29T13:29:46Z`.

Evidence JSON: `evidence/gates/R4-422/gmail-oauth-bootstrap-v2-execution-20260829.json`.
Leakage scan: `evidence/gates/R4-422/gmail-oauth-bootstrap-v2-execution-leakage-scan-20260829.json`.
