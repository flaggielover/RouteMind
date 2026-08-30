# R4-422 Refresh-If-Required Single-Send Design

Date: 2026-08-30
Status: Approved for implementation design review
Scope: Preparation only. No execution authorization is granted by this design.

## Goal

Prepare one new, independently identified Gmail validation contract that can,
after a later Human Gate, load the existing repository-external Windows
credential, refresh it at most once only when readiness requires it, and send to
exactly one synthetic recipient at most once. The command must stop immediately
on refresh or send failure and must never start browser, SSH, OAuth consent,
Gmail reads, retries, fallback, or resource/account mutations.

All historical Gmail refresh, OAuth, and single-send contracts are consumed and
non-reusable. Their contracts and evidence remain append-only and unchanged.

## Boundaries and ownership

Java remains responsible for credential loading, readiness assessment, the
single refresh decision, request construction, and the bounded Gmail send.
Python remains responsible for canonical contract validation and static evidence
checks. The new command is a one-shot process; it does not add a service,
cache, queue, or durable business state.

The command requires explicit execution mode and the new contract digest. It
reuses the existing environment-based configuration and external-path policy.
The synthetic sender and recipient come from the existing non-secret execution
environment references; raw values are never persisted in evidence.

## Contract

The new contract is:

`contracts/provider/r4-422-google-gmail-refresh-if-required-single-send-v1.json`

Its canonical digest is computed by the repository contract tool after the file
is frozen. The contract records:

- `gmail.send` as the only OAuth scope;
- one credential load and zero new OAuth authorization-code sessions;
- at most one token refresh request, only when readiness requires refresh;
- at most one Gmail API v1 `users.messages.send` request;
- exactly one synthetic recipient, with no CC, BCC, attachments, batch, drafts,
  reads, or other message operations;
- zero retries, zero fallback, zero account/resource mutations;
- a 15-minute wall-time limit and USD 0.10 conservative ceiling;
- explicit preservation and non-reuse of every historical R4-422 Gmail
  refresh/send contract.

The contract tool rejects digest mismatch, missing historical non-reuse
declarations, broader scopes, larger budgets, and nonzero retry/fallback/read
limits.

## Execution flow

The Java executor follows one bounded state machine:

```text
explicit mode and digest
  -> load and validate external paths/client configuration
  -> construct one FileDataStore-backed Google flow
  -> load one Credential object
  -> assess readiness without network activity
  -> if ready: retain refresh count 0
  -> if refresh required: call refreshToken exactly once
  -> reassess the same Credential object in memory
  -> if unusable: record sanitized failure and stop
  -> construct the Gmail client with the current token snapshot
  -> send one synthetic request
  -> record sanitized provider outcome and stop
```

The executor does not use `Credential.initialize` for the send request because
that library interceptor can independently refresh near expiry. The bounded
executor instead applies the post-refresh token snapshot to a request
initializer after the explicit one-refresh decision. The provider is configured
with zero retries and no fallback, and observation validation rejects any
unexpected second request.

The refresh and send use the same loaded `Credential` object. A refresh failure,
an unusable post-refresh assessment, a provider rejection, or an observation
that violates the one-request bound terminates the process without another
network operation.

## Sanitized evidence

The executor emits only metadata sufficient to distinguish credential loaded,
refresh required, refresh attempted, refresh accepted, post-refresh usability,
send attempted, provider acceptance, safely available HTTP status, sanitized
error category/code, message-ID presence, request/refresh/recipient/retry/
fallback counts, elapsed time, and conservative cost.

Evidence must not contain access or refresh tokens, client secrets, authorization
headers/codes, raw token/provider responses, MIME content, complete addresses,
credential-file contents, raw exceptions, or external path values. A paired
leakage scan is committed with the preparation evidence.

## Offline test design

Tests use fake credentials and a fake bounded provider or request observer. They
must not construct a real network transport or read the external token store.
The suite covers:

1. usable credential, zero refresh, one send;
2. refresh-required credential, exactly one refresh, one send;
3. refresh failure, zero sends;
4. unusable after refresh, zero sends;
5. send failure, zero retries;
6. second-refresh attempt rejected;
7. second-send attempt rejected;
8. no CC/BCC/attachments/batch/read operations;
9. sanitized evidence excludes secrets and complete addresses;
10. contract digest and historical non-reuse validation.

Existing production provider request factories and notification domain types are
reused wherever they preserve these boundaries. Tests assert provider request
shape and counters rather than real delivery.

## Validation and release gate

Preparation runs the new contract validator/tests, focused Java tests, the full
Java gate, RouteMind verification, security and leakage scans, both Round 4
graph checks, and the final resume gate. It also runs the repository full gate
and resilience gate where required by the changed Java/control-plane surface.

Preparation evidence records zero Gmail API requests, zero token refresh
requests, zero OAuth/browser/SSH operations, and zero email sends.

Only after all local gates pass will the implementation and evidence be committed
as one coherent checkpoint, pushed to `origin/main`, and observed through real
CI. The process then stops at Human Gate. The new contract is never executed in
this task.

## Open evidence boundary

The audit that motivated this contract remains inconclusive about why the prior
refresh-only process was followed by a refresh-required V2 preflight. This new
contract may collect sanitized same-process refresh/send outcome metadata, but
it does not retroactively prove historical store identity or alter any consumed
evidence.
