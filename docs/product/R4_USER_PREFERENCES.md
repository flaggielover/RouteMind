# RouteMind User Preferences

R4-421 makes the preference key from the frozen R4-420 contract executable:
`tenant_id + verified principal_id + namespace`. Java owns the durable state in
PostgreSQL. Python, the Web fixture sources, and LLM agents cannot write it.

The API is self-scoped. A caller supplies only the role-bound `X-Actor`; in OIDC
mode the verified JWT supplies the subject, tenant, and role. Local compatibility
mode maps the actor to a server-defined local subject and still rejects unknown
roles. A requested target principal, tenant header in OIDC mode, or mismatched
role is not accepted.

`GET /api/v1/preferences/{namespace}` returns a deterministic version-zero
default when no durable row exists. `PUT` requires a namespace-valid object,
`expectedVersion`, and a bounded `Idempotency-Key`. The transaction locks the
current row, applies the version precondition, appends an audit record, and
stores the idempotent response. Replays return the original version without a
second audit entry; a stale version returns `409 preference_version_conflict`.

The Web surface intentionally keeps a draft separate from the confirmed
snapshot. It represents loading, ready, stale, conflict, unavailable, and
rollback states, retains the draft on failure, and disables writes for demo,
replay, or degraded sources. No notification is sent by R4-421.
