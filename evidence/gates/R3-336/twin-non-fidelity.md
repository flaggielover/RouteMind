# R3-336 Twin Failure and Non-Fidelity Report

Date: 2026-08-25 (Asia/Shanghai)
Status: passed as a read-only scientific failure/non-fidelity report
Implementation checkpoint: `2d0600178e3d271fc798f71946569ae827927ae0`
GitHub Actions: PASS - run `32752905068` (all five jobs)

## Frozen report plan

The machine-readable plan is
`docs/research/r3/manifests/twin/r3-336-twin-non-fidelity-v1.json`.
Its canonical plan digest is
`ed63c2a2c7a8020076411f285ff3c7fccd3b12e7800de70c4ad5b4a9a674dd94` and its
byte SHA-256 is
`87359292944b701cedfa11546cbca2553c259645d83d6bb2b4e6857b9d58e571`.

The report is lineage-bound to the frozen plans:

- R3-330 split contract:
  `fb3f3162ac073815cba838f3fde5a3b8ac94604e21dc4f9049bdf3785d108eaa`;
- R3-333 fidelity protocol:
  `de453fdf1181b2e5a52839eb9f1b7536db3f5f5fb1177f4b5351269cfa3c1825`;
- R3-331 calibration plan:
  `86f17d2edb74a25a806348461917c9943fa9cb765579c01becccb82def02937f`;
- R3-332 held-out validation plan:
  `348150cc5bd4bd6dea1261a81e13e7240606bb24cbc1898504ec34d4c8d9cfee`;
- R3-334 drift plan:
  `587d71667062561ee98c4fe17434178dead070df30b4f1b7e33538d3bb7c3478`;
- R3-335 What-if boundary plan:
  `81c52721886c646d2ff468f500c334566e3ed7f4f66bf0f63a9c4478f4b42023`.

## Read-only report result

The generator loads the prior evidence and does not run optimization, replay,
simulation, causal inference, or synthetic substitution. Both authorized Twin
split artifacts contain zero observed records, so the result is:

- `status`: `INSUFFICIENT_DATA`;
- `thresholds`: `NOT_EVALUATED_NO_DATA`;
- `unsupported_regimes`: `NOT_ANALYZED_NO_DATA`;
- `sensitivity`: `NOT_RUN_NO_DATA`;
- `data_limits`: `INSUFFICIENT_DATA`;
- `claim_status`: `C-NO-CLAIM`.

All four R3-333 thresholds, all four drift axes, and the three R3-335 What-if
modes remain explicitly represented. No Twin-validity, causal, external-validity,
stability, or simulation-transfer claim is authorized. R3-325 remains frozen
exactly as `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Executable evidence

- Five directed tests pass; the R3-336 module reaches 100% statement and branch
  coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 831/831 Python tests,
  95.68% total coverage, Ruff and strict mypy, 6 schemas/18 fixtures,
  determinism, analytics, semantic metrics, and repository controls.
- The real report execution returned the statuses above and the frozen source
  digests; no data-backed estimate was produced.
- GitHub Actions run `32752905068`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-336 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The negative result is valid scientific evidence and a claim-control boundary,
not an implementation failure. The next eligible critical task is R3-340,
freezing `RADS-BASELINE-v1`.
