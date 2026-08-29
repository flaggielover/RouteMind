# R4-422 Gmail OAuth Bootstrap V2 Preparation

The independent V2 contract
`contracts/provider/r4-422-google-gmail-oauth-bootstrap-v2.json` has canonical
SHA-256 `e6fc0dec19ea96c2eaee337694e7a0a19716e5491ea4b50d9be09892391ca22e`.

The implementation starts a Windows listener on `127.0.0.1` before generating
any authorization URL. It exposes one non-consuming
`/routemind-oauth-preflight` health endpoint. The operator manually runs a
strict, loopback-only SSH `-R` command to `suzhe@10.10.1.27` in a separate
terminal and enters the Mac password there. RouteMind never starts SSH or reads
the password. The OAuth URL is eligible only after one valid preflight request
returns `ROUTEMIND_GMAIL_OAUTH_TUNNEL_READY`.

After a future independent Human Gate, the command permits one fresh OAuth
session, one callback, and one token exchange using only `gmail.send`. Gmail
message operations, email sends, retries, fallback, and resource mutation are
forbidden. Client credentials and the resulting token remain in external
Windows-only paths; no code, token, query, or message content is recorded.

No SSH tunnel, preflight request, OAuth session, Google request, token exchange,
Gmail request, or email send occurred during preparation. Historical Gmail and
SES contracts/evidence remain unchanged. State is
`BLOCKED / OAUTH_BOOTSTRAP_V2_HUMAN_GATE_PENDING / NO_PRODUCTION_CLAIM`.

Evidence JSON: `gmail-oauth-bootstrap-v2-preparation-20260829.json`.
