# RouteMind Round 4 Graph Audit

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `6f4dd92c3ed2ac79126aaca5b0466a353b6c693c`

Status: audited and promoted; Round 4 is `ACTIVE`

## Decision

The prepared 38-task graph is retained as the Round 4 execution design. It is
promoted into `TASK_GRAPH.yaml` without deleting tasks, flattening external
gates, or changing dependency intent. A separate closure classification makes
the final-program purpose visible while the original workstream and technical
classification remain authoritative.

The alternatives rejected by this audit were:

- regenerating a new graph from the final-closure prompt, which would discard
  reviewed task identities and Round 3 lineage;
- flattening blocked external tasks into documentation-only passes, which would
  manufacture completion; and
- activating every root task at once, which would violate human, external, and
  conditional gates.

Only R4-400 is active at promotion. After its evidence closes, the local
critical path selects R4-402 before high-priority local roots. R4-401 and
R4-410 remain explicit human/external gates; R4-437 remains conditional and is
not activated merely because its dependency passes.

## Inventory

- 38 tasks in six workstreams.
- 15 tasks require external evidence.
- 12 tasks require task-specific human approval.
- R4-437, R4-440, and R4-453 require recorded activation conditions.
- The critical spine begins at R4-400 and terminates at R4-499.
- R4-499 depends on all nine terminal evidence lanes named by the prepared graph.
- Dependency order is acyclic and every dependency points backward in the
  audited task sequence.

## Closure classifications

- `CORE_CLOSURE`: R4-400, R4-409, R4-430, R4-499.
- `PRODUCTION`: R4-401.
- `SECURITY`: R4-402, R4-403, R4-404, R4-450, R4-451.
- `RELIABILITY`: R4-405, R4-406, R4-408.
- `PERFORMANCE`: R4-407.
- `DATA_GOVERNANCE`: R4-420, R4-438.
- `FINAL_BENCHMARK`: R4-434, R4-435, R4-439, R4-452.
- `PRODUCT_DEMO`: R4-421, R4-423, R4-424.
- `THESIS_DEFENSE`: R4-461, R4-462.
- `DEFERRED_EXTERNAL`: R4-410 through R4-413, R4-422, R4-431 through
  R4-433, R4-436, and R4-460.
- `OPTIONAL_STRETCH`: R4-437, R4-440, R4-453.

Classification is a planning view, not a maturity or completion claim. An item
classified `DEFERRED_EXTERNAL` may contain locally executable preparation, but
it cannot pass without its declared external evidence.

## Frozen scientific inputs

The audit treats the following as immutable inputs:

- Claim Matrix SHA-256
  `c6656ac6a1f4634c001cace78867c924b950eebef944380f8a26c556fac9d4cc`;
- final claim counts: zero `C-PASS`, two `C-NO-NOVELTY`, five
  `C-NO-CLAIM`, and zero `C-DEFERRED`;
- R3-325 exactly
  `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; and
- the 31-entry negative-result ledger prefix digest
  `89fe0c2eb1cab8da5162c4769f4bcef41bc8b904dcc0f933a1bf069192032706`.

Round 4 engineering can enable future research. It cannot rewrite these
outcomes, invent historical propensities, or turn production polish into a
scientific claim.

## Executable control

`scripts/round4_graph_gate.py` validates both the Round 4 contract and its live
mirror in `TASK_GRAPH.yaml`. It rejects incomplete promotion, dependency or
gate drift, classification loss, premature conditional activation, Round 3
claim promotion, and invalid active/closed states. Directed mutation tests
exercise these failure paths.
