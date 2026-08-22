# P8 Deployment and Edge-Security Adapter Boundary

## Goal

Describe the integration boundary between RouteMind's auditable release
contracts and deployment/edge systems without pretending that local Compose
validation is production deployment. The adapter translates immutable release
and policy digests into provider-neutral checks and commands; the provider
retains credentials, traffic control, and runtime state.

## Adapter inputs and outputs

An adapter request binds release manifest digest, staged decision digest,
authorization policy version, rate/input policy digest, target environment, and
an explicit operation (`preflight`, `plan`, `apply`, or `rollback`). It contains
references to secret identities and provider capabilities, never secret values.
Responses include provider name/version, observed capability flags, immutable
operation id, and stable outcomes (`ready`, `blocked`, `accepted_external`, or
`failed_external`) with reason codes. A provider cannot rewrite source,
artifact, migration, recovery, or policy digests.

## Edge-security checks

The boundary requires explicit identity issuer/audience, TLS termination and
key-reference status, WAF/bot policy reference, distributed limiter reference,
and secret-manager identity. Missing, mutable, or unverified references fail
closed for apply/rollback. Local `preflight` and `plan` remain read-only;
`apply` and `rollback` require an external operator/CI gate and never run from
the local evaluator.

## Validation boundary

Tests will cover canonical request/response digests, capability mismatches,
missing secret references, immutable release linkage, fail-closed apply/rollback
gates, and read-only local operations. Provider API behavior, real TLS/WAF/
limiter enforcement, identity rotation, deployment health, and production
rollback remain external gates.
