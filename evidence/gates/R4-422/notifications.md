# R4-422 Notification Provider Human Gate Preparation

## Gate classification

R4-422 remains `BLOCKED / PREPARED_NOTIFICATION_PROVIDER_HUMAN_GATE`. R4-420
already freezes notification intent, consent, quiet-hours, retry, bounce, and
delivery-truth semantics. This preparation chooses no provider or recipient,
creates no account/resource, configures no credential, and sends no message.

Canonical preparation contract:

```text
contract = contracts/product/r4-422-notification-human-gate-v1.json
sha256 = 0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb
recommended_candidate = AWS_SES_EMAIL_AP_NORTHEAST_1
selected_provider = UNAPPROVED
selected_channel = UNAPPROVED
real_send_authorized = false
maximum_real_send_spend_if_separately_authorized = USD 1
```

## Original Evidence Contract audit

- Java and PostgreSQL retain durable notification intent and delivery state.
  Intent belongs in the same transaction/Outbox as its business trigger;
  delivery is asynchronous and idempotent.
- Consent is rechecked before every attempt and after quiet-hours deferral.
  Retry count is bounded at five. Duplicates, bounce, terminal failure,
  cancellation, opt-out, and unauthenticated callback behavior remain explicit.
- Provider acceptance is not delivery. `DELIVERED` requires an authenticated
  provider delivery receipt; no intent, queue write, HTTP acceptance, or local
  fixture may be substituted.
- The first external candidate is email only. SMS and push remain deferred.
  AWS documents an SES endpoint in `ap-northeast-1` and delivery, bounce, and
  complaint event publishing; this is capability evidence, not a live result.
- RouteMind exposes no public inbound callback in this contract. A future exact
  execution contract must approve an authenticated event topology and any AWS
  resources before creation.

Sources inspected 2026-08-27:

- <https://docs.aws.amazon.com/general/latest/gr/ses.html>
- <https://aws.amazon.com/ses/pricing/>
- <https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html>
- <https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html>

## Secret, sender, and recipient boundary

Only secret/configuration names are committed:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` (optional for the approved credential mechanism)
- `ROUTEMIND_NOTIFICATION_SENDER`
- `ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT`

Values remain outside Git, logs, evidence, screenshots, and chat. The recipient
must be synthetic and owner-approved; production recipients are prohibited.
Evidence may retain only a redacted digest. The reviewed template must contain no
personal or production content.

## Bounded future evidence

A later execution contract, with a new digest and Human Gate, is required before
adapter activation or real send. It is bounded to 30 minutes, ten messages, and
USD 1. The evidence contract covers transactional intent/Outbox identity,
consent, quiet hours, opt-out, duplicate/idempotency, retry exhaustion, provider
acceptance versus delivery, authenticated delivery/bounce events, tenant scope,
provider identity/region, cost, leakage, timestamps, versions, and digests.

## R4-422 Human Gate

Minimum human action:

```text
I approve R4-422 contract SHA-256 0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb, ratify AWS SES email in ap-northeast-1 as the RouteMind candidate notification provider/channel, and approve the external AWS account owner, verified sender, synthetic recipient, and authenticated event-topology design. This approval freezes the provider boundary only and does not authorize account/resource creation or a real send.
```

The named secrets and sender/recipient values must then be configured through a
secure external mechanism. Real sends remain prohibited until a new exact
execution contract states any resources, recipient digest, callback topology,
message count, cost, cleanup, and separate approval.

## Provider-neutral local preparation audit - 2026-08-28

The frozen contract's local boundary is already represented by executable
repository evidence: Java remains the durable owner; PostgreSQL migrations and
repositories retain business/outbox/inbox identity; RabbitMQ publication uses
bounded retry; Inbox processing deduplicates by event identity and routes poison
messages to a bounded dead-letter state. The frozen R4-420 product contract
supplies notification intent, consent, quiet-hours, opt-out, tenant/principal,
template-locale, lifecycle, authenticated-receipt, and privacy semantics.

The zero-send R4-422 preparation contract provides the provider-neutral seam for
a future sender adapter: an asynchronous idempotent worker, consent recheck
before every attempt, maximum five attempts, explicit retry/DLQ outcomes,
provider acceptance distinct from delivery, authenticated delivery and bounce
receipts, bounded timeout/rate/cost policy, synthetic recipient and sender
injection, redacted recipient digests, and telemetry exclusion of recipient,
sender, body, credentials, and provider message IDs. The real adapter remains
disabled by default.

Local gates validate the frozen contract and mutation boundaries; they do not
prove AWS account ownership, sender verification, recipient ownership, callback
authentication in AWS, delivery, bounce, cost, or any real send. Those facts
remain the independent Human Gate and later execution contract boundary. The
contract JSON and canonical SHA-256 are unchanged.

## Provider-neutral local implementation checkpoint - 2026-08-28

The Java-only zero-send seam is now executable and covered by focused unit
tests in `services/business-api/src/test/java/com/routemind/business/application/notification/NotificationDeliveryTests.java`.
The implementation deliberately has no Spring bean, AWS SDK, network client,
credential reader, or provider side effect:

- `NotificationCommand`, `NotificationRequest`, and `NotificationResult` carry
  tenant, correlation, trace, idempotency, attempt, and provenance metadata.
- `NotificationTemplateRenderer` only renders declared variables from the
  privacy allowlist and attaches the required
  `EXTERNAL_NOTIFICATION_DATA_MINIMIZATION` marker.
- `NotificationOutbox` emits a transaction-ready `notification.requested`
  event containing endpoint digests, never recipient/sender addresses or
  rendered content.
- `NotificationDeliveryWorker` rechecks consent for every attempt, bounds
  retries at five, separates provider acceptance from authenticated delivery,
  and preserves the original idempotency owner when a duplicate is in flight.
- `InMemoryNotificationDeliveryLedger` and `MockNotificationProvider` provide
  deterministic local idempotency, DLQ, retry, timeout, rate-limit, malformed,
  client, and server failure paths.

The seven focused tests verify template/privacy rejection, redacted audit and
Outbox payloads, authenticated-receipt requirements, retry-to-delivery,
retry-exhaustion-to-DLQ, duplicate suppression, consent/quiet-hours behavior,
and every offline mock outcome. They are local evidence only: no AWS account,
sender, recipient, callback, credential, delivery, bounce, cost, or production
claim is established by this checkpoint.

## AWS SES offline preparation checkpoint - 2026-08-28

The Java notification boundary now includes non-secret SES configuration under
`routemind.notification.ses`. `AWS_PROFILE` (or an explicit profile property)
selects the AWS SDK for Java v2 standard `DefaultCredentialsProvider` chain;
RouteMind does not parse shared credential files or resolve credentials during
offline readiness checks. The SES client factory is not a sender bean and the
configuration default is disabled. Readiness returns only `AVAILABLE`,
`MISSING`, or `INVALID_CONFIGURATION`.

The independent future execution contract is
`contracts/provider/r4-422-aws-ses-live-validation-v1.json` with SHA-256
`e6576212ff580f57231ceb83ca95363fb4fd8b42053e85461b6dcd0b1d41b3ca`. It binds
to the frozen provider contract without modifying it, limits synthetic email
validation to `ap-northeast-1`, ten messages, thirty minutes, and USD 1.00,
and forbids account/IAM/resource mutation, production access, and secret or
recipient leakage. It is not authorized or executed; no AWS network request
was made. Evidence path: this file plus the contract and design record at
`docs/superpowers/specs/2026-08-28-r4-422-aws-ses-offline-preparation-design.md`.

## Verification checkpoint - 2026-08-28

- `NotificationSesConfigurationTests`: 4 passed, 0 failed under JDK 17
- Business API full Maven suite: 124 passed, 0 failed under JDK 17
- `r4_independent_human_gates_test.py`: 21 passed, 0 failed
- Contract, control-plane, security, scientific, and external-boundary gates
  reached `PASS` before the repository Compose check.
- The local Docker client did not return from `docker compose config --quiet`;
  no container or network mutation occurred. Compose validation remains a CI
  responsibility and is required before this checkpoint is considered fully
  CI-closed.

No AWS network request, credential resolution, account/resource mutation, or
email send occurred during verification.

## SES runtime-context and sanitized error-observability checkpoint - 2026-08-29

The historical one-shot helper read raw process environment endpoint values and
placed them directly into `SendEmailRequest`; it bypassed the domain endpoint
normalization used by product notification code. The historical values and full
exception are not retained, so that execution cannot be reconstructed.

The production SES boundary now has one shared request factory used by both the
offline auditor and future provider execution. It requires the EMAIL channel,
exact bounded configured sender and recipient, one To recipient, and no CC/BCC
or delegated optional fields. The SDK retry strategy is explicitly no-retry;
RouteMind's existing worker remains the bounded retry authority. The adapter is
still disabled by default.

The current process values contain no structural whitespace, display-name,
Unicode-normalization, case-normalization, cardinality, or optional-field anomaly.
An independent approved comparator and the historical raw values are unavailable,
so root cause remains inconclusive. Future AWS failures retain structured safe
fields only; raw exception text, endpoints, content, ARNs, account IDs, credentials,
headers, and request payloads are excluded. Full evidence is
`aws-ses-runtime-context-observability-offline-audit-20260829.md`. No AWS request,
mutation, contract creation, or historical evidence change occurred.
