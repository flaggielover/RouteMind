# R3-346 Interpretable Policy-Boundary Support Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed as a read-only `INSUFFICIENT_DATA` support audit
Implementation: `43e3549cf2db17b3554637b9406c2395d60eefb9`
GitHub Actions: PASS - run `32784278395` (all five jobs)

## Frozen boundary protocol

Manifest:
`docs/research/r3/manifests/rads/r3-346-policy-boundaries-v1.json`

- Plan digest:
  `02304c1910463a30a481070382d76bb55c01c76be1bd6b7bcbeba972b14da5dd`
- Byte SHA-256:
  `daa5e1a3ca7bf423eb1c1fa99ed50d1a25a35683a84751f926c056de234a7e8d`
- The only eligible learner is a depth-three shallow axis-aligned rule tree.
- Support requires empirical stability cells, selected-strategy labels,
  alternate-strategy outcomes, risk outcomes, feasibility outcomes, pairing
  units, and regime identities.
- At least two strategy classes with 30 records each and two eligible empirical
  stability cells are required before learning.
- Paired-bootstrap uncertainty and leave-one-regime-out plus threshold
  perturbation sensitivity are mandatory for every reportable boundary.
- Predictive accuracy alone, black-box substitution, synthetic filling,
  external writes, and R3-325 reruns are prohibited.

## Read-only source audit

The exact R3-343, R3-345, and R3-350 lineages were inspected after the frozen
implementation passed remote CI:

- R3-343 reports zero eligible empirical stability cells.
- R3-345 contains no Safe-RADS risk or feasibility outcome records.
- The R3-350 corpus contains two privacy-bounded synthetic records. Both have
  the selected strategy label `shadow`, so there is one class with two records.
  Candidate feasibility summaries are not feasibility outcomes, and candidate
  alternatives do not contain alternate-strategy outcomes.
- Pairing units and regime identities are absent.

Formal audit digest:
`dd5787f22a328cc6afb532624def46eea7866326b595903fc16884287ef35ed6`.

The audit returned:

- status: `INSUFFICIENT_DATA`
- available fields: `selected_strategy_labels`
- missing fields: `empirical_stability_cells`, `alternate_strategy_outcomes`,
  `risk_outcomes`, `feasibility_outcomes`, `pairing_unit`, `regime_identity`
- strategy counts: `shadow = 2`
- eligible stability cells: `0`
- all seven axes: `NOT_MAPPED_INSUFFICIENT_EMPIRICAL_SUPPORT`
- all five outputs: `NOT_ESTIMATED_INSUFFICIENT_BOUNDARY_SUPPORT`
- uncertainty: `NOT_ESTIMATED_NO_SUPPORTED_BOUNDARY`
- sensitivity: `NOT_RUN_NO_SUPPORTED_BOUNDARY`

No decision region, boundary rule, uncertainty interval, sensitivity result,
predictive model, or scientific effect was produced. This is not a failed
implementation; it is the required fail-closed scientific result for the
available evidence.

## Executable evidence

- Seven directed tests cover missing, underpowered, ready, malformed, and
  protocol-drift paths.
- The first complete Python run passed all 911 tests but measured 94.97% total
  coverage. Additional validation failure-path tests restored the unchanged
  95% gate.
- `./scripts/full-gate.ps1`: PASS - Java 81/81, Python 912/912 at 95.04%, Web
  92/92 plus production build, and all static, contract, research,
  determinism, and bounded-resilience controls.
- Actions run `32784278395`: all five jobs passed for implementation SHA
  `43e3549cf2db17b3554637b9406c2395d60eefb9` before the material read-only
  audit.

## Final disposition

R3-346 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The protocol is executable, but current evidence cannot support an
interpretable policy boundary. R3-325 remains frozen exactly as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` and was not rerun.
