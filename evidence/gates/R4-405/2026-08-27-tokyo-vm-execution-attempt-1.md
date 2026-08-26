# Tokyo VM External Validation Attempt 1

## Classification

This is an immutable external-execution attempt record for the approved
platform-neutral contract. The attempt did not reach VM deployment or the
RouteMind workload. It is neither a target pass nor a root-cause claim.

```text
contract = r4-vultr-tokyo-vm-external-validation-v1
contract_sha256 = 2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a
execution_id = r4-vm-20260826t182938z-d3255b7d6c
region = nrt
```

## Preflight

- Authenticated provider account and Tokyo `nrt` region passed read-only checks.
- `vc2-8c-32gb`, `vc2-2c-4gb`, Ubuntu 24.04 x64, the configured provider SSH
  key identity, and the exact operator `/32` passed.
- Authenticated hourly quote was USD 0.219 for primary and USD 0.027 for
  recovery. The six-hour compute upper bound was USD 1.476, below the USD 3
  incremental contract ceiling.
- The exact Terraform plan contained only six creates: two instances, one VPC,
  one firewall group, and two firewall rules. All instance/VPC regions were
  `nrt`; no public application or OTLP port was present.

## Provider result

Terraform created the contract firewall group and its two exact rules, then the
provider rejected the VPC create with HTTP 400:

```text
Only 5 VPCs are permitted per location for this account.
```

No primary VM, recovery VM, or VPC was created. The created firewall identities
were execution-scoped and were not reused by any other run.

## Teardown and cleanup

- Terraform state contained exactly the execution firewall group and two rules.
- A destroy plan contained exactly three deletes; it applied successfully.
- The firewall group identity returned HTTP 404 after teardown.
- Credentialed provider list checks found zero resources matching the execution
  label across firewall groups, instances, and VPCs.
- No workload, telemetry backend, recovery package, or customer data ran.

## Cost and evidence boundary

No billable VM, storage, VPC, or load-balancer resource was created. The
conservative execution cost is USD 0.00; the approved USD 3 ceiling was not
approached. This record contains no secret values and is retained separately
from all VKE v1/v2/v3 evidence.

R4-405 and R4-406 remain `TARGET_PENDING`. The VKE lane remains frozen as
`EXTERNAL_VKE_VALIDATION = INCONCLUSIVE`, with `NO_TARGET_CLAIM` and
`NO_ROOT_CAUSE_CLAIM`. R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

The actionable external blocker is the provider account's VPC-per-location
quota. Existing VPCs were not modified or deleted. A future retry requires a
new explicit contract/approval or an approved topology that does not violate
the frozen resource and network boundaries.

## Repository closure

The evidence and task-graph update was committed as `e6e009f` and pushed to
`main`. GitHub Actions run `33000804025` passed all five required jobs. This CI
result validates repository controls only; it does not convert the quota-blocked
attempt into Tokyo target evidence.
