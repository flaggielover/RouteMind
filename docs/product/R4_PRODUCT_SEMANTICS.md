# R4 Product Preference and Notification Semantics

Contract identity: `r4-420-product-semantics-v1`

## Durable ownership

Java and PostgreSQL own preferences, consent, optimistic concurrency, audit, and
notification intent. The persistence identity is verified tenant, principal,
and namespace; a caller cannot select a different tenant, principal, or role.
Customer, courier, merchant, analyst, and operator principals may read and write
their own accessibility, locale, notification, and quiet-hour namespaces.
Cross-tenant access, cross-principal access, role impersonation, and an implicit
administrator override fail closed. A future support override needs a separate
versioned policy; it is not hidden in this contract.

Preference writes require an expected version and an idempotency key scoped by
tenant, principal, and operation. Notification intent is created through the
transactional Outbox in the same Java transaction as the durable trigger. A
delivery worker may update attempt/delivery state but cannot rewrite preference
or consent history. Python and LLM agents have no durable product authority.

## Defaults, consent, and time

The default locale and zone are `en-US` and `UTC`. The in-app channel is enabled;
email, SMS, and push fail closed until explicitly enabled. Consent is versioned
by tenant, principal, purpose, and channel, with `NOT_ASKED`, `GRANTED`,
`DENIED`, and `WITHDRAWN` states. Every external channel requires an explicit
grant, including transactional and security purposes. Consent is rechecked
before every provider attempt and after quiet-hour deferral.

Quiet hours use an IANA time zone and a start-inclusive/end-exclusive interval.
DST gaps advance to the first valid instant; overlaps choose the earlier offset.
Non-critical notifications wait until the next eligible instant. Only narrowly
defined critical security, on-call incident, and active-delivery failure cases
may bypass, and every bypass is audited. Marketing never bypasses quiet hours.

Locales use BCP 47 tags and every attempt records the actual template locale.
External delivery fails without a reviewed template. In-app delivery may use the
reviewed `en-US` fallback. This is a content fallback, not a claim that broad
localization has been tested.

## Accessibility baseline

All future preference and notification surfaces must remain keyboard complete,
keep visible focus, expose screen-reader names and status, avoid color-only
status, respect reduced motion, meet AA contrast, reflow responsively, associate
errors with controls, and announce live updates without stealing focus. System
theme, contrast, and reduced-motion settings are the defaults.

## Delivery truth

`INTENT_RECORDED`, `READY`, and `PROVIDER_ACCEPTED` are not delivery. Exactly one
state means delivered: `DELIVERED`. It is reachable only from
`PROVIDER_ACCEPTED` after an authenticated provider delivery receipt containing
provider, channel, provider message identity, and receipt time. Provider
acceptance is distinct from delivery. The in-app adapter must likewise return a
durable-visible-record acknowledgement before delivery is recorded.

Retries are idempotent and capped at five attempts. Consent withdrawal,
cancellation, bounce, retry exhaustion, missing templates, and terminal provider
failures remain explicit states rather than being relabeled as delivery.

## Scope boundary

This task freezes and locally validates semantics only. It does not create a
preference database, send a notification, select a provider, authorize a
recipient, supply credentials, approve spend, establish legal basis, or prove
production accessibility. R4-421 implements preferences; R4-422 remains behind
its external and human gates for real sends; AWS SES is retired as an active
provider after its preserved failed validation, and Google Gmail API is the
active email-provider candidate pending a new bounded Human Gate. R4-423 and
R4-424 complete the role surfaces and end-to-end product evidence. No Gmail
live or production claim exists yet.
