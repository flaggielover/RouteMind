# P8 Authentication and Authorization Boundary Contract

## Goal

Define a security boundary for the role-aware surfaces without making the web
client, Python compute runtime, or an LLM agent authoritative for business
permissions. Authentication establishes a caller principal; Java evaluates
durable command authorization against current party status, role, scope, and
resource ownership before changing state or writing an Outbox event.

## Principal and request context

An authenticated principal carries a stable subject identifier, issuer, token
identifier, issued/expiry times, and normalized role/scope claims. The boundary
rejects blank identity fields, expired or not-yet-valid credentials, unknown
issuers, duplicate claims, and audience mismatches. Request context also carries
correlation/request/trace identifiers, but observability identifiers never grant
permission.

## Authorization policy

Policies are explicit `(role, action, resource)` rules with a deny-by-default
result. A command is allowed only when the principal is active, the action is
listed for the role, the requested resource is in scope, and the expected
version/idempotency context is present. Forbidden, stale, malformed, and
repeated commands remain distinguishable for audit and client behavior. Every
decision records a reason code and policy version; secret/token contents are
never logged.

The web and compute runtimes may carry and forward a validated context, but
cannot mint credentials, bypass Java authorization, or write durable business
state. Agent tools remain read-oriented and separately permission-bounded.

## Validation boundary

The first implementation will provide a framework-independent Java policy
contract and unit tests for valid/expired/unknown-issuer principals, role and
scope checks, deny-by-default behavior, stale/repeated command context, and
audit-safe reason codes. Real OIDC/JWKS identity-provider verification,
rotation, key revocation, rate limiting, edge WAF, and production secret
management remain external deployment gates.
