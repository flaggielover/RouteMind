# R4-422 SES IAM Authorization Semantics Differential Audit

Date: 2026-08-29
Scope: read-only AWS Console inspection, official documentation review, and
offline policy-context reasoning. No AWS API, CLI, STS, IAM, SES, or SendEmail
request was made by this audit.

## Frozen boundary

- R4-422 remains `BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`.
- The third approved single-send contract and its `AccessDenied` / HTTP 403
  result are historical, append-only evidence and were not changed.
- External SendEmail requests in this audit: `0`.
- AWS mutations in this audit: `0`.
- R3-325 remains `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Verdict

`AUTHORIZATION_MODEL_VALID_NO_STATIC_CAUSE_FOUND` (confidence: medium).
The current policy and request shape are consistent with the documented SES/IAM
model. The evidence narrows the discrepancy to an unobserved service-side or
request-context authorization difference, but no documented rule directly
explains this specific 403. `FOURTH_SENDEMAIL_CURRENTLY_JUSTIFIED = NO`.

## Phase A: policy audit

The authenticated IAM Console showed one customer inline policy attached to the
intended IAM user. Sensitive account, ARN, and address values were not retained.
Its semantic shape is:

```text
Effect: Allow
Action: ses:SendEmail, ses:SendRawEmail
Resource: one exact SES identity ARN in ap-northeast-1, same account as the user
Condition:
  StringEquals ses:FromAddress = the verified configured sender (scalar)
  ForAllValues:StringEquals ses:Recipients = one verified synthetic recipient (set)
  Bool aws:SecureTransport = true
Permissions boundary: not configured (Console observation)
```

The policy is an identity-based IAM policy. It is not an SES identity sending-
authorization policy and does not grant a delegate principal.

The AWS Service Authorization Reference lists `ses:SendEmail` as granting the
permission to send email, with the `identity*` resource type required, and lists
`ses:FromAddress` and `ses:Recipients` as supported service condition keys. This
supports exact identity-resource matching for this action; it does not prove
that the service accepted the particular historical request.

## Phase B: condition semantics

- `ses:FromAddress` is a String condition key filtering the message From address.
  IAM `StringEquals` is exact and case-sensitive. The RouteMind SDK request sets
  `Source` from the bounded sender address; no display name, angle brackets,
  whitespace, or Unicode normalization difference was found in the existing
  offline audit.
- `ses:Recipients` is an `ArrayOfString` condition key covering To, CC, and BCC
  recipients. The RouteMind request has one To recipient and zero CC/BCC. The
  documented key does not include Return-Path or Reply-To.
- `ForAllValues:StringEquals` requires every value in the request context set to
  match one of the policy values. It is case-sensitive. AWS IAM documents that a
  missing or empty set is vacuously true for `ForAllValues`; a separate `Null`
  check is required when presence itself must be mandatory. SES `SendEmail`
  independently requires at least one recipient.
- A missing ordinary condition key makes that condition false unless an
  `...IfExists` operator is used. The policy uses neither `IfExists` nor `Null`.
- `aws:SecureTransport=true` is an SES-supported global key in the SES policy
  anatomy documentation. The SDK client uses the normal HTTPS endpoint with no
  endpoint override.

The current request fields therefore have semantic equivalence to the simulator
inputs recorded in the prior operator evidence, subject to the simulator not
being able to prove the service's actual derived context.

## Phase C: resource semantics

`EXACT_IDENTITY_RESOURCE_SUPPORTED_FOR_THIS_REQUEST = YES` according to the
Service Authorization Reference: `SendEmail` includes the required `identity*`
resource type. SES documentation also describes an identity ARN as the resource
for authorization policies. No evidence supports replacing the exact resource
with `*`; doing so would weaken least privilege and is not proposed.

SES evaluates recipient addresses through the `ses:Recipients` condition context,
not as separate recipient resources. Sandbox verification is a service-side
constraint on destinations, not a substitute for IAM authorization.

## Phase D: delegated sending

`DELEGATED_SENDING_AUTH_REQUIRED = NO` for the observed same-account model.
The SendEmail API reference states that `SourceArn` is used only when sending on
behalf of another identity owner. The RouteMind request intentionally has no
`SourceArn`, `FromArn`, or `ReturnPathArn`, and the sender has no sending-
authorization policy. Adding those fields would switch authorization models and
is not justified.

## Phase E: Policy Simulator limitation

The IAM Policy Simulator evaluates the policies and context values supplied to
the simulation and returns a binary IAM authorization result. AWS explicitly
warns that simulator results can differ from the live environment; the simulator
does not make an actual service request, does not return a service response, and
does not reproduce all service-side checks. Thus `EXPLICIT ALLOW` and a real SES
HTTP 403 can coexist without contradiction: the former proves only the modeled
IAM policy/context evaluation, while the latter reflects SES's complete request
processing path.

The simulator also relies on caller-supplied values for most condition keys. It
cannot verify that SES derived exactly the same From/recipient context from the
SDK request, nor can it establish identity verification, sandbox/account state,
provider-side enforcement, or an unobserved resource/policy layer beyond the
simulation inputs.

## Phase F: Console findings

Read-only authenticated Console observations, with identifiers redacted:

- IAM user permissions page: one customer inline policy named
  `RouteMindSesBoundedSend`; permissions boundary shown as not configured.
- IAM policy editor: the semantic policy above, with no additional statements.
- SES Tokyo account dashboard: region `ap-northeast-1` (Tokyo), account healthy,
  sandbox status, daily quota 200 and max rate 1/s.
- SES Tokyo identities page: two email identities, each shown as `Verified`.

These observations weaken generic missing-credential, wrong-region, unverified-
identity, and obvious sandbox-recipient explanations, but do not expose the
service's hidden authorization decision path.

## Phase G: RouteMind request-context mapping

| RouteMind semantic | AWS SDK / SES field | IAM effect | Observed shape | Simulator equivalence |
| --- | --- | --- | --- | --- |
| bounded sender | `SendEmailRequest.source` / `Source` | `ses:FromAddress`, identity resource | one verified address, scalar | supplied exact scalar |
| bounded synthetic recipient | `Destination.toAddresses` / `Destination.ToAddresses` | `ses:Recipients` | one-element set; CC/BCC empty | supplied one value |
| no delegation | no `SourceArn`/`FromArn`/`ReturnPathArn` | same-account identity model | absent | no delegated input |
| transport | AWS SDK HTTPS endpoint | `aws:SecureTransport` | true | supplied true |
| endpoint/region | `SesClient` region `ap-northeast-1` | resource region and service endpoint | no override | selected Tokyo region |
| retry/fallback | client retry strategy and provider | not an IAM key | retries 0, fallback false | outside simulator |

The factory also omits configuration set, tags, Reply-To, Return-Path, and all
other optional authorization-affecting fields. Historical evidence retained only
sanitized error metadata, so raw provider context cannot be reconstructed.

## Strongest explanation and competitors

Strongest explanation: the simulator proved the exact modeled IAM statement, while
real SES applied a service-side or request-context check not represented in the
simulation. The current evidence cannot identify whether the hidden difference is
context derivation, an SES authorization layer, or another account/service rule.

Competing explanations, all unconfirmed:

1. SES derived a From/recipient/resource value different from the values supplied
   to the simulator (for example an undocumented normalization or identity
   association detail).
2. An SES-side authorization or account control was evaluated outside the
   simulator; current Console observations rule out only the obvious checks.
3. A stale or incomplete simulator input/policy snapshot differed from the
   policy used by the real request; no local evidence proves this.
4. Historical provider evidence is insufficient to distinguish the above because
   the raw exception message and full authorization context were intentionally
   sanitized and not retained.

No adapter defect or static policy defect is demonstrated. The offline model
tests are analytical aids only and make no provider claim.

## Minimal fix and next decision

No AWS-side or RouteMind production fix is justified by the available evidence.
Do not broaden `Resource`, remove conditions, add delegation fields, or mutate
IAM/SES. The safe next step is to preserve this inconclusive classification and
obtain a new, separately approved diagnostic only if a concrete, read-only
provider-side evidence source becomes available. Under the current evidence,
another SendEmail is not justified.

## Official sources

- [Actions, resources, and condition keys for Amazon SES](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ses.html)
- [Amazon SES policy anatomy](https://docs.aws.amazon.com/ses/latest/dg/policy-anatomy.html)
- [Overview of Amazon SES sending authorization](https://docs.aws.amazon.com/ses/latest/dg/sending-authorization-overview.html)
- [SendEmail API Reference](https://docs.aws.amazon.com/ses/latest/APIReference/API_SendEmail.html)
- [IAM policy testing with the IAM policy simulator](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html)
- [IAM JSON policy elements: Condition operators](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition_operators.html)

## Offline regression evidence

`python -m unittest scripts/ses_iam_policy_differential_model_test.py` passed
7 tests. The tests cover exact identity/context matching, missing context,
additional recipients, case/whitespace, ForAllValues versus ForAnyValue,
vacuous ForAllValues semantics, wildcard-resource non-equivalence, and scalar /
multivalue shape. They are not a substitute for a live SES authorization result.

Security/leakage scan: PASS. No secret, account identifier, full ARN, address,
message body, request ID, or credential identifier is stored in this artifact.
