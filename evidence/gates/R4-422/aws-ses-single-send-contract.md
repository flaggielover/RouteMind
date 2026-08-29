# R4-422 AWS SES single synthetic send contract

Date: 2026-08-29

## Preparation status

- State: `PREPARED_AWS_SES_SINGLE_SEND_HUMAN_GATE`
- Contract: `contracts/provider/r4-422-aws-ses-single-send-validation-v1.json`
- Canonical semantic SHA-256: `e942a04b080da7cf42645d757fec61a1fb67428b59da29f90c93227b06c7d660`
- Provider: `AWS_SES`
- Region: `ap-northeast-1`
- Sender source: `ROUTEMIND_NOTIFICATION_SENDER` (value not persisted)
- Recipient source: `ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT` (value not persisted)

This is a new independent execution contract. The frozen provider-boundary
contract and the prior ten-message execution contract remain unchanged. The
new contract authorizes no action until a Human Gate approval matches its exact
canonical SHA-256.

## Bounds

- Exactly one synthetic `SendEmail` request and one synthetic recipient
- No CC, BCC, attachment, bulk send, or automatic retry
- Maximum duration: 15 minutes
- Conservative external spend ceiling: USD 0.10
- No account, IAM, SES configuration, or other AWS resource mutation
- No production recipient and no customer, courier, merchant, order, tenant,
  address, phone, or credential data

## Evidence and claims

Execution must retain redacted request/response metadata, timestamps, opaque
notification and Outbox identity, authenticated delivery or bounce outcome,
usage/cost accounting, artifact digests, and the leakage scan. Credential,
sender, recipient, message-body, and raw provider-token values are forbidden
from Git, logs, evidence, chat, and screenshots.

`PASS` requires bounded provider acceptance plus the required authenticated
delivery evidence. `PARTIAL` records acceptance without a complete delivery or
other required evidence item and makes no delivery claim. `FAIL` records
rejection, timeout, boundary violation, leakage risk, or untrustworthy
artifact. A local fallback may be recorded only with reason and provenance and
cannot be represented as AWS truth.

## Current execution facts

- AWS calls made while preparing this contract: `0`
- SES sends made while preparing this contract: `0`
- AWS account/IAM/resource mutations: `0`
- Contract state remains Human Gate pending; no live execution is authorized.
