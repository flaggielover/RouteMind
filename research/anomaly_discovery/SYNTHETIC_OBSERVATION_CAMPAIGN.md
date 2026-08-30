# Synthetic Observation Campaign

Checkpoint: RM-241
Manifest schema: `routemind-synthetic-observation-campaign-v1`
Catalog: `product-readiness-scenarios-v1` (8 frozen scenarios)
Seeds per scenario: 16
Total runs: 128
Total observations: 640
Raw export: `research-observations/policy-observations-v1.jsonl` below `ROUTEMIND_DATA_ROOT`
Raw data committed to Git: **NO**
Observation schema: `routemind-policy-observation-v1`
Replay consistency: **PASS**
Observation quality: **PASS**
Raw export SHA-256: `bee86ff2d804dc6ae99d54d6b27a2539bdd17736aba68085d9982c8f8619192b`

## Metric availability

| Metric | Status | Source |
| --- | --- | --- |
| decision_count | AVAILABLE | PolicyTrace |
| switch_count | AVAILABLE | PolicyTrace |
| switch_rate | DERIVED | PolicyTrace.metrics |
| dwell_ticks | AVAILABLE | PolicyTrace |
| policy_occupancy | DERIVED | PolicyTrace.metrics |
| transition_matrix | DERIVED | PolicyTrace.metrics |
| short_window_reversals | DERIVED | PolicyTrace.metrics |
| decision_latency | UNAVAILABLE | not in PolicyObservation |
| solver_runtime | UNAVAILABLE | not in PolicyObservation |
| fallback_degradation_state | AVAILABLE | scenario configuration |
| assignment_churn | UNAVAILABLE | not in PolicyObservation |
| route_recomputation | UNAVAILABLE | not in PolicyObservation |
| sla_risk_delta | UNAVAILABLE | not in PolicyObservation |
| consequence_components | AVAILABLE | observation consequences |
| missingness | DERIVED | quality validator |
| provenance_completeness | DERIVED | quality validator |
| replayability | DERIVED | ScenarioKernel replay digest |
| digest_consistency | DERIVED | canonical digest |
| ordering_invariant_violations | DERIVED | quality validator |

## Scenario summary

| Scenario | Runs | Decisions | Switches | Reversals | Switch rate | Stable across seeds | Quality |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| NORMAL_BASELINE | 16 | 48 | 0 | 0 | 0.000000 | YES | PASS |
| DINNER_RUSH | 16 | 128 | 0 | 0 | 0.000000 | YES | PASS |
| COURIER_SHORTAGE | 16 | 64 | 0 | 0 | 0.000000 | YES | PASS |
| MERCHANT_DELAY | 16 | 48 | 0 | 0 | 0.000000 | YES | PASS |
| TRAFFIC_DEGRADATION | 16 | 48 | 0 | 0 | 0.000000 | YES | PASS |
| ROUTING_PROVIDER_FAILURE | 16 | 48 | 0 | 0 | 0.000000 | YES | PASS |
| DISPATCH_PRESSURE | 16 | 192 | 0 | 0 | 0.000000 | YES | PASS |
| RECOVERY | 16 | 64 | 0 | 0 | 0.000000 | YES | PASS |

## Candidate scan

Candidate anomalies detected: **2**

| ID | Affected scenarios | Reproducibility | Simple explanation | Final residue verdict |
| --- | --- | --- | --- | --- |
| AD-001 | NORMAL_BASELINE, DINNER_RUSH, COURIER_SHORTAGE, MERCHANT_DELAY, TRAFFIC_DEGRADATION, ROUTING_PROVIDER_FAILURE, DISPATCH_PRESSURE, RECOVERY | 128/128 runs; 16 independent seeds per scenario | Explained: the frozen runner instantiates ScenarioKernel(strategy=nearest) and does not perform policy selection. | EXPLAINED |
| AD-002 | ROUTING_PROVIDER_FAILURE | 16/16 runs; 16 independent seeds | Measurement artifact: provider fallback is exercised by the travel layer but ScenarioKernel does not copy TravelTime.fallback_used into PolicyObservation.fallback_state. | MEASUREMENT_ARTIFACT |

The scan is descriptive. No policy-switch cost, causal effect, novelty, production behavior, Digital Twin fidelity, or strategy superiority claim is made.
