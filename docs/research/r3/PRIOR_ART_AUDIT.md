# RouteMind Round 3 Adversarial Prior-Art Audit

Audit version: `r3-prior-art-audit-v1`

Search date: 2026-08-25 (Asia/Shanghai)

Status: complete bounded audit; not a patentability or freedom-to-operate opinion

## Decision rule and scope

This audit asks whether each RouteMind candidate category is already disclosed,
closely approached, or only partially separated from current primary or
peer-reviewed work. It deliberately searches for disconfirming prior art. A
RouteMind-specific name, threshold, schema, or combination is not treated as a
scientific contribution by itself.

The allowed classifications are:

- `SUBSUMED`: prior work covers the essential proposition or mechanism.
- `CLOSE_PRIOR`: prior work covers most of the proposition; remaining
  differences are implementation, domain, or evaluation details.
- `PARTIAL_GAP`: prior work covers the core mechanism, while this bounded search
  did not find the exact application-level combination.
- `PLAUSIBLE_GAP`: a more material separation survived the bounded search, but
  still is not a novelty finding.
- `UNRESOLVED`: source quality, terminology, or search coverage is insufficient
  to classify more strongly.

No category received `PLAUSIBLE_GAP`. `PARTIAL_GAP` means only that the exact
RouteMind combination was not located in this bounded search. It does not prove
novelty, non-obviousness, priority, usefulness, or claim admissibility.

The audit covers the seven Claim Matrix rows plus the R3-346 policy-boundary and
R3-347 counterfactual Decision X-Ray categories. It is literature-focused, not
a patent search, citation-network review, or legal opinion.

## Adversarial classification

| Audit ID | Candidate category | Closest prior art | Adversarial finding | Classification | Claim consequence |
| --- | --- | --- | --- | --- | --- |
| PA-A1 | Verified VRPTW feasibility on Solomon instances | S01, S02 | Solomon established the benchmark family and computational comparison; Desrochers et al. established exact VRPTW optimization on benchmark problems. Independent feasibility checking and a Wilson threshold are evaluation discipline, not a new routing mechanism. | `SUBSUMED` | R3-A1 remains `S-FAIL/C-NO-CLAIM`; no novelty, feasibility, optimality, or superiority claim follows. |
| PA-A2 | All-outcome VRPTW gap and timeout census | S01, S02, S03 | Benchmark comparison, best/reference objectives, and computational outcomes are established practice. Retaining timeouts and non-comparable cases is valuable reporting hygiene but does not create a scientific novelty category. | `SUBSUMED` | R3-A2 remains descriptive and `C-NO-CLAIM`. |
| PA-B1 | Risk-aware dispatch with paired risk reduction and assignment non-inferiority | S04, S05 | Robust and distributionally robust routing already optimize uncertain demand, travel time, and budget-overrun risk. RouteMind's paired CRN design and assignment margin are an evaluation protocol around established risk-aware routing ideas. | `CLOSE_PRIOR` | The frozen R3-325/R3-327 `S-FAIL/C-NO-CLAIM` outcome is unchanged; no risk-aware superiority claim is admissible. |
| PA-C1 | Calibrated logistics Digital Twin with disjoint held-out fidelity gates | S06, S07 | Logistics Digital Twins have been verified/validated against real operations, and calibration/validation methodologies for warehouse twins are published. RouteMind's split contract and absolute thresholds are scope controls rather than a new Digital Twin principle. | `SUBSUMED` | Existing `INSUFFICIENT_DATA/C-NO-CLAIM` remains; no Twin fidelity, transfer, or causal claim is admissible. |
| PA-D1 | Hysteresis-based dispatch strategy switching with bounded service/cost change | S08 | Hysteresis supervisory control already selects among candidate controllers and bounds switching under uncertainty. This search did not locate the exact RouteMind dispatch-strategy/CRN/non-inferiority combination, but the core anti-chatter mechanism is prior art. | `PARTIAL_GAP` | The application-level search gap is not novelty. Missing tick-level logs still force `C-NO-CLAIM`; no empirical or theoretical stability claim is admissible. |
| PA-D2 | Explicitly constrained Safe-RADS dispatch with measured efficiency cost | S04, S09 | Robust routing and constrained policy optimization already formalize uncertainty-aware decisions and explicit safety constraints. A RouteMind-specific late-service threshold and strategy name do not establish a new scientific mechanism. | `CLOSE_PRIOR` | Missing Safe-RADS outcomes still force `C-NO-CLAIM`; no safety, calibration, feasibility, or efficiency claim is admissible. |
| PA-D3 | Interpretable dispatch policy boundaries | S10, S11 | Decision-tree policy extraction, verification, and interpretable differentiable trees for reinforcement learning are established. RouteMind's shallow axis-aligned boundary plan is directly within that family. | `SUBSUMED` | R3-346 remains `INSUFFICIENT_DATA/C-NO-CLAIM`; no interpretable boundary was estimated. |
| PA-D4 | Counterfactual Decision X-Ray with minimal perturbation and replay lineage | S12, S13 | Minimal-change counterfactual explanations and counterfactual explanations for reinforcement-learning agents are established. Exact same-model replay provenance is a useful engineering constraint; this search did not find the full RouteMind lineage bundle as one contribution. | `PARTIAL_GAP` | The bundle-level search gap is not novelty. R3-347 has zero executable replays and remains `C-NO-CLAIM`; no causal interpretation is allowed. |
| PA-E1 | OPE identifiability from logged dispatch decisions | S14, S15, S16 | Off-policy value estimation, doubly robust estimators, variance/support limitations, and unobserved-confounding boundaries are established. Refusing to fabricate propensities correctly applies those limits. | `SUBSUMED` | `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS` remains a negative diagnostic, not a novel OPE method or causal result. |

## Source ledger

All sources below are original works, official publisher/proceedings pages, or
peer-reviewed articles. The URLs were rechecked during this audit.

- **S01** - M. M. Solomon, "Algorithms for the Vehicle Routing and Scheduling
  Problems with Time Window Constraints," *Operations Research* 35(2), 1987.
  https://doi.org/10.1287/opre.35.2.254
- **S02** - M. Desrochers, J. Desrosiers, and M. Solomon, "A New Optimization
  Algorithm for the Vehicle Routing Problem with Time Windows," *Operations
  Research* 40(2), 1992. https://doi.org/10.1287/opre.40.2.342
- **S03** - J. Homberger and H. Gehring, "Two Evolutionary Metaheuristics for
  the Vehicle Routing Problem with Time Windows," *INFOR* 37(3), 1999.
  https://doi.org/10.1080/03155986.1999.11732386
- **S04** - "Robust Vehicle Routing," *INFORMS Tutorials in Operations
  Research*, 2010/2014 online publication.
  https://doi.org/10.1287/educ.1100.0078
- **S05** - A. Flajolet, S. Blandin, and P. Jaillet, "Robust Adaptive Routing
  Under Uncertainty," *Operations Research* 66(1), 2018.
  https://doi.org/10.1287/opre.2017.1662
- **S06** - A. C. B. Vieira et al., "Simulation-based decision support tool for
  in-house logistics: the basis for a digital twin," *Computers & Industrial
  Engineering* 153, 2021. https://doi.org/10.1016/j.cie.2020.107094
- **S07** - "A method for developing and validating simulation models for
  automated storage and retrieval system digital twins," *International
  Journal of Advanced Manufacturing Technology*, 2023.
  https://doi.org/10.1007/s00170-023-12660-y
- **S08** - J. P. Hespanha, D. Liberzon, and A. S. Morse, "Hysteresis-based
  switching algorithms for supervisory control of uncertain systems,"
  *Automatica* 39(2), 2003.
  https://doi.org/10.1016/S0005-1098(02)00241-8
- **S09** - J. Achiam et al., "Constrained Policy Optimization," ICML 2017,
  PMLR 70. https://proceedings.mlr.press/v70/achiam17a.html
- **S10** - O. Bastani, Y. Pu, and A. Solar-Lezama, "Verifiable Reinforcement
  Learning via Policy Extraction," NeurIPS 2018.
  https://papers.nips.cc/paper_files/paper/2018/hash/e6d8545daa42d5ced125a4bf747b3688-Abstract.html
- **S11** - A. Silva et al., "Optimization Methods for Interpretable
  Differentiable Decision Trees Applied to Reinforcement Learning," AISTATS
  2020, PMLR 108. https://proceedings.mlr.press/v108/silva20a.html
- **S12** - S. Wachter, B. Mittelstadt, and C. Russell, "Counterfactual
  Explanations without Opening the Black Box," *Harvard Journal of Law &
  Technology* 31(2), 2018.
  https://jolt.law.harvard.edu/assets/articlePDFs/v31/Counterfactual-Explanations-without-Opening-the-Black-Box-Sandra-Wachter-et-al.pdf
- **S13** - M. L. Olson et al., "Counterfactual State Explanations for
  Reinforcement Learning Agents via Generative Deep Learning," *Artificial
  Intelligence* 295, 2021. https://doi.org/10.1016/j.artint.2021.103455
- **S14** - N. Jiang and L. Li, "Doubly Robust Off-policy Value Evaluation for
  Reinforcement Learning," ICML 2016, PMLR 48.
  https://proceedings.mlr.press/v48/jiang16.html
- **S15** - P. Thomas and E. Brunskill, "Data-Efficient Off-Policy Policy
  Evaluation for Reinforcement Learning," ICML 2016, PMLR 48.
  https://proceedings.mlr.press/v48/thomasa16.html
- **S16** - H. Namkoong et al., "Off-policy Policy Evaluation for Sequential
  Decisions Under Unobserved Confounding," NeurIPS 2020.
  https://papers.nips.cc/paper/2020/hash/da21bae82c02d1e2b8168d57cd3fbab7-Abstract.html

## Claim discipline and limitations

- The classifications constrain, but do not replace, R3-359's final claim
  review. A `PARTIAL_GAP` cannot become `C-PASS` without positive scientific
  evidence, independent verification, reproduction, defensible wording, and a
  stronger novelty review.
- No source was used to reinterpret, tune, rerun, or optimize R3-325. Its frozen
  outcome remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
- Search absence is not evidence of absence. Synonym, language, indexing, patent,
  and unpublished-work coverage is incomplete.
- RouteMind's reproducibility, lineage, fail-closed reporting, and no-claim
  boundaries may be strong engineering practices without being scientific
  novelty.
- This audit supports no `C-PASS` row. R3-359 must independently assign final
  claim statuses from the full evidence record.
