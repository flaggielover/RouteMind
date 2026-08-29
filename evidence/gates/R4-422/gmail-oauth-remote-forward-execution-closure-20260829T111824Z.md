# R4-422 Cross-Device Gmail OAuth Execution Closure

Status: `INCOMPLETE_CONSUMED / DIAGNOSTIC_INCOMPLETE / NO_RETRY`

Contract: `contracts/provider/r4-422-google-gmail-oauth-remote-forward-bootstrap-v1.json`

Contract SHA-256: `2ef914d10c541f800a61107bc521f3edbfcec05b608b8dc52c6c65bcd102c629`

One approved bootstrap session was launched. The Windows Java listener and one
Windows-initiated SSH process were started, but the Mac browser callback to
`127.0.0.1:52817` returned `ERR_CONNECTION_REFUSED`. Read-only inspection after
the report found no listener on port `52817` and no active Java or SSH process.
Therefore listener reachability and remote-forward liveness at callback time are
not established; the callback did not reach the Windows listener.

The operator's authorization/consent action is counted as one session. No
authorization code was captured, printed, logged, or persisted. Token exchange,
Gmail API requests, message operations, and email sends are all zero. The
external token-store metadata did not change during the attempt; token-store
contents were not read. SSH diagnostics were discarded by design.

The initial Java 8 Maven-plugin incompatibility was a local preflight failure
before SSH. A Java 17-only rerun reached URL generation but remained incomplete.
The approved contract is consumed under fail-closed semantics. No retry or new
OAuth session is authorized; any future bootstrap requires a new contract and
Human Gate. Historical contracts and evidence remain unchanged.

Evidence JSON: `gmail-oauth-remote-forward-execution-20260829T111824Z.json`.
