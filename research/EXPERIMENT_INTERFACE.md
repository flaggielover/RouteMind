# Experiment Interface

This is the provider-neutral local interface for future bounded studies. It is
a preparation contract, not an authorization to run a confirmatory or paid
campaign.

## Manifest minimum

Each material study must bind:

- `experiment_id`, hypothesis/question, and manifest version;
- implementation Git revision and successful CI run;
- dataset/reference-data identity and checksum;
- scenario generator, scenario ID, city/regime, and seed;
- strategy IDs and versions, policy version, and canonical parameters;
- random-stream ownership and derived stream digests;
- environment, hardware, solver version, thread/resource/time limits;
- output root below `ROUTEMIND_DATA_ROOT`;
- statistical estimands, stopping/exclusion rules, and claim boundary.

## Execution sequence

1. Validate the manifest and all source digests.
2. Create an isolated content-addressed output directory and environment record.
3. Execute one bounded run or pair at a time, writing raw run output before
   aggregation.
4. Record `COMPLETED`, `TIMEOUT`, `STRATEGY_FAILURE`, `FALLBACK`,
   `HARNESS_DEFECT`, or `INFRASTRUCTURE_DEFECT` explicitly.
5. Aggregate only from retained raw records and emit a digest-linked report.
6. Run independent checks and leakage/claim gates.

`CampaignArtifactStore` currently implements this sequence for the frozen
Statistical RouteBench protocol and resumes already written pair records. A
future generic campaign runner must preserve the same write-once and
fail-closed semantics.

## Failure and restart rules

Failed or partial runs remain in the ledger. They are not replaced by a more
favorable seed. A restarted campaign may reuse only byte-identical verified
artifacts under the same manifest; changed bytes fail closed. A hard process
termination during an in-flight pair is a known gap: the pair is rerun under
the same seed, and the next version should add an atomic per-arm checkpoint if
that distinction is scientifically material.
