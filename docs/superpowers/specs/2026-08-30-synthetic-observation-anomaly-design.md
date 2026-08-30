# Synthetic Observation and Anomaly Discovery Design

Date: 2026-08-30
Checkpoint: RM-241 (RM-238 is already occupied by the frontend visual foundation)

## Scope

Run the existing `product-readiness-scenarios-v1` catalog through the existing
`ScenarioKernel` and RM-237 policy-observation trace. The campaign is a bounded
synthetic runtime observation exercise, not a new algorithm or a scientific
claim campaign. It starts with 16 deterministic seeds per frozen scenario and
does not exceed 32 seeds per scenario.

## Components and data flow

`scripts/synthetic_observation_campaign.py` loads and hashes the frozen catalog,
freezes a compact manifest, builds each scenario with the existing
`deterministic_scenarios.build_manifest`, runs the existing `ScenarioKernel`
twice for replay verification, and collects the returned `PolicyObservation`
sequence. All observations are validated against
`routemind-policy-observation-v1`, checked for ordering, transition invariants,
provenance, and digest stability, then exported through
`ResearchObservationExporter` below `ROUTEMIND_DATA_ROOT`.

The repository receives only the manifest, run registry, aggregate metrics,
candidate records, explanation attack, decision, and evidence note. Raw JSONL
observations remain external. Compact artifacts contain relative paths and
digests, never a hard-coded data-root path.

## Preregistered scan

The scan records decision and switch counts/rates, dwell ticks, occupancy,
transition counts, reversals, fallback/degradation labels, scenario/load
configuration, and quality outcomes. Solver latency, route recomputation,
assignment churn, SLA/risk deltas, and other consequence components are marked
unavailable unless already present in the trace; no missing value is imputed.

Candidate rules are transparent: a pattern must occur in at least two seeds in
the affected scenario, and every candidate receives one residue verdict. The
simple explanation attack checks fixed scenario construction, fixed strategy,
ordinary load/shortage behavior, fallback activation, initialization, replay,
and measurement/export artifacts. Only a reproducible `UNEXPLAINED_RESIDUE`
could justify a future Claude Science reopening; this campaign never proposes
an algorithm or promotes a claim.

## Validation and failure handling

Any malformed observation, schema failure, ordering violation, digest mismatch,
or raw-data export failure aborts the campaign without deleting prior artifacts.
Rerunning the same manifest must reproduce aggregate and raw-export digests.
The runner uses local deterministic providers only and performs no network,
cloud, provider, or paid-API calls.
