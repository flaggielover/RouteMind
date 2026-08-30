# R4-422 Gmail Refresh-If-Required Single-Send Preparation

Date: 2026-08-30

The independent contract
`contracts/provider/r4-422-google-gmail-refresh-if-required-single-send-v1.json`
is frozen at canonical SHA-256
`35702d6d6698b78f08757b2560deb2bfee50503d0b8cc90b8fd2fcdf9431535f`.

This checkpoint is preparation only. The Java bounded executor and offline
tests are present, but no credential store was loaded and no refresh, OAuth,
browser, SSH, Gmail API, or email operation was invoked. Preparation counters
are all zero: Gmail API requests `0`, `users.messages.send` requests `0`,
credential refresh requests `0`, email sends `0`, recipients `0`, retries `0`,
fallbacks `0`, reads `0`, and account/resource mutations `0`. Cost is
`USD 0.00`.

The later Human Gate is limited to one standard refresh only when readiness
requires it, followed by at most one `users.messages.send` request to one
synthetic recipient. The process uses one loaded credential object, reassesses
it after refresh, applies a fixed post-refresh token snapshot to the send
request, and stops on any refresh or send failure. New OAuth sessions,
authorization-code exchanges, browser/SSH paths, reads, attachments, CC/BCC,
batch operations, retries, fallback, and Google/account/resource mutations are
forbidden. Historical Gmail contracts and evidence remain consumed, immutable,
and non-reusable.

The contract validator, self-tests, focused Java tests, security gate, and
leakage scan passed. No provider, delivery, or production claim is made.
