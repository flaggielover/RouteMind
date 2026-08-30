# R4-422 Gmail Refresh-If-Required Single-Send Execution

The approved contract
`contracts/provider/r4-422-google-gmail-refresh-if-required-single-send-v1.json`
was consumed exactly once at canonical SHA-256
`35702d6d6698b78f08757b2560deb2bfee50503d0b8cc90b8fd2fcdf9431535f`.

The existing repository-external credential loaded in a refresh-required state.
The same credential object was refreshed once, reassessed as usable, and used
for one Gmail API v1 `users.messages.send` request to the configured synthetic
recipient. Gmail returned sanitized provider acceptance with HTTP status `200`
and message-id presence; this does not confirm recipient delivery or production
readiness.

- Gmail API requests / `users.messages.send`: `1 / 1`
- Credential refresh requests: `1`
- Recipients / successful provider sends: `1 / 1`
- OAuth sessions / token exchanges: `0 / 0`
- Browser / SSH sessions: `0 / 0`
- Retries / fallback: `0 / 0`
- Reads / attachments / CC / BCC / batch: `0 / 0 / 0 / 0 / 0`
- Google resource / account mutations: `0 / 0`
- Elapsed time / observed cost: `5419 ms / USD 0.00`

No credential value, token, client secret, authorization header, raw response,
address, message content, or external path was recorded. The contract is
consumed and must not be retried or reused. Any future Gmail operation requires
a new independent contract and Human Gate. Historical Gmail/SES evidence and
the frozen R3-325 result remain unchanged.

Evidence JSON: `google-gmail-refresh-if-required-single-send-execution-20260830.json`.
Leakage scan: `google-gmail-refresh-if-required-single-send-execution-20260830-leakage-scan.json`.
