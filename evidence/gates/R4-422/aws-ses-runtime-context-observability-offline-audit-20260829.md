# R4-422 SES Runtime Context and Error Observability Offline Audit

Date: 2026-08-29

## Boundary and frozen result

- HEAD before work: `0bb5c32b` (`main == origin/main`)
- HEAD after work: the commit containing this evidence; resolve with `git rev-parse HEAD`
- External provider requests: `0`
- AWS network requests: `0`
- `SendEmail` / `SendRawEmail` requests: `0 / 0`
- AWS mutations: `0`
- Historical contract reused: `NO`
- Historical evidence modified: `NO`
- Frozen R4-422 result: `BLOCKED / FAILED_PROVIDER_REJECTED / NO_PRODUCTION_CLAIM`
- Frozen historical provider result: one request, zero retries, `SesException / AccessDenied`,
  no provider acceptance, MessageId, or delivery

The consumed contract and every historical execution, cost, and leakage artifact
remain append-only and unchanged.

## Request-construction audit

The historical one-shot helper used this path:

```text
process environment
-> nonblank-only precondition
-> raw sender in SendEmailRequest.source
-> raw recipient in Destination.toAddresses
-> SesClient.sendEmail
```

It did not pass sender or recipient through `NotificationSender`,
`NotificationRecipient`, `NotificationSesProperties`, or the product notification
boundary. The original values and full provider exception were not retained.

The hardened production path is:

```text
notification intent / template
-> NotificationRequest domain endpoints
-> bounded NotificationSesProperties equality checks
-> AwsSesRequestFactory
-> SendEmailRequest
-> AwsSesNotificationProvider
-> SesClient
```

The factory is shared by the offline audit and future provider execution. It
fails closed when the channel, sender, or recipient differs from the bounded
configuration. The real SES adapter remains disabled by default.

## Current runtime-context result

Classification:

```text
runtime_context = COMPARISON_INPUT_UNAVAILABLE
historical_context = HISTORICAL_CONTEXT_NOT_RECONSTRUCTABLE
runtime_mismatch_found = false
```

Current process sender observations:

```text
present=true
raw_equals_domain_normalized=true
trimmed_equals_domain_normalized=true
leading_or_trailing_whitespace=false
display_name_syntax=false
angle_bracket_syntax=false
unicode_normalization_difference=false
case_normalization_changes_value=false
exact_approved_value_comparison=COMPARISON_INPUT_UNAVAILABLE
```

Current process recipient observations are identical in structure: present,
raw and trimmed values equal the domain-normalized value, with no boundary
whitespace, display name, angle brackets, Unicode normalization difference, or
case-normalization change. Exact approved-value comparison is unavailable
because the consumed contract bound execution-time environment values without
persisting an independent approved value. No value or endpoint hash was emitted.

Current request shape from the production request builder:

```text
source_present=true
source_populated_exactly_once=true
recipient_count=1
to_count=1
cc_count=0
bcc_count=0
duplicate_recipients=false
reply_to_count=0
return_path_present=false
source_arn_present=false
return_path_arn_present=false
configuration_set_present=false
tag_count=0
delegated_authorization_fields_present=false
unexpected_optional_fields_present=false
endpoint_override_present=false
region_override_present=false
retry_behavior=AWS_SDK_RETRIES_DISABLED_APPLICATION_BOUNDED
```

`fromArn` is not an applicable field on the AWS SDK for Java v2 SES v1
`SendEmailRequest` model. No substitute field is populated.

## Root-cause disposition

Root cause remains `INCONCLUSIVE`. The current process does not exhibit the
whitespace, display-name, Unicode, case, cardinality, CC/BCC, delegated-field,
endpoint, region, or retry mismatch classes examined here. That weakens the
runtime-context mismatch hypothesis for the current configuration, but it does
not reconstruct or disprove a difference in the historical execution process.
No mismatch is proven and no historical cause claim is made.

## Sanitized provider-error observability

Future SES provider rejection observations retain only:

- provider and operation constants;
- configured region;
- safe exception class token;
- safe structured AWS service error code;
- HTTP status;
- request-ID status as `ABSENT` or `PRESENT_REDACTED`;
- normalized provider category and semantic;
- provider acceptance (`false` for errors);
- request and retry counts;
- fallback usage (`false` for AWS evidence);
- timestamp;
- non-content request-shape booleans and cardinalities.

Request IDs are treated as operational identifiers but are not persisted raw or
hashed in this checkpoint. Only presence is retained. Raw exception messages are
never read into the observation. Email addresses, subject, body, account IDs,
ARNs, access-key patterns, secrets, session tokens, authorization headers, raw
requests, and raw SDK payloads are excluded and covered by synthetic regression
tests.

The AWS SDK client retry strategy is explicitly `doNotRetry`; the existing
RouteMind worker remains the only bounded application retry authority.

## Verification

- Offline current-process context audit: `1 passed`
- Focused SES context/configuration/error tests: `16 passed`
- External HTTP/provider traffic during tests: `0`
- Credential resolution during context audit: `0`
- Broader Java suite: `136 passed, 0 failed` under JDK 17 with the repository
  Maven cache and no network access
- `scripts/verify.ps1`: `PASS`
- Control-plane validation: `PASS`
- Round 4 graph validation: `PASS`
- Security gate: `PASS`
- Standalone `scripts/validate_contracts.py`: not executable in the current
  local Python environment because `jsonschema` is not installed. This
  independent tooling prerequisite is not an SES runtime failure; no package was
  downloaded because this checkpoint prohibits external package traffic.
- Leakage scan: `evidence/gates/R4-422/aws-ses-runtime-context-observability-leakage-scan-20260829.json`

## Remaining evidence gaps and next decision

The historical raw sender/recipient representation, complete `SesException`,
HTTP status, provider request ID, and AWS authorization explanation remain
unrecoverable. No safer offline artifact can reconstruct them.

`ANOTHER_SENDEMAIL_CURRENTLY_JUSTIFIED = YES` for a future separately approved,
single-request diagnostic because the shared request path is now bounded and a
new provider rejection would retain materially more discriminating structured
metadata. This checkpoint does not create or execute that contract. A new exact
contract, digest, bounded budget, and explicit Human Gate remain mandatory.
