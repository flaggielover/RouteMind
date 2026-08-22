# RM-086 Authentication and Authorization Boundary Evidence

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `45850cd5dcce04c3e6fcc9090f08650bfd978b65`
- Worktree: clean after the implementation checkpoint

## Contract

The Java domain security package defines immutable `AuthenticatedPrincipal`,
`AuthorizationRule`, `CommandAuthorizationRequest`, and explicit decision
records. `AuthorizationPolicy` validates issuer, audience, active status, and
credential time bounds, then applies deny-by-default role/scope/resource rules.
Repeated commands take precedence over stale versions, and forbidden, stale,
repeated, and invalid-principal outcomes carry stable reason codes and a policy
version. No credential contents are logged or persisted by this contract.

## Commands and results

1. `./mvnw.cmd -q -Dtest=AuthorizationPolicyTests test` with repository JDK
   17 -> 5 tests passed.
2. `./scripts/full-gate.ps1` -> Java 39 tests passed; Python 56 tests passed at
   96.05% statement/branch coverage; 4 schemas and 12 fixtures passed; Web
   formatting, lint, typecheck, unit, and production build passed; control,
   security, recovery, release-preflight, and staged-release self-tests passed.

The local gate intentionally resolves JDK 17 because the workstation's global
`JAVA_HOME` points to JDK 8. The Java tests cover active allow, deny-by-default,
expired and unknown-issuer rejection, repeated/stale distinction, and malformed
input boundaries.

## Boundary

This is a framework-independent Java policy boundary. OIDC/JWKS signature
verification, key rotation/revocation, rate limiting, WAF, and production secret
management remain external gates. Web, Python, and agent runtimes do not mint
credentials or bypass this policy.

## GitHub Actions

- Run: `32558622055`
- Commit: `7327aef3e74c5ccc000e3e12200530cb14b80aaa`
- Result: all five jobs passed: control plane and Compose, Java business
  runtime, Python compute and contracts, Web application, and bounded
  degradation/resilience.
