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
