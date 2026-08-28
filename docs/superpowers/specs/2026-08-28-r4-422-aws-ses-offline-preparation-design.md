# R4-422 AWS SES Offline Preparation Design

## Scope

This change prepares, but does not execute, a bounded AWS SES validation. The
existing provider-boundary contract remains immutable at
`contracts/product/r4-422-notification-human-gate-v1.json` and its SHA-256
`0cc9bcf99a11e3a4f948693e818c1c497ea7e0e3314ce15cd76f0a973eda4ffb`.

## Authentication and configuration

The business service exposes non-secret SES settings under
`routemind.notification.ses`: `enabled`, `profile`, `region`, `sender`, and
`synthetic-recipient`. Profile selection uses an explicit non-secret property
or `AWS_PROFILE`; the expected external profile is `routemind-ses`. AWS SDK for
Java v2 `DefaultCredentialsProvider` is the only credential-chain integration.
RouteMind never parses shared credential files and never resolves credentials
during offline readiness checks. SES client creation is not a Spring send bean
and is disabled unless configuration explicitly enables it.

Readiness is intentionally configuration-only and returns `AVAILABLE`,
`MISSING`, or `INVALID_CONFIGURATION`. It does not prove AWS identity,
permission, SES connectivity, sender verification, or delivery.

## Runtime boundary

The existing Java-owned transactional Outbox, consent rechecks, idempotency,
bounded retry, DLQ, authenticated receipt semantics, privacy policy, and local
mock provider remain unchanged. A future adapter may use the factory at the
provider boundary, but no send operation is wired or invoked in this change.

## Future execution contract

A new independent contract is prepared at
`contracts/provider/r4-422-aws-ses-live-validation-v1.json`. It is limited to
synthetic notifications in `ap-northeast-1`, at most 10 messages, 30 minutes,
and a conservative USD 1.00 cap. It forbids account/resource/IAM changes,
production-access requests, production recipients, and credential values in
Git, logs, evidence, or chat. Provider acceptance, delivery/bounce receipts,
idempotency, retry, fallback provenance, cost, and leakage evidence are
required. The contract is not executed by this change and requires a distinct
Human Gate approval containing its exact digest.
