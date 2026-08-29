# R4-422 Cross-Device Gmail OAuth Bootstrap Preparation

Date: 2026-08-29

Status: `PREPARED_OFFLINE / HUMAN_GATE_REQUIRED / NO_SSH_TUNNEL / NO_OAUTH_EXECUTED / NO_EMAIL_SENT`

The prior loopback-only contract remains immutable and does not cover a second
host or an SSH remote forward. This checkpoint prepares a separate contract for
the Windows RouteMind host to initiate one strict SSH connection to the
operator Mac at `10.10.1.27` as user `suzhe`.

Windows binds the OAuth listener only to `127.0.0.1:<windows-port>`. The SSH
command requests exactly one remote forward,
`127.0.0.1:<mac-port>:127.0.0.1:<windows-port>`, so the Mac browser uses its own
loopback URL while callback bytes travel through the encrypted SSH channel to
Windows. The Windows process performs the only token exchange and persists
tokens only in the existing external Windows token store. No token file or
credential is sent to or persisted on the Mac.

The remote command requires external existing regular files for the SSH
identity and pinned `known_hosts`, canonicalized outside the repository.
`StrictHostKeyChecking=yes`, `CheckHostIP=yes`, `IdentitiesOnly=yes`,
`BatchMode=yes`, `ExitOnForwardFailure=yes`, and `PermitRemoteOpen` restricted
to the Windows loopback destination are mandatory. Wildcard binds,
`GatewayPorts`, `-g`, remote shell commands, additional forwards, and public
ingress are forbidden. SSH diagnostics are drained and not persisted.

The new contract is
`contracts/provider/r4-422-google-gmail-oauth-remote-forward-bootstrap-v1.json`
with canonical SHA-256
`2ef914d10c541f800a61107bc521f3edbfcec05b608b8dc52c6c65bcd102c629`.
It authorizes no action by itself and remains at a new Human Gate.

Offline tests cover path containment and link rejection, bounded Mac ports,
fixed host/user, strict SSH options, loopback-only forwarding, forbidden
wildcards/remote commands, exact `gmail.send` scope, and absence of Gmail
message operations. No SSH connection, OAuth consent, Google request, token
exchange, Gmail message request, email send, or resource mutation occurred.

Implementation commit `cd7336b9590838cacc33a75a3681d32dc9acf6ca` passed real
GitHub Actions run `33249022500`; all five required jobs were green.
