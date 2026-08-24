# RouteMind Round 3 Claim Matrix

Matrix version: `r3-claim-matrix-v1`
Status: preregistered candidates; no supported scientific claims yet

| Claim ID | Hypothesis | Prior art | Dataset/scenario | Manifest | Primary metric/test | Effect/uncertainty gate | Independent verification/reproduction | Current gates | Final wording |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R3-A1 | H1-A1: scoped Solomon verified-feasibility rate >= 0.95 lower bound | R3-357 pending; benchmark sources verified in R3-310/311 | Preregistered compatible Solomon subset | R3-311 pending | Verified feasible completion; 95% Wilson interval | Lower bound >= 0.95; all instances retained | Independent verifier R3-314; exact cross-check R3-315; reproduction R3-356 | E-PENDING / X-PENDING / S-PENDING / C-DEFERRED | No claim permitted |
| R3-A2 | Describe RouteMind objective gaps and timeout behavior without a superiority hypothesis | R3-357 pending | Solomon plus bounded Gehring-Homberger subset | R3-311/312/316 pending | Median/p90/best/worst gap; timeout/infeasible rate | Descriptive uncertainty; reference status retained | R3-314/315/356 pending | E-PENDING / X-PENDING / S-PENDING / C-DEFERRED | No quality or optimality claim permitted |
| R3-B1 | H1-B1: risk-aware lowers paired risk with assignment non-inferiority | R3-357 pending | Preregistered RouteBench stress matrix and common streams | R3-320/325 pending | Paired difference interval; Holm correction | Risk CI below 0; assignment margin -0.02 | Independent manifest reproduction R3-356 pending | E-PENDING / X-PENDING / S-PENDING / C-DEFERRED | No superiority claim permitted |
| R3-C1 | Calibrated Twin meets frozen held-out fidelity thresholds | R3-357 pending | Immutable calibration and disjoint held-out datasets | R3-330/331/332 pending | Variable-specific fidelity metrics from R3-333 | Every primary absolute threshold plus leakage gate | Alternate clean-room validation R3-356 pending | E-PENDING / X-PENDING / S-PENDING / C-DEFERRED | No Twin-validity claim permitted |
| R3-D1 | H1-D1: formal RADS-H reduces switching with bounded service/cost change | R3-357 pending | Preregistered CRN stress regimes | R3-341/342 pending | Paired switching, service, and cost intervals; Holm | >=25% switching reduction; service -0.02; cost +3% bounds | Cooldown/fixed/RADS baselines plus R3-356 | E-PENDING / X-PENDING / S-PENDING / C-DEFERRED | No stability or novelty claim permitted |
| R3-D2 | Explicit Safe-RADS constraint is satisfied with measured efficiency cost | R3-357 pending | Preregistered risk regimes after constraint freeze | R3-344/345 pending | Violation, feasibility, cost, lateness, calibration | Epsilon and uncertainty frozen by R3-344 | Penalty-only/conservative baselines and R3-356 | E-PENDING / X-PENDING / S-PENDING / C-DEFERRED | Safety wording prohibited until C review |
| R3-E1 | Determine whether current logs identify off-policy effects | R3-357 pending | Privacy-bounded Decision Corpus | R3-350/354 pending | Propensity availability, overlap, effective support | Identifiable or OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS | Corpus audit and alternate checker | E-PENDING / X-PENDING / S-NOT-APPLICABLE / C-DEFERRED | No OPE claim permitted |

Every row must retain claim ID, hypothesis, prior art, dataset/scenario, manifest,
metric, statistical test, effect size, uncertainty, independent verification,
reproduction status, and final wording. New claims require a new row before
material results are inspected. Only `C-PASS` rows may appear as supported claims
in the Round 3 closure report.
