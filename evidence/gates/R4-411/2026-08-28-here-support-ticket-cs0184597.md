# R4-411 HERE Support Ticket Evidence

## Non-sensitive external evidence

This append-only record captures the owner-reported submission of a HERE
Support ticket. It contains no API key, credential, account identifier, request
payload, coordinate, screenshot, or provider response body.

- Ticket: `CS0184597`
- Title: `Japan access eligibility for HERE Matrix Routing API v8`
- Status at submission: `NEW`
- Ticket type: `Product Catalog`
- Support category: `Account Support`
- Organization access: HERE Support is permitted to inspect the current HERE
  Platform organization for the entitlement review.
- Requested determination: HERE Matrix Routing API v8 Japan-region access
  eligibility and any required entitlement.

## Conservative interpretation

Ticket submission is evidence that an entitlement inquiry was opened; it is not
an entitlement approval, a Japan eligibility confirmation, a live API result, or
a production/provider validation. Until HERE supplies an explicit answer,
`HERE_MATRIX_JAPAN = RESTRICTED / REQUIRES_HERE_CONFIRMATION` and
`JAPAN_SERVICE_ELIGIBILITY = PARTIAL_PENDING_CONFIRMATION` remain unchanged.
`HERE_ROUTING_JAPAN = DOCUMENTED_SUPPORTED` remains limited to the separately
documented point-routing capability and cannot be transferred to Matrix access.

R4-411 therefore remains `BLOCKED / HUMAN_GATE_PENDING` at frozen contract
SHA-256
`4eacaad0c0d8a71a73715b750b370d58a4439d70b1f9dd1cc97d119599da6d1c`. No HERE
live call, key test, account mutation, paid request, or contract mutation was
performed for this record.
