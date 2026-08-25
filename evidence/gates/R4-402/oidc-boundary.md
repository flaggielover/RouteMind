# R4-402 OIDC Authentication Boundary Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `6bb86573719b30f64e0d2d51a2942fbf073df193`

Status: in progress - `CI_PENDING`

## Implemented boundary

- Added the Spring Security OAuth2 Resource Server boundary to the Java
  business API without moving durable authorization into a framework, client,
  Python service, or agent.
- Enabled mode fails closed unless issuer, audience, JWK Set URI, and role claim
  semantics are explicit. Remote issuer and key endpoints require HTTPS and
  must share an authority; HTTP is limited to an explicit loopback-test flag.
- JWT validation combines signature verification with issuer, timestamp,
  audience, subject, token identifier, issued/expiry time, bounded role, and
  bounded scope requirements.
- Enabled HTTP security is stateless, disables request caching and local logout,
  permits only health/info anonymously, authenticates business/metrics paths,
  and denies unlisted paths.
- `X-Actor` on legacy commands must match a verified `ROLE_*` authority before
  the controller can use it. The same JWT claims map to the existing
  framework-independent `AuthenticatedPrincipal`, while Java application and
  domain policy still own durable command authorization, versioning,
  idempotency, audit, transactions, and Outbox events.
- Disabled mode is an explicit local-only stateless compatibility chain. It
  permits existing local workflows without accidentally enabling Boot's Basic
  login, form login, saved requests, or CSRF session state.

## Threat and operations contract

`docs/security/R4_OIDC_THREAT_MODEL.md` specifies token, session, logout, key
rotation, failure, replay, confused-deputy, privilege-escalation, key-confusion,
token-leakage, and service-to-service boundaries. It separates this locally
tested implementation from a real identity-provider deployment, revocation
drill, emergency key rotation, workload-identity rollout, or production TLS
verification.

## Local validation

- `./scripts/business-api.ps1 test`
- 89 Java tests passed, 0 failures, 0 errors, 0 skipped.
- The eight new directed tests cover secure/invalid configuration, loopback
  isolation, exact audience, required replay identity, role/scope mapping,
  anonymous health, authenticated API access, deny-by-default paths, and actor
  role mismatch.
- Existing architecture rules and all prior Java integration tests passed.
- `git diff --check` passed.

## Recovery record

The first test invocation was interrupted when the external `F:` workspace
volume disappeared. Read-only disk inspection confirmed the entire volume was
absent; no alternate clone or divergent write was created. After the volume
returned, the cached Maven JAR and working tree were verified before retrying.
The next run exposed Boot's default security auto-configuration in disabled
mode; the explicit local compatibility chain fixed that regression, after which
the complete suite passed twice (88/88 before actor binding and 89/89 after it).

## Evidence boundary

This checkpoint does not claim a live IdP, credential, certificate, revocation,
JWKS outage, or production key-rotation result. R4-402 remains `in_progress`
until the implementation commit passes every required GitHub Actions job.
