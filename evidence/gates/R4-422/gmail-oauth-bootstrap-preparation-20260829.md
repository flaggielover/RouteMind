# R4-422 Gmail OAuth Bootstrap Preparation

Date: 2026-08-29
Status: `GMAIL_OAUTH_BOOTSTRAP_PREPARED / HUMAN_GATE_REQUIRED / NO_OAUTH_EXECUTED / NO_EMAIL_SENT`

## Boundary

The prepared command is an explicit operator invocation only. It reads the
Desktop OAuth client JSON from `ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE` and uses
`ROUTEMIND_GMAIL_TOKEN_STORE` as an existing writable directory. Both paths are
canonicalized and must resolve outside the RouteMind repository; redirects are
rejected. The operator identity is supplied only through
`ROUTEMIND_GMAIL_OAUTH_USER_ID`. No credential or token value is represented in
the application configuration, logs, evidence, or CI.

The flow uses the official Google OAuth client library with the single hardcoded
scope `https://www.googleapis.com/auth/gmail.send`, a loopback redirect bound to
`127.0.0.1` on an ephemeral port, one operator-controlled browser session, and
one token exchange. The operator performs Google login and consent. The command
does not construct a Gmail service and cannot invoke a message operation.

The command is not loaded by Spring, application startup, `resume.ps1`, or CI.
Gmail remains disabled by default. Existing Gmail live-send contract
`bc05c17490bcf1be3bd444ead6a68e941b29b0a09d71842283b228f8c5a811f1` is unchanged
and still requires its own Human Gate.

## Offline validation

Scope allowlist, missing environment inputs, malformed Desktop credentials,
repository-contained paths, external token-store semantics, and loopback URL
construction are covered by `GoogleGmailOAuthBootstrapTests`. No Google request,
OAuth consent, token exchange, Gmail message operation, Google Cloud mutation,
AWS request, or email send occurred.

The bootstrap contract is
`contracts/provider/r4-422-google-gmail-oauth-bootstrap-v1.json` with canonical
SHA-256 `ca3c1974b846f83846724091416f41bc431d51d9e26f1bfcdaac2b05c0ab9284`.
It authorizes only the future bootstrap session and stops before any Gmail
message operation.

Evidence is redacted and records only statuses, path semantics, counters,
contract digests, and artifact metadata.

Final local gate results: focused OAuth/Gmail Java tests `11/11 PASS`, Java
regression suite `PASS`, Gmail OAuth contract validator/tests `PASS`, control
plane validation and Round 4 graph gate `PASS`, security/leakage gate `PASS`,
and repository `verify.ps1` `PASS`. No new task denominator or production claim
was created by this preparation checkpoint.
