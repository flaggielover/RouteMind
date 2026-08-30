# R4-422 Gmail Credential Lifecycle Offline Audit

Date: 2026-08-30

## Boundary

This is a local, read-only audit of the consumed refresh-only evidence, the
consumed V2 preflight evidence, RouteMind source, and the locally cached Google
OAuth client bytecode. It performed zero Google, Gmail, OAuth, token refresh,
browser, SSH, or email operations. Secret, token, client-secret, address, and
external-path values were not read or recorded. Historical contracts and
evidence remain unchanged.

## Findings

### Token-store identity

The refresh executor and the V2 preflight both read the same four environment
inputs, validate the repository-external paths through `GmailOAuthPathPolicy`,
construct a `FileDataStoreFactory`, and load the configured user entry through
`GoogleAuthorizationCodeFlow.loadCredential`. The V2 helper delegates directly
to that same loader. The path policy normalizes absolute paths, resolves the
real path, rejects link redirects, and requires the store outside the
repository.

This proves the implementations resolve the same path and user-key algorithm.
The redacted historical artifacts do not retain path identities or the user key,
so equality of the two historical process environments cannot be proven.

### Refresh persistence

The locally cached Google OAuth client implementation shows that
`AuthorizationCodeFlow.newCredential` automatically attaches
`DataStoreCredentialRefreshListener` when a `DataStore` is configured. A
successful `Credential.refreshToken()` applies the token response to the
in-memory credential and invokes that listener. The listener creates a
`StoredCredential` and calls `DataStore.set(userId, storedCredential)`.
An I/O failure from the listener propagates out of the refresh call.

Therefore the historical `REFRESH_SUCCEEDED` result proves a successful token
response, an in-memory update, and that the standard persistence listener
returned without an error in that process. The evidence does not include a
post-refresh store listing or a sanitized before/after metadata comparison, so
it cannot prove what a later process read from the external store.

### Process and cache behavior

Both commands are one-shot processes. Each constructs its own transport, data
store, flow, and credential object. No static or shared credential cache exists
in these paths, so a stale in-memory object cannot survive from the refresh
process into the V2 process. A later stale read would require a persistent-store
state or environment difference not retained by the evidence.

### Freshness and clock behavior

V2 stops unless the readiness assessment is `READY_WITHOUT_REFRESH`. The exact
refresh-required predicate is: missing or blank access token, missing expiration,
or `getExpiresInSeconds()` at or below 120 seconds. Only after that predicate is
true does the code independently check whether a nonblank refresh token exists.
Refresh capability is therefore not confused with current readiness.

The Google client computes remaining seconds from expiration milliseconds minus
the current `Clock.currentTimeMillis()`, using integer division by 1000. The
RouteMind code does not convert units or apply another clock. No local clock,
skew, or unit defect was found. The V2 artifact records only the safe result
`CREDENTIAL_REFRESH_REQUIRED`; it does not record which of the three freshness
subconditions was true.

## Disposition

Classification: `EXTERNAL_CREDENTIAL_BEHAVIOR_REQUIRES_FURTHER_EVIDENCE`

Confidence is low for the historical root cause. No local credential lifecycle
defect is confirmed, and no Phase 3 credential repair was performed. The
remaining discriminator is sanitized, process-to-process evidence of the
external store identity and persisted credential metadata before and after a
future separately approved operation. This checkpoint does not create or
execute that operation.

## Verification

- External provider, OAuth, refresh, browser, SSH, and email operations: `0`
- Historical refresh evidence and V2 preflight evidence: inspected read-only
- Google OAuth client bytecode: inspected from the local Maven cache
- Local full gate and resilience gate: passed before this audit checkpoint
- Leakage scan: `google-gmail-credential-lifecycle-offline-audit-20260830-leakage-scan.json`

Next safe action: stop. Any future credential or message operation requires a
new independent contract and Human Gate; the consumed V2 contract must not be
reused.
