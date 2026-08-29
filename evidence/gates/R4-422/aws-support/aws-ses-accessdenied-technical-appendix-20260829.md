# AWS SES AccessDenied Technical Appendix (Sanitized)

Date: 2026-08-29
Internal tracking: R4-422
Repository revision: `702a1e7`

## Scope and safety

This package is documentation/evidence preparation only. During preparation:

- AWS API/CLI/STS/IAM/SES calls: `0`;
- `SendEmail`/`SendRawEmail` requests: `0`;
- AWS mutations: `0`;
- credentials, account identifiers, identity values, addresses, cookies, and
  message content: not retained.

R4-422 remains `BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`.
R3-325 remains frozen as `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Timeline

| Attempt | UTC window | Operation | Result | Interpretation |
| --- | --- | --- | --- | --- |
| 1 | 2026-08-29T02:54:03Z to 02:54:08Z; correction run 02:55:50Z to 02:55:55Z | Local SDK/client construction helper | `NoClassDefFoundError` / client-path failure; AWS requests 0 | Local diagnostic-launcher classpath issue, not an AWS failure; Maven production dependency graph was not defective |
| 2 | 2026-08-29T04:18:01Z to 04:18:06Z | AWS SES `SendEmail` | One request, `SesException / AccessDenied`; HTTP status not retained then; no email | Real provider rejection; diagnostic retention was insufficient |
| 3 | 2026-08-29T07:16:42Z to 07:16:45Z | AWS SES `SendEmail` via hardened production path | One request, `SesException / AccessDenied`, HTTP 403, request-ID presence retained but ID redacted; retries 0, fallback false | Real provider authorization rejection with sanitized observability |

Attempt 1 is deliberately not classified as an AWS failure. Attempt 2 and
Attempt 3 are independent provider attempts and are not merged.

## IAM policy semantics

The intended validation principal is a console-disabled IAM user used only for
bounded SES validation. The configured profile was independently confirmed to
resolve to that principal; Access Advisor showed SES access on the relevant day.

The current inline policy, with all sensitive values redacted, is:

```text
Effect: Allow
Action: ses:SendEmail, ses:SendRawEmail
Resource: exact verified SES identity ARN in ap-northeast-1 (redacted)
Condition:
  StringEquals ses:FromAddress = [VERIFIED_SENDER]
  ForAllValues:StringEquals ses:Recipients = [VERIFIED_SYNTHETIC_RECIPIENT]
  Bool aws:SecureTransport = true
```

There are no IAM groups, no permissions boundary, and no known organization
SCP. The policy is identity-based. It is not a delegated SES sending-
authorization policy.

## Policy Simulator evidence and limitation

The simulator input selected `ses:SendEmail`, the exact sender identity
resource, the expected `ses:FromAddress`, the expected `ses:Recipients`, and
`aws:SecureTransport=true`. The result was `ALLOWED / EXPLICIT ALLOW`.

IAM documentation states that the simulator evaluates the policies and context
values supplied to it, returns a binary IAM result, does not make an actual AWS
service request, and returns no service response. AWS also warns that simulator
results can differ from the live environment. Therefore the simulator result
does not establish SES service acceptance, identity verification, sandbox
eligibility, or every service-side authorization check.

## SES Console evidence

Read-only authenticated Console observations for `ap-northeast-1`:

- account status: sandbox, health normal;
- daily sending quota and maximum rate: normal for the bounded diagnostic;
- sender identity: verified;
- synthetic recipient identity: verified;
- sending-authorization policy on sender: none;
- account suppression list: enabled and empty;
- configuration sets relevant to this request: zero;
- sending pause or reputation/enforcement block: not observed;
- AWS Organizations membership: none observed, therefore no organization SCP;
- IAM permissions boundary: not configured.

These observations weaken generic credential, region, verification, sandbox,
suppression, and visible account-pause explanations. They do not expose SES's
internal authorization decision.

## Request-shape and authorization mapping

The hardened `AwsSesRequestFactory` and provider produced:

- one `Source` sender and one `Destination.ToAddresses` recipient;
- CC/BCC, Reply-To, Return-Path, tags, configuration set, `SourceArn`,
  `FromArn`, and `ReturnPathArn`: absent;
- no duplicate, display-name, angle-bracket, whitespace, Unicode-normalization,
  or case-normalization anomaly in the offline audit;
- endpoint and region overrides: absent;
- AWS SDK retry policy: zero.

This is semantically equivalent to the simulator inputs for the fields that can
be supplied there. The exact context values as internally derived by SES are
not available. Same-account sending from an owned verified identity does not
require delegated sending fields; adding them would change the authorization
model.

## Authorization-semantics audit conclusion

AWS's Service Authorization Reference lists the required `identity*` resource
type for `ses:SendEmail` and supports `ses:FromAddress` and `ses:Recipients`.
`ses:Recipients` is an `ArrayOfString` covering To, CC, and BCC. IAM
`ForAllValues:StringEquals` requires every context value to match a policy
value; missing/empty sets are documented as vacuously true unless presence is
separately required with `Null:false`.

No documented rule directly explains this exact live HTTP 403 under the
observed policy and request shape. Classification:
`AUTHORIZATION_MODEL_VALID_NO_STATIC_CAUSE_FOUND`, confidence `MEDIUM`.

Strongest explanation: Policy Simulator evaluated the modeled IAM layer, while
SES applied an unobserved service-side or request-context authorization check.
Other candidates remain the exact SES-derived From/recipient/resource context,
an account/service rule not represented in the simulator, or an incomplete
simulator snapshot. None is confirmed.

## Evidence references

- Third attempt execution: `evidence/gates/R4-422/aws-ses-third-single-send-execution-20260829T071645Z.json`
- Third attempt closure: `evidence/gates/R4-422/aws-ses-third-single-send-execution-closure-20260829T071645Z.md`
- Second attempt execution: `evidence/gates/R4-422/aws-ses-second-single-send-execution-20260829T041801Z.json`
- Completed semantics audit: `evidence/gates/R4-422/aws-ses-iam-authorization-semantics-differential-audit-20260829.md`
- Offline model tests: `scripts/ses_iam_policy_differential_model_test.py`

The full request ID is not available: Attempt 3 retained only
`PRESENT_REDACTED` by policy. That policy may be revisited only for a future,
separately approved diagnostic if AWS Support confirms the minimum required
correlation fields. No new request will be sent merely to retry.

## Recommended support category

Conceptually: `Amazon SES -> Sending -> AccessDenied / Authorization / API
issue`. The exact console label and eligibility depend on the AWS Support plan;
this package does not initiate a support purchase or case.
