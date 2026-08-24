# Round 3 Scientific Graph Audit

Date: 2026-08-24 (Asia/Shanghai)
Baseline commit: `ed947eb`
Prepared graph: `docs/research/ROUND_3_TASK_GRAPH.yaml` at the baseline commit

## Finding

The prepared graph preserved useful deferred work but made production readiness,
OIDC/tenancy, product preferences, broad agent evaluation, and telemetry export
dependencies of a generic research closure. It also existed only as a side
document: `TASK_GRAPH.yaml`, `scripts/resume.ps1`, and the control-plane validator
could not select or validate any Round 3 task. A single `status` field could not
distinguish engineering integrity from experiment execution, statistical support,
or claim validity.

## Reclassification

| Prepared task | Classification | Scientific disposition |
| --- | --- | --- |
| Production readiness contract | ROUND_4_PRODUCTION | Preserved for Round 4; removed from scientific critical path |
| Provider-backed travel quality | PARALLEL_ENGINEERING | Preserved as non-blocking external/provider validation |
| Larger VRPTW workloads | CORE_RESEARCH | Expanded into public benchmark, verifier, exact cross-check, gap, and timeout tasks |
| Statistical RouteBench/RADS | CORE_RESEARCH | Split into preregistration, CRN, paired estimation, power, multiplicity, robustness, and reporting |
| Identity and tenancy | ROUND_4_PRODUCTION | Preserved for Round 4 |
| Preferences/notifications/accessibility productization | ROUND_4_PRODUCTION | Preserved for Round 4 |
| Tracing export/cost/incident drills | PARALLEL_ENGINEERING | Preserved for operations work; not a scientific prerequisite |
| Scheduled Twin experiments | RESEARCH_INFRASTRUCTURE | Calibration and held-out science retained; production scheduling deferred |
| Broad agent evaluation | REMOVE_FROM_ROUND_3_CRITICAL_PATH | Preserved for Round 4 and never granted dispatch authority |
| Generic Round 3 closure | CORE_RESEARCH | Replaced by evidence-gated R3-365 scientific closure |

No accepted RouteMind capability is deleted. `TASK_GRAPH.yaml` now owns 45
Round 3 records across Workstreams A through E. Each record has independent
engineering, experiment, statistical, and claim status. The validator rejects
missing dimensions and rejects a generically passed research task while X, S, or
C remains open.

## Scientific sequencing

The critical sequence is provenance before data, verification before solver
claims, preregistration before experiments, calibration before held-out
validation, baseline freeze before RADS variants, and independent reproduction
plus prior-art review before claim review. Optional Li and Lim compatibility and
IPS/DR remain non-blocking. Production-heavy work moves to the Round 4 graph at
R3-365 instead of blocking scientific closure.

## Non-claims

This audit executes no benchmark, statistical campaign, Twin validation, or RADS
experiment. It creates the control plane only. CI can establish E-PASS for this
control-plane task; it cannot establish any scientific effect or novelty.
