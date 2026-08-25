# RouteMind Round 4 Control Contract

## Authority and state

`TASK_GRAPH.yaml` is the executable task authority. The Round 4 graph preserves
the dependency, workstream, gate, classification, acceptance, evidence, and
Round 3 lineage contract. Both representations must agree while Round 4 is
active.

Tasks move through `pending`, `ready`, `in_progress`, `implemented`,
`validating`, and `passed`. `blocked`, `failed`, and `deferred_external` retain
non-success outcomes. A dependency is satisfied only by `passed`; conditional
or optional work may instead receive a terminal, explicitly reconciled
disposition before R4-499.

## Evidence scopes

- Local tests support `LOCAL_VALIDATED` only.
- Clean GitHub Actions support `CI_VALIDATED` only.
- A deployment candidate requires the R4-401 target contract and all applicable
  security, recovery, load, and rollback evidence.
- `EXTERNALLY_VALIDATED` requires the task's matching live evidence.
- No Compose, fixture, synthetic, or demo result is production verification.

Human approval and external evidence are independent gates. The general Round 4
authorization does not supply provider credentials, approve paid campaigns,
select production data residency, authorize real notification recipients, or
approve an unblinding/resource gate unless a task records that specific scope.

## Safety boundaries

- Java and PostgreSQL retain durable business and authorization authority.
- Python retains optimization, simulation, research, and bounded experiment
  orchestration authority.
- Redis remains rebuildable hot state and RabbitMQ remains the reliable event
  backbone.
- Analytical agents are advisory and cannot become dispatch authority.
- Large artifacts remain under `ROUTEMIND_DATA_ROOT` and Git stores compact
  manifests, hashes, reports, and reproducibility metadata.
- Frozen Round 3 manifests, thresholds, negative results, and claim statuses are
  read-only scientific inputs.

## Completion rule

A task passes only after its acceptance criteria, scoped tests, evidence record,
and required real CI or external gate pass. R4-499 must reconcile every lane,
produce the final closure/evidence/demo/reproducibility package, keep limitations
explicit, and verify a clean tracked worktree with `main == origin/main`.
