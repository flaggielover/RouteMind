# R4-422 AWS SES second single-send contract

Date: 2026-08-29

## Preparation status

- State: `PREPARED_AWS_SES_SECOND_SINGLE_SEND_HUMAN_GATE`
- Contract: `contracts/provider/r4-422-aws-ses-second-single-send-validation-v1.json`
- Canonical semantic SHA-256: `9c32cc9df3ac34e2a85f722ec2bcce6c64e9e5057a2f9e85e0e14656c082feaa`
- Provider: `AWS_SES`
- Channel: `EMAIL`
- Region: `ap-northeast-1`
- Expected shared profile: `routemind-ses`
- Sender source: `ROUTEMIND_NOTIFICATION_SENDER` (value not persisted)
- Recipient source: `ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT` (value not persisted)

This is a new independent contract. The prior consumed single-send contract,
its digest, and its `FAIL_LOCAL_RUNTIME_DEPENDENCY_BEFORE_SEND` evidence remain
unchanged and are not reused. This contract authorizes no action until a Human
Gate approval matches its exact canonical SHA-256.

## Bounds

- Exactly one synthetic `SendEmail` request and one synthetic recipient
- Zero CC, BCC, attachments, bulk operations, and automatic retries
- Maximum duration: 15 minutes
- Conservative external spend ceiling: USD 0.10
- No account, IAM, SES configuration, or other AWS resource mutation
- Synthetic RouteMind template and opaque notification ID only
- No customer, courier, merchant, order, tenant, payment, address, phone,
  production-recipient, or arbitrary PII data

## Execution semantics

The future run must validate this exact digest before any AWS call, record
redacted request/response metadata and a MessageId digest if returned, stop
after the one request, and preserve all negative or partial outcomes. A failed
request is terminal for this contract. Acceptance without authenticated mailbox
delivery is `PARTIAL` and must not trigger another request. A local fallback may
be recorded only with explicit reason and provenance and can never represent
AWS truth.

## Preparation facts

- AWS calls made while preparing this contract: `0`
- SES sends made while preparing this contract: `0`
- AWS account/IAM/resource mutations: `0`
- Cost incurred: `USD 0.00`
- Local readiness inherited from the repaired runtime: provider `AVAILABLE`,
  `SesClient` construction `AVAILABLE`
- Contract state remains Human Gate pending; no live execution is authorized
