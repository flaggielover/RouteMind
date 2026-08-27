# Round 4 External Infrastructure Evidence Freeze

## Decision

The external infrastructure diagnostic lane is frozen as of 2026-08-27. No new
Vultr Tokyo VKE, VM, or SSH paid diagnostic attempt is designed, authorized, or
executed by this checkpoint.

Exact retained states:

```text
R4-405 = LOCAL_AND_CI_VALIDATED / TARGET_PENDING / NO_TARGET_CLAIM
R4-406 = LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING / NO_TARGET_CLAIM
EXTERNAL_VKE_VALIDATION = INCONCLUSIVE
TOKYO_VM_EXTERNAL_VALIDATION = INCONCLUSIVE
SSH readiness = TCP22_OK / SSH_BANNER_NOT_RECEIVED / ROOT_CAUSE_UNKNOWN
```

## Evidence preservation

All VKE v1/v2/v3, Tokyo VM v1/v2, VPC-quota, SSH-readiness, cost, teardown,
404, zero-label, and leakage evidence remains unchanged and addressable through
the existing R4-405/R4-406 evidence lists. This freeze does not remove, overwrite,
reinterpret, or promote any historical outcome.

The cumulative conservative external cost remains USD 11.256. Teardown remains
complete, retained execution-label resources remain zero, and the last leakage
scan remains zero findings. Those facts are historical evidence, not target
telemetry, DR, VKE, production, or root-cause claims.

## Reopening condition

No automatic v2/v3/v4 retry is allowed. The lane may reopen only after a human
provides a new proposal with clearly higher information gain and approves a new
exact contract, new SHA-256, resource/network boundary, budget, and teardown.
No such proposal or approval exists at this checkpoint.

R3-325 remains unchanged at
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
