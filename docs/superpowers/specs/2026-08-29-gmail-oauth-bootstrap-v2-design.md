# Gmail OAuth Bootstrap V2 With Operator-Managed SSH Tunnel

## Context

The prior cross-device Gmail bootstrap contracts are consumed and immutable.
They either used an automated SSH process or reached the Mac callback before a
live Windows listener and tunnel were proven. This design introduces an
independent V2 path without changing the historical commands, contracts, or
evidence.

## Goals

- Prove the callback tunnel before any Google authorization URL is emitted.
- Keep SSH password handling entirely outside RouteMind visibility.
- Allow exactly one `gmail.send` OAuth session and one token exchange.
- Persist OAuth tokens only in the existing repository-external Windows store.
- Make callback state, path, duplicate use, timeout, and teardown fail closed.
- Keep Gmail message operations and email sends impossible in this bootstrap.
- Preserve all historical evidence and claim boundaries.

## Non-goals

- No automatic SSH launch or password automation.
- No Gmail API request, message operation, or email send.
- No account, OAuth client, IAM, or cloud resource mutation.
- No modification of the consumed key- or password-based contracts.

## Architecture

The implementation is a new explicit `GmailOAuthBootstrapV2Cli`; the existing
bootstrap CLIs remain unchanged. The command is reachable only through a
dedicated operator script and is not loaded by Spring, CI, or `resume.ps1`.

1. The Windows process binds an HTTP server only to `127.0.0.1` and selects a
   fixed Windows listener port (`WPORT`) for this session.
2. The server exposes `/routemind-oauth-preflight` and `/oauth2callback`.
   Preflight is a separate, non-consuming health request and returns the fixed
   synthetic response `ROUTEMIND_GMAIL_OAUTH_TUNNEL_READY`.
3. The command prints a sanitized SSH template. The operator runs it manually
   in a separate Windows terminal and types the Mac password there:

   `ssh -N -T -o ExitOnForwardFailure=yes -R 127.0.0.1:MPORT:127.0.0.1:WPORT suzhe@10.10.1.27`

   RouteMind never starts SSH, reads stdin, captures output, or handles the
   password. The operator separately opens the Mac localhost preflight URL.
4. The authorization URL is generated only after exactly one valid preflight
   request for the active session and a live listener/tunnel confirmation.
5. The command creates one fresh OAuth state, emits one authorization URL, and
   accepts one callback only at the exact path. It validates state before
   exchanging the code, performs at most one token exchange, and stops.

## Configuration and boundaries

The V2 command reuses the existing external client-file, external token-store,
and operator-id environment variables. All paths are canonicalized and must be
outside the repository without redirecting links. The only allowed scope is
`https://www.googleapis.com/auth/gmail.send`; access is offline and the
redirect is `http://127.0.0.1:MPORT/oauth2callback`. No client secret, code,
token, query string, or message content is printed or persisted.

## Failure and teardown

The command stops and records redacted metadata if the listener dies, preflight
is missing or duplicated, the SSH tunnel disappears, callback path/state is
wrong, a callback is duplicated, the timeout expires, token exchange fails, or
path safety fails. It performs zero retry and zero second OAuth session. The
HTTP server is stopped in a `finally` block after every terminal outcome. A
future attempt requires a new independent contract and Human Gate.

## Evidence

Preparation and execution evidence records only contract identity, loopback
ports as non-secret session metadata, preflight/callback counts, state outcome,
token-exchange count, teardown, timestamps, and leakage-scan result. It records
no credentials, authorization code, token values, email addresses, raw query,
or provider response bodies containing sensitive data.

## Tests and gates

Offline tests cover loopback-only binding, preflight isolation, URL gating,
path/state validation, duplicate callback rejection, query/code non-logging,
external token-store containment, zero retries, timeout teardown, listener
teardown, historical contract non-reuse, and leakage scanning. The standard
RouteMind verification suite and real CI must be green before the new contract
is offered to a Human Gate. This design authorizes no OAuth or Google traffic.

## Human Gate output

After implementation, tests, evidence, commit, push, and CI success, prepare a
new independent V2 contract with a canonical SHA-256 and stop. The approval
statement must authorize only one operator-managed tunnel, one fresh OAuth
session, one callback, one token exchange, `gmail.send` only, no Gmail message
operation, no send, no retry, no mutation, and redacted fail-closed evidence.
