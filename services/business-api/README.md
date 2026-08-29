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
