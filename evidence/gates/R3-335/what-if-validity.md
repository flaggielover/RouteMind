# R3-335 What-if Validity Boundaries

Date: 2026-08-25 (Asia/Shanghai)
Status: passed as a validity-boundary control
Implementation checkpoint: `4fb44c1803ec2bd91853736d0acba9f28f80e96a`
GitHub Actions: PASS - run `32750946090` (all five jobs)

## Frozen boundary plan

The machine-readable plan is
`docs/research/r3/manifests/twin/r3-335-what-if-validity-v1.json`.
Its canonical plan digest is
`81c52721886c646d2ff468f500c334566e3ed7f4f66bf0f63a9c4478f4b42023` and its
byte SHA-256 is
`20640a2cd366fd992dec681c3dc4139b4b352cb9609bf71ba0542a9bceb9a57d`.

The plan keeps three interpretations separate:

- `counterfactual_replay`: descriptive replay under a specified model and
  fixed assumptions only; it cannot support causal effect, external validity,
  or source-optimality wording;
- `simulation_comparison`: scenario-relative engineering comparison with
  simulator assumptions retained; it cannot support real-world effect,
  external-validity, or causal-effect wording;
- `causal_inference`: requires an identified treatment, outcome, assumptions,
  and eligible observed data; it cannot support a causal effect without
  identification, external validity, or a generic Twin-validity claim.

When held-out validation is `INSUFFICIENT_DATA`, the only allowed status is
`NO_VALIDITY_CLAIM`. Even with supported evidence, wording remains
`SCOPE_ONLY`, and external-validity wording is always prohibited.

## Executed boundary assessment

The assessor loaded the frozen R3-332 validation outcome. Because it is
`INSUFFICIENT_DATA`, the result is:

- status: `NO_VALIDITY_CLAIM`;
- allowed scope: empty;
- `counterfactual_replay`: `BOUNDARY_ONLY`;
- `simulation_comparison`: `BOUNDARY_ONLY`;
- `causal_inference`: `BOUNDARY_ONLY`.

No counterfactual effect, simulation-to-reality comparison, causal estimate,
or external-validity claim was generated. This task formalizes claim discipline;
it does not turn replay or simulation into evidence that the Twin is valid.

## Executable evidence

- `tests/test_twin_what_if_validity.py`: six directed tests; the validity-boundary
  module reaches 100% statement and branch coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 826/826 Python tests,
  95.62% total coverage, 145 files checked by Ruff/mypy, 6 schemas/18 fixtures,
  determinism, analytical archive/mart, and semantic metrics.
- GitHub Actions run `32750946090`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-335 closes `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE / C-NO-CLAIM`.
The boundary result is a guard against overclaiming, not a causal or Twin-validity
finding.
