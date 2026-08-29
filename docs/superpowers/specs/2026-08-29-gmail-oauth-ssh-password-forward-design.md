# Cross-Device Gmail OAuth SSH Password Forward

## Scope

This design replaces the key-authentication requirement for the cross-device
Gmail OAuth bootstrap with operator-entered interactive SSH password
authentication. It is independent of the consumed key-based contract
`2ef914d10c541f800a61107bc521f3edbfcec05b608b8dc52c6c65bcd102c629`.

The first executable stage is synthetic-only remote-forward validation. It
must stop before Google OAuth. A later OAuth stage, if justified, remains
bounded to one operator-controlled `gmail.send` consent session and one
Windows token exchange under a new contract.

## SSH Boundary

Windows initiates exactly one OpenSSH connection to the fixed target
`suzhe@10.10.1.27`. The command uses one remote forward:

`127.0.0.1:<mac-port>:127.0.0.1:<windows-port>`

The angle-bracket port tokens are intentional runtime-selected loopback values,
not unfinished requirements; the contract freezes their valid range and
loopback binding.

Host verification remains strict with an external pinned `known_hosts` file,
`StrictHostKeyChecking=yes`, `CheckHostIP=yes`, `ExitOnForwardFailure=yes`,
`PermitRemoteOpen=127.0.0.1:<windows-port>`, and no wildcard bind or
`GatewayPorts`. Public-key authentication is disabled explicitly. Password
authentication is enabled only through the native Windows `ssh.exe` prompt:

`BatchMode=no`, `PubkeyAuthentication=no`,
`PasswordAuthentication=yes`, `KbdInteractiveAuthentication=yes`, and
`PreferredAuthentications=keyboard-interactive,password`.

There is no `IdentityFile`, `IdentitiesOnly`, password environment variable,
`sshpass`, `expect`, `-pw`, SecureString conversion, stdin scripting, remote
command, or password helper. The Java child inherits Windows console stdin and
stderr so the operator types the password directly. Codex and Java never read,
capture, echo, persist, or log password bytes. SSH diagnostics are not
persisted.

## Synthetic-Only Validation

The validation command creates a Windows HTTP listener bound only to
`127.0.0.1` on an ephemeral port. It returns a generated non-secret probe
nonce and accepts one `GET /synthetic-probe` request. The operator manually
opens the printed Mac loopback URL (or runs a local Mac browser/curl command)
and confirms the response. No remote shell is used. The command records only
redacted request/response metadata, tunnel liveness, timestamps, and teardown
state. It does not load a Google client file, construct an authorization URL,
accept an OAuth callback, exchange a token, or call Gmail.

## OAuth Boundary After Validation

OAuth remains a separate, explicit stage and cannot start automatically after a
synthetic pass. If a future contract authorizes it, the Mac browser performs
one consent session for exactly `https://www.googleapis.com/auth/gmail.send`.
The callback is forwarded to the Windows loopback listener, Windows performs
one token exchange, and only the external Windows token store is writable.
No Gmail message operation, email send, broader scope, or Google resource
mutation is allowed.

## Fail-Closed Behavior

Any digest mismatch, host-key mismatch, non-loopback bind, unexpected target,
password automation attempt, listener failure, tunnel exit, probe timeout,
extra request, or output-leakage finding stops execution and tears down the
listener and SSH process. There is no retry or fallback. A failed or partial
synthetic run consumes its contract and requires a new independent contract and
Human Gate.

## Evidence and Tests

The new contract must capture the exact target, strict SSH options, password
interaction boundary, synthetic request count, callback reachability, process
and listener state, timestamps, teardown, zero OAuth/Google/Gmail activity,
and leakage-scan result. Tests must prove that key options and password
automation are absent, console inheritance is present, host/port/bind limits
remain fixed, synthetic failure preserves redacted evidence, and OAuth remains
unreachable from the synthetic command. Contract validation uses a new
canonical SHA-256 and never mutates historical key-based evidence.

## Human Gate

The new independent Human Gate authorizes only the bounded password-based
synthetic remote-forward validation until its explicit pre-OAuth stop. It does
not authorize Google OAuth, token exchange, Gmail operations, or password
collection by Codex. Exact resources, ports, duration, retry limits, evidence,
teardown, and the canonical digest are frozen in the new contract.
