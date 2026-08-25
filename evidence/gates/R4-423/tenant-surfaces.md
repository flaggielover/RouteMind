# R4-423 Tenant and Identity Aware Surface Evidence

Date: 2026-08-25 (Asia/Shanghai)

Implementation revision: `7bc03a85cb159b023b098b54a1d69311f0543abb`

Status: `LOCAL_VALIDATED / CI_VALIDATED`

## Implementation boundary

- OIDC-enabled Java exposes a read-only `/api/v1/session` projection from the
  authenticated JWT context through an application port. It returns normalized
  subject, tenant, roles, and expiry and is not enabled in local compatibility
  mode.
- Web session parsing rejects nil or malformed tenants, expired sessions, and
  unknown-only roles. Tokens are supplied by a host callback, verified by Java,
  carried in authorization headers, and never written to a URL or browser
  storage by RouteMind.
- Live navigation and deep links use verified roles. Live projections are scoped
  to tenant, subject, and roles; session changes clear cached identity and data
  before reloading.
- Live snapshots, preferences, and role commands carry bearer authorization.
  Java role operations bind `X-Actor` to an authorized session role.
- Authenticated fetch-SSE validates tenant identity before cursor or projection
  mutation. Cross-tenant, stale, cursor-gap, malformed, and unavailable states
  fail closed.
- Demo, replay, simulation, and supplied fixtures remain explicit isolated
  sources. They cannot authorize durable writes.

## Executable evidence

- Java targeted security and architecture gate: `7/7` tests passed, covering
  the session endpoint, verified JWT mapping, and API/application/infrastructure
  dependency direction.
- Java full Maven gate: `110/110` tests passed with zero failures, errors, or
  skips. The initial architecture failure caused by a direct API-to-infrastructure
  dependency was corrected through `CurrentSessionIdentity`; the final full gate
  is green.
- Web full unit gate: `36` files / `104` tests passed. Session, live snapshot,
  preferences, role commands, deep-link denial, session scope, tenant mismatch,
  authenticated SSE, stale, degraded, and unavailable behavior are covered.
- Web quality gates passed: Prettier, ESLint, TypeScript, and Vite production
  build.
- Playwright browser gate: `34` passed / `2` expected project-specific skips
  across desktop and mobile. The live fixtures verify bearer and actor headers,
  token-free URLs, tenant-aware SSE, explicit failure states, and axe accessibility.
- `git diff --check`: passed before repository verification.
- `./scripts/verify.ps1`: passed, including task graph, frozen evidence ledger,
  Claim Matrix, negative-result package, Round 4 graph, security, dependency,
  provenance, product, agent, Compose, and control-file gates.

No external identity provider, notification provider, paid service, production
data, or production credential was used. R3-325 remains frozen exactly as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` and was not rerun, tuned, reinterpreted,
or optimized.

GitHub Actions run `32839582664` passed all five jobs for the implementation
revision: Python compute/contracts, Java business runtime with supply-chain
evidence, role-aware Web static/unit/browser gates, bounded resilience, and the
repository control plane with Compose validation.
