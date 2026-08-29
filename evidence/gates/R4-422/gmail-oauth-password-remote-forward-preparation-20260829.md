# R4-422 Password-Authenticated Remote-Forward Preparation

Status: `PREPARED_OFFLINE / HUMAN_GATE_PENDING / SYNTHETIC_ONLY / NO_OAUTH`

Contract: `contracts/provider/r4-422-google-gmail-oauth-password-remote-forward-v1.json`

Canonical SHA-256:
`3c8cb8104cad351b74620f68fa02129c516a46a458401ae78a909b3879aec215`

The new contract is independent of the consumed key-based remote-forward
contract. Windows uses native `ssh.exe` to the fixed `suzhe@10.10.1.27` target,
strict external `known_hosts` verification, and exactly one loopback-only
`ssh -R` forward. Public-key authentication and key-file options are disabled;
the only permitted authentication is the operator typing the password into the
Windows terminal prompt. RouteMind and Codex do not read, capture, echo, log,
persist, or automate password bytes.

The first execution stage is synthetic only. A Windows loopback listener serves
one `GET /synthetic-probe` request and returns a fixed non-sensitive marker.
The operator manually visits the Mac loopback URL. The stage stops before
Google OAuth: no client file is loaded, no OAuth URL is generated, no consent
session or token exchange occurs, and no Gmail message operation or email send
is possible.

The command is explicit and excluded from startup, CI, and `resume.ps1`.
Failures are fail-closed with immediate listener/tunnel teardown, no retry, and
append-only redacted evidence. Any future OAuth stage requires its own explicit
contract and Human Gate.

Validation artifacts:

- `evidence/gates/R4-422/gmail-oauth-password-remote-forward-preparation-20260829.json`
- `evidence/gates/R4-422/gmail-oauth-password-remote-forward-leakage-scan-20260829.json`
