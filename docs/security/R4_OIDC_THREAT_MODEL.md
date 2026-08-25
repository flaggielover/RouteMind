# Round 4 OIDC Authentication Boundary and Threat Model

## Boundary and deployment status

The Java business API is an OAuth 2.0 resource server when
`ROUTEMIND_OIDC_ENABLED=true`. This repository implements and tests the local
verification and identity-mapping boundary. It does not claim that a production
identity provider, DNS name, certificate, client registration, or revocation
operation has run.

Local development keeps OIDC disabled for compatibility. The disabled chain is
stateless and permits all local requests without enabling Basic or form login;
that mode is not a production posture. An enabled process fails during configuration binding unless
issuer, audience, and JWK Set URI are explicit. Remote endpoints require HTTPS;
plain HTTP is accepted only for an explicitly enabled loopback test endpoint.
Issuer and JWK Set URI must share scheme, host, and effective port.

## Token, session, logout, and rotation contract

- The API accepts Bearer JWT access tokens. Signature, issuer, expiry,
  not-before, and exact audience membership are validated before a request
  reaches a controller.
- `sub`, `jti`, `iat`, `exp`, a non-empty roles claim, and a non-empty `scope`
  claim are required. Role and scope values use a bounded identifier grammar.
  The token identifier is mandatory so audit and future
  replay controls do not collapse distinct credentials into an anonymous actor.
- The API is stateless and never stores authentication in an HTTP session. CSRF
  protection is disabled only because authenticated API calls use bearer headers
  rather than cookie credentials. Request caching and server logout are disabled.
- Logout is owned by the identity provider: the client discards the access token
  and invokes the provider's approved logout/revocation flow. The resource server
  does not pretend that deleting a local session revokes a JWT.
- The Nimbus decoder selects verification material from the configured JWK Set.
  Rotation uses overlapping old/new signing keys and distinct `kid` values. A
  provider must retain the old public key through the maximum accepted token
  lifetime. Unknown keys, invalid signatures, and unavailable uncached keys fail
  closed with HTTP 401; cached valid keys may continue until their cache policy
  requires refresh.
- Health and info probes are anonymous. Business APIs and metrics require an
  authenticated token. Unlisted paths are denied by default. A valid identity
  that lacks a later endpoint or durable permission receives HTTP 403.

## Authority ownership

Spring Security establishes a verified caller and maps normalized `ROLE_*` and
`SCOPE_*` authorities. When a legacy command supplies `X-Actor`, the enabled
boundary requires that value to match one verified token role before the
controller can use it; a client cannot select a role absent from its token.
`OidcPrincipalMapper` converts the same claims into the
framework-independent `AuthenticatedPrincipal`. Java domain/application policy
remains authoritative for durable commands, ownership, state transitions,
idempotency, current-version checks, transactions, audit, and Outbox production.
Neither a role claim alone nor an HTTP route-level success authorizes a durable
state mutation. Python, web clients, and analytical agents cannot mint or widen
this context.

## Threat analysis

| Threat | Control | Residual or next boundary |
| --- | --- | --- |
| Confused deputy or token substitution | Exact issuer/audience checks, same-authority JWKS configuration, required subject, and deny-by-default routes | R4-403 binds tenant and resource ownership inside each transaction |
| Replay | Short-lived signed tokens, required `jti`, durable command idempotency, version checks, and audit-safe token identity | Provider revocation and distributed `jti` deny-list are deployment policy, not claimed here |
| Privilege escalation | Roles/scopes are accepted only from a verified token; `X-Actor` must match a verified role; Java policy still evaluates the command | Role lifecycle and privileged access reviews require the selected IdP and operator process |
| Service-to-service impersonation | Workload tokens use the same issuer/audience/signature boundary and must carry bounded service roles/scopes; user and workload subjects remain distinguishable | Workload identity issuance and certificate/secret rotation are external deployment evidence |
| Key or algorithm confusion | Verification keys come only from the configured same-authority JWKS and signature validation precedes claim use | The selected IdP deployment must freeze allowed signing algorithms and exercise emergency rotation |
| Token leakage | Tokens and secrets are excluded from application evidence and logs; errors expose reason classes rather than credential contents | TLS termination, browser storage policy, WAF, and secret scanning continue in R4-404 |
| Stale authorization after logout | Short access-token lifetime and provider revocation/introspection policy bound the window; no misleading local logout exists | A real revocation drill requires external IdP approval and evidence |

## Failure semantics and operations

Malformed, unsigned, expired, premature, wrong-issuer, wrong-audience, missing
identity-claim, unknown-key, or bad-signature tokens return 401 without echoing
token material. Authenticated callers denied by a route or later Java policy
receive 403. Identity provider or JWKS failure never grants anonymous fallback.
Operators should alert on sustained 401 changes, JWKS refresh failure, unknown
`kid`, or issuer/audience mismatch, while avoiding subject and token cardinality
in metrics.

Production enablement requires approved issuer/audience values, TLS validation,
key-overlap and emergency-rotation drills, provider logout/revocation behavior,
workload identity issuance, alert routing, and rollback evidence. Those facts
must be recorded as external evidence rather than inferred from this code.
