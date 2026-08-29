# RouteMind Business API

This Java runtime owns durable business state, transactional domain behavior,
state machines, migrations, and event production. It does not contain dispatch or
research algorithms.

## Layers

- `domain`: pure business concepts and invariants; no framework dependencies.
- `application`: use cases and ports; may depend on domain only.
- `api`: inbound HTTP adapters; depends on application contracts.
- `infrastructure`: framework wiring and outbound adapters.

ArchUnit tests enforce the dependency direction.

## Notification provider

The active email-provider candidate is the disabled-by-default
`GoogleGmailNotificationProvider`. It uses the provider-neutral notification
port and Gmail API `users.messages.send` with the narrow
`https://www.googleapis.com/auth/gmail.send` OAuth scope. OAuth consent and
token loading are explicit operator steps; application startup performs no
Gmail network call. AWS SES remains only in append-only historical evidence
and is not active runtime wiring.

The operator-controlled OAuth bootstrap is invoked only through
`../../scripts/gmail-oauth-bootstrap.ps1` after its separate Human Gate. It
accepts `ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE`, `ROUTEMIND_GMAIL_TOKEN_STORE`, and
`ROUTEMIND_GMAIL_OAUTH_USER_ID` as process environment variables. The first two
paths must refer to an existing Desktop client file and writable token-store
directory outside the repository. Client credentials and tokens are never
printed or committed. The bootstrap uses one loopback redirect on
`127.0.0.1`, the single `gmail.send` scope, and performs no message operation.

When the operator must authenticate on a Mac, the separate
`../../scripts/gmail-oauth-bootstrap-remote.ps1` command starts the Windows
callback listener and initiates one strict SSH `-R` forward to the configured
Mac (`suzhe@10.10.1.27`). The Mac browser uses its own loopback port; callback
bytes are forwarded to the Windows loopback listener, and only Windows writes
the token to the external token store. The remote path requires
`ROUTEMIND_GMAIL_OAUTH_MAC_SSH_KEY_PATH`,
`ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS`, and
`ROUTEMIND_GMAIL_OAUTH_MAC_PORT`. It forbids wildcard binds, remote commands,
token transfer, Gmail message operations, and automatic retry, and remains a
separate Human Gate from the original loopback-only bootstrap.

The password-authenticated synthetic preflight is a different explicit command:
`../../scripts/gmail-oauth-remote-forward-password-probe.ps1`. It requires only
`ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS` and
`ROUTEMIND_GMAIL_OAUTH_MAC_PORT`. Native `ssh.exe` prompts in the Windows
terminal with public-key authentication disabled; the operator types the
password manually. The command inherits console input/error only, never reads
or persists password bytes, and serves one Windows-loopback
`/synthetic-probe` request before tearing down. It does not load OAuth client
material or generate a Google authorization URL. The password probe contract is
independent of the consumed key-based contract.

The V2 operator-managed OAuth bootstrap is invoked only through
`../../scripts/gmail-oauth-bootstrap-v2.ps1` after its own Human Gate. It starts
the Windows loopback OAuth listener first and prints a sanitized manual SSH
command; RouteMind never starts `ssh.exe` or handles the Mac password. The
operator runs the exact loopback-only `-R` command in a separate terminal and
opens the printed Mac preflight URL. Only after one valid
`/routemind-oauth-preflight` request returns
`ROUTEMIND_GMAIL_OAUTH_TUNNEL_READY` does the command emit the OAuth URL. The
V2 flow validates one callback state, performs at most one token exchange, and
stores credentials only in the external Windows token store. It uses only
`gmail.send`, never sends a Gmail message, and fails closed with zero retry.

## Commands

```powershell
../../scripts/business-api.ps1 test
../../scripts/business-api.ps1 run
```

The repository command resolves the active JDK from `PATH` so a stale machine-level
`JAVA_HOME` cannot silently run Maven with an older Java runtime.

The service uses PostgreSQL at `127.0.0.1:15432` and listens at
`http://127.0.0.1:18080` by default. Start dependencies from the repository root
with `../../scripts/infra.ps1 up`.
