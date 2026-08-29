# R4-422 AWS SES third single-send execution closure

Date: 2026-08-29

## Contract binding

- Contract: `contracts/provider/r4-422-aws-ses-third-single-send-diagnostic-v1.json`
- Canonical SHA-256: `6c52a2457b4d136f17d11e66af15cf9a1a79a721bc8558cca68658f728ed4387`
- Exact Human Gate approval was recorded before execution.
- Provider/region: `AWS_SES` / `ap-northeast-1`

## Result

- Final classification: `FAIL_PROVIDER_REJECTED`
- Provider response class: `SesException`
- Normalized provider error: `AccessDenied`
- HTTP status: `403`
- Request ID: present, redacted
- AWS `SendEmail` requests dispatched: `1`
- Messages/recipients consumed: `1 / 1`
- Automatic retries: `0`
- Fallback: `false`
- Emails sent or delivery confirmed: `0 / 0`
- AWS account, IAM, SES configuration, or resource mutations: `0`
- Execution window: `2026-08-29T07:16:42Z` to `2026-08-29T07:16:45Z` (3.081 seconds)
- Observed cost: `USD 0.00`; conservative contract bound: `USD 0.10`; billing readback was not performed

The local `DefaultCredentialsProvider` resolved before the request, the SES
client was constructed successfully, and the bounded request shape was audited
before dispatch. The single authorized request was rejected by AWS SES with
normalized authorization-rejected semantics. It was not retried, no fallback
was used, no message ID or authenticated delivery receipt was returned, and no
production or delivery claim is made.

The one-request budget is consumed. Any subsequent live attempt requires a new
independent contract and a new Human Gate; this contract and prior contracts
must not be reused.

## Security and cleanup

- Sender, recipient, message body, credential values, credential identifiers,
  account/identity identifiers, and raw provider response: not persisted
- Leakage scan: `evidence/gates/R4-422/aws-ses-third-single-send-leakage-scan-20260829T071645Z.json`
- No shared credential-store mutation occurred
- No AWS resources were created, so no provider teardown action was required
- Evidence is redacted and append-only; historical first/second contract
  evidence is unchanged

R4-422 remains externally incomplete as
`FAILED / PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`.
