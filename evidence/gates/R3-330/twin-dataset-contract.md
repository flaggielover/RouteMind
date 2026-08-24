# R3-330 Digital Twin Dataset Split Contract

Date: 2026-08-24 (Asia/Shanghai)
Status: passed
Implementation checkpoint: `825384d124a412fad386dbdaa4330cab3ac0b1a9`
GitHub Actions: PASS - run `32742587929` (all five jobs)

## Frozen contract

The machine-readable contract is
`docs/research/r3/manifests/twin/r3-330-twin-split-contract-v1.json`.
Its canonical contract digest is
`fb3f3162ac073815cba838f3fde5a3b8ac94604e21dc4f9049bdf3785d108eaa`; its
byte SHA-256 is
`5a1436facd2a673686d0fd8831b9b45afb0e5574604a263598672d3981730daa`.

Calibration and held-out identities are distinct:

- `r3-330-calibration-observed-v1`, identity digest
  `00226911b80061f9c3eeeccbe3ca2bff7b86e252c999dbdc5c3cdfc463e51b9e`
- `r3-330-held-out-observed-v1`, identity digest
  `68fa75e30f5889ecf5320e98f7a2c52b2cee364ff07f12ecab6ab1ba087a60e1`

The primary split axis is temporal and the secondary axis is scenario. The
contract requires event identity, temporal, scenario, geographic, and source
manifest leakage checks. Calibration may not read held-out data, validation
requires observed outcomes, and geographic handling uses aggregate partition
keys rather than exporting precise coordinates.

## Data availability and scientific boundary

No authorized immutable observed dispatch outcome corpus is present locally.
Both split artifacts therefore remain `UNAVAILABLE_NO_OBSERVED_DATA` with zero
records and no fabricated checksums. The top-level outcome is
`INSUFFICIENT_DATA`; every leakage check is explicitly `NOT_RUN_NO_DATA`.
Synthetic Twin scenarios and replay artifacts are not substituted for observed
held-out outcomes. No calibration, held-out validation, fidelity metric, or
Twin-validity claim was executed.

## Executable evidence

- `tests/test_twin_split_contract.py`: 12 directed tests; the loader itself
  reaches 100% statement and branch coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 786/786 Python tests,
  95.24% total coverage, Ruff, strict mypy, 6 schemas/18 fixtures,
  determinism, analytical archive/mart, and semantic metrics.
- GitHub Actions run `32742587929`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-330 closes `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE`. The contract is an infrastructure prerequisite; it does not
establish Digital Twin fidelity. R3-333 must freeze variable-appropriate
metrics and thresholds before any future validation attempt.
