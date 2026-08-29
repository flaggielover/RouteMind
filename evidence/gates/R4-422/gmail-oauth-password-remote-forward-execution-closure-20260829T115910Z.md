# R4-422 Password Remote-Forward Synthetic Probe Closure

Status: `INCOMPLETE_CONSUMED / DIAGNOSTIC_INCOMPLETE / NO_RETRY`

The exact approved contract `3c8cb8104cad351b74620f68fa02129c516a46a458401ae78a909b3879aec215`
was consumed once. The Windows probe process launched one native `ssh.exe`
process using the fixed `suzhe@10.10.1.27` target, strict external
`known_hosts`, password authentication, and a loopback-only remote-forward
configuration. The process exited with code `1` before a synthetic request was
observed. SSH connection and remote-forward establishment are therefore
unconfirmed. The exact SSH diagnostics were not retained by design.

No Mac password was read, captured, echoed, logged, persisted, or automated by
Codex/Java. Synthetic request count is `0`; OAuth sessions, token exchanges,
Google requests, Gmail message operations, and email sends are all `0`. The
Windows listener and SSH process were torn down, and no resource or credential
store mutation occurred. Observed and conservative cost are USD `0.00`.

This is a real incomplete outcome, not provider evidence. No retry, second SSH
connection, OAuth session, or new contract is authorized automatically. Any
future attempt requires a new independent contract and Human Gate. Historical
key-based contract `2ef914d10c541f800a61107bc521f3edbfcec05b608b8dc52c6c65bcd102c629`
and its evidence remain unchanged.

Evidence JSON: `gmail-oauth-password-remote-forward-execution-20260829T115910Z.json`.
