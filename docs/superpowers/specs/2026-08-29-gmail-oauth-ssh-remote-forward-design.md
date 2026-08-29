# Gmail OAuth Cross-Device Bootstrap over SSH Remote Forward

Date: 2026-08-29

## Scope

This design adds an explicit, operator-invoked bootstrap path for a Windows
RouteMind host whose Google login and consent happen in a browser on the
operator's Mac. It does not send Gmail messages and does not replace the
existing loopback-only bootstrap contract.

## Topology

The Windows Java process binds an OAuth callback listener to
`127.0.0.1:<windows-port>`. Windows initiates one SSH connection to
`suzhe@10.10.1.27` using an external identity file and an external pinned
`known_hosts` file. The connection requests:

`-R 127.0.0.1:<mac-port>:127.0.0.1:<windows-port>`

The remote listener therefore exists only on the Mac loopback interface. The
Mac browser uses `http://127.0.0.1:<mac-port>/oauth2callback`; callback bytes
travel through the encrypted SSH channel to the Windows loopback listener.
The Windows process performs the single token exchange and persists the token
only in the already validated external Windows token store.

## Security boundaries

- SSH host and account are fixed to `10.10.1.27` and `suzhe` for this contract.
- `StrictHostKeyChecking=yes`, `CheckHostIP=yes`, `IdentitiesOnly=yes`,
  `ExitOnForwardFailure=yes`, and `BatchMode=yes` are mandatory.
- The identity file and `known_hosts` file are existing regular files outside
  the repository; links and repository-contained paths are rejected.
- Both tunnel endpoints are loopback-only. Wildcard binds, `GatewayPorts`,
  `-g`, additional forwards, remote commands, and shell execution are denied.
- `PermitRemoteOpen` limits the SSH destination to the Windows callback port.
- SSH output is drained and never persisted; authorization codes, tokens,
  client secrets, and account identifiers are never logged or evidenced.

## Execution and failure semantics

The explicit command creates one listener and one SSH process, prints the
authorization URL for the operator to open on the Mac, accepts one callback,
performs one token exchange on Windows, and tears down the listener and SSH
process in every exit path. A tunnel failure, unexpected callback, timeout,
host-key mismatch, path-policy failure, or token-exchange failure stops the
flow without retry or fallback. No Gmail service is constructed and no
`users.messages.send` operation is reachable from this command.

## Evidence and tests

Offline tests cover canonical external paths, port bounds, fixed host/account,
strict SSH options, loopback-only forwarding, forbidden wildcard/remote
command flags, exact `gmail.send` scope, and the absence of message operations.
The contract and evidence record zero Google requests, zero OAuth executions,
zero token exchanges, and zero emails until a separate Human Gate is consumed.
