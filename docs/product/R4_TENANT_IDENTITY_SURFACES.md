# R4 Tenant and Identity Aware Role Surfaces

R4-423 binds the operations, strategy, customer, merchant, and courier live
surfaces to one server-verified tenant session. The browser is a presentation
and transport boundary; it does not mint identity or decide durable business
authorization.

## Verified session boundary

When OIDC resource-server mode is enabled, Java exposes `GET /api/v1/session`.
The endpoint reads only the authenticated Spring Security JWT context and
returns the normalized subject, tenant, roles, and expiry. Its controller uses
an application port so the API layer does not depend on infrastructure mapping.
The endpoint is absent in local compatibility mode and returns no fabricated
production identity.

The host application supplies a short-lived access token through
`window.__ROUTEMIND_OIDC_ACCESS_TOKEN__`. The token is verified by Java before
the Web application accepts the session. It is never placed in a URL or browser
storage by RouteMind. The host dispatches `routemind:session-changed` after
sign-in, refresh, tenant switch, or sign-out; RouteMind immediately clears the
session and live snapshot before re-verification.

Server authorities map narrowly to surfaces: `operator` to operations,
`analyst` to strategy, and customer, merchant, and courier to their matching
surfaces. Invalid tenants, expired responses, and sessions without a recognized
role fail closed.

## Navigation and data isolation

Live navigation contains only roles in the verified session. Direct links to a
different role render an accessible authorization alert and never mount that
workspace. A live snapshot carries an identity scope derived from tenant,
subject, and sorted roles; navigation remains closed until the snapshot scope
matches the current session. A session-change event clears the old projection
before another tenant can be rendered.

Demo, replay, simulation, and explicitly supplied test sources are isolated
non-production sources. They may demonstrate all roles, but durable commands
remain disabled without a verified live identity and their UI states do not
claim production authorization.

## Authenticated transport

Live Java and Python snapshot requests carry the bearer token. Java-bound role
operations also carry an `X-Actor` value derived from an authorized session role;
a caller cannot request an actor outside its verified roles. Customer, merchant,
courier, and preference commands use the same binding.

Realtime uses authenticated `fetch` streaming rather than native EventSource so
the bearer token stays in the request header. Cursor state is the only query
parameter. Every event must contain the verified tenant ID; a cross-tenant event
is rejected before cursor or projection state changes. Reconnects are bounded,
and stale, gap, malformed, and unavailable outcomes remain explicit.

## Complete failure states

The shell and role views retain named, announced states for identity verification,
unauthorized access, loading, empty data, unavailable services, stale snapshots,
degraded realtime, conflicts, and disabled writes. Existing keyboard, responsive,
focus, and axe accessibility gates cover both desktop and mobile surfaces.

## Scope boundary

R4-423 does not implement an identity-provider login UI, provision tenants,
authorize provider credentials, make an external send, use production data, or
prove production deployment. Java remains the durable authorization authority,
Python remains the compute owner, and LLM agents receive no dispatch or durable
state authority.
