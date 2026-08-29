# R4-422 AWS SES second single-send execution closure

Date: 2026-08-29

## Contract binding

- Contract: `contracts/provider/r4-422-aws-ses-second-single-send-validation-v1.json`
- Canonical SHA-256: `9c32cc9df3ac34e2a85f722ec2bcce6c64e9e5057a2f9e85e0e14656c082feaa`
- Approval: exact digest approved by the operator before execution
- Provider/region: `AWS_SES` / `ap-northeast-1`

## Result

- Final classification: `FAIL_PROVIDER_REJECTED`
- Provider response class: `SesException`
- Normalized provider error: `AccessDenied`
- AWS `SendEmail` requests dispatched: `1`
- Messages/recipients consumed: `1 / 1`
- Automatic retries: `0`
- Emails sent or delivery confirmed: `0 / 0`
- AWS account, IAM, SES configuration, or resource mutations: `0`
- Execution window: `2026-08-29T04:18:01Z` to `2026-08-29T04:18:06Z` (5 seconds)
- Observed cost: `USD 0.00`; conservative contract bound: `USD 0.10`; billing readback was not performed

The local `DefaultCredentialsProvider` resolved before the request and the SES
client was constructed successfully. The single authorized request was rejected
by AWS SES with normalized `AccessDenied` semantics. The request was not retried,
no fallback was represented as AWS truth, and no message ID or authenticated
delivery receipt was returned. This is a provider-rejection result, not a
connectivity, delivery, or production-readiness claim.

The one-message budget is consumed. Any subsequent live attempt requires a new
independent contract and a new Human Gate; this contract must not be reused.

## Security and cleanup

- Sender, recipient, message body, credential values, and raw provider response:
  not persisted
- Leakage scan: `evidence/gates/R4-422/aws-ses-second-single-send-leakage-scan-20260829T041801Z.json`
- No shared credential-store mutation occurred
- No AWS resources were created, so no provider teardown action was required
- Redacted evidence is append-only

R4-422 remains externally incomplete as
`FAILED / PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`; provider acceptance and
delivery are not established.
