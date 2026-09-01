# Claude Science Work Packets

Prepared: 2026-09-02 (Asia/Shanghai)

These ten packets contain the remaining scientific judgment. Engineering
commands are Windows/PowerShell examples from the repository root. Set
`ROUTEMIND_DATA_ROOT` to an authorized external directory before any data or
experiment run; never commit external data. Passing a readiness command is not
a scientific result.

## R3-313 — Li/Lim applicability (historical terminal task)

- Scientific question: do Li/Lim pickup-delivery problem semantics map natively
  to RouteMind, require an explicitly lossy transformation, or fall outside the
  current research scope?
- Current evidence: Round 3 closed this task as `deferred_external` and moved
  any future analysis to R4-437; Solomon CVRPTW ingestion is available, but no
  Li/Lim dataset or semantic mapping is present.
- Engineering support/data: public-benchmark parser, gap analysis, manifest and
  artifact infrastructure; external data root currently contains Solomon only.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_public_benchmarks.py services/compute-api/tests/test_benchmark_gap_analysis.py --no-cov -q`.
- Expected output: parser/gap tests pass, followed—only if research scope is
  activated—by a content-addressed semantic mapping and one of `COMPATIBLE`,
  `TRANSFORMED`, or `NOT_APPLICABLE`.
- Unresolved decision: whether pickup-delivery semantics belong in the thesis
  scope and which transformations preserve scientific comparability.
- Dependencies/acceptance: R3-310 passed; map semantics without forced
  compatibility and retain evidence for the disposition.

## R3-355 — IPS/DR applicability (historical terminal task)

- Scientific question: were the frozen Round 3 logs causally identifiable for
  IPS/DR, and if a future log lineage differs, what estimand and assumptions are
  scientifically defensible?
- Current evidence: R3-354 returned non-identifiable; R3-355 is terminally
  deferred. The external 640-row observation fixture is simulated,
  deterministic, and explicitly observational-association only.
- Engineering support/data: OPE identifiability audit, decision corpus,
  append-only negative-result handling, and new exact decision-time logging.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_ope_identifiability.py services/compute-api/tests/test_r4_decision_logging.py --no-cov -q`.
- Expected output: fail-closed support audit; absent positive support evidence,
  `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS` and no estimator claim.
- Unresolved decision: causal estimand, sufficiency/interference/censoring
  assumptions, and whether any future log lineage warrants reactivation.
- Dependencies/acceptance: frozen R3-354 evidence; activate estimators only from
  positive, lineage-matched identifiability and report ESS/clipping instability.

## R4-432 — observed-data Twin calibration

- Scientific question: which preregistered calibration model, metrics,
  uncertainty treatment, exclusions, and drift limits are appropriate for the
  authorized observed calibration split?
- Current evidence: Round 3 split/calibration/fidelity contracts and explicit
  insufficient-data/non-fidelity outcomes; R4-431 has no authorized observed
  dataset.
- Engineering support/data: immutable split contract, calibration engine,
  fidelity protocol, provenance, artifact digests and tests. Only synthetic
  fixtures are currently available for these paths.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_twin_split_contract.py services/compute-api/tests/test_twin_calibration.py services/compute-api/tests/test_twin_fidelity_protocol.py --no-cov -q`.
- Expected output: a manifest-linked calibration artifact with parameters,
  uncertainty, drift, exclusions, failures and cost, or an explicit no-result.
- Unresolved decision: model family/priors, metric hierarchy, uncertainty and
  drift interpretation; held-out data must remain unseen.
- Dependencies/acceptance: R4-430 passed and R4-431 must supply an approved
  frozen split; calibrate only on that split with preregistered metrics.

## R4-433 — immutable held-out Twin fidelity

- Scientific question: do the calibrated Twin variables meet frozen fidelity
  thresholds, with what uncertainty and external-validity boundary?
- Current evidence: Round 3 retained zero observed held-out records and an
  `INSUFFICIENT_DATA`/non-fidelity boundary; no current observed split exists.
- Engineering support/data: held-out validator, drift audit, what-if validity,
  non-fidelity reporting, immutable manifest and negative-result tests.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_twin_held_out_validation.py services/compute-api/tests/test_twin_drift.py services/compute-api/tests/test_twin_what_if_validity.py services/compute-api/tests/test_twin_non_fidelity_report.py --no-cov -q`.
- Expected output: variable-level effect/uncertainty/failure records and a
  bounded fidelity or non-fidelity disposition, with no post-result tuning.
- Unresolved decision: interpretation of partial-variable passes, drift and
  uncertainty; whether any claim is supportable.
- Dependencies/acceptance: R4-432 and its untouched held-out identities; retain
  every failure and never generalize partial passes.

## R4-435 — powered RADS preregistration

- Scientific question: what hypotheses, variants, regimes, experimental units,
  effect sizes, multiplicity/stopping rules, exclusions and claim boundaries
  constitute a defensible powered RADS campaign?
- Current evidence: frozen Round 3 baseline, RADS-H, Safe-RADS, stability,
  boundary, counterfactual, ablation and robustness artifacts, including
  insufficient-data outcomes.
- Engineering support/data: bounded scheduler, tick instrumentation,
  deterministic variants, content-addressed artifacts, power utilities and
  full failure retention. Existing data are synthetic Round 3 experiments.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_rads_baseline.py services/compute-api/tests/test_rads_h_experiment.py services/compute-api/tests/test_safe_rads_experiment.py services/compute-api/tests/test_rads_ablation.py services/compute-api/tests/test_rads_stability_map.py services/compute-api/tests/test_rads_robustness.py services/compute-api/tests/test_r4_rads_instrumentation.py services/compute-api/tests/test_r4_experiment_scheduler.py --no-cov -q`.
- Expected output: a frozen preregistration and resource estimate covering
  compute, duration, storage, provider, cost and all analysis rules.
- Unresolved decision: scientific hypotheses/effects, power/multiplicity and
  whether observed-data fidelity permits the planned claims.
- Dependencies/acceptance: R4-433 scientific disposition and passed R4-434;
  Round 3 negative outcomes remain inputs, not tuning targets; owner approval is
  required before R4-436.

## R4-437 — Li/Lim pickup-delivery applicability

- Scientific question: is native pickup-delivery now in scope, and if so is a
  scientifically valid native or transformed comparison possible?
- Current evidence: R3-313 was not activated; available public benchmark data
  are Solomon CVRPTW, not Li/Lim pickup-delivery.
- Engineering support/data: public benchmark ingestion, gap analysis, RouteBench
  artifacts and deterministic runner foundations.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_public_benchmarks.py services/compute-api/tests/test_benchmark_gap_analysis.py --no-cov -q`.
- Expected output: `COMPATIBLE`, `TRANSFORMED`, or `NOT_APPLICABLE`, plus a
  semantic mapping and provenance; transformations must be labeled.
- Unresolved decision: activation and semantic equivalence boundary.
- Dependencies/acceptance: R4-400 passed; activate only when pickup-delivery is
  explicitly in current research scope and never claim transformed data as
  native support.

## R4-439 — OPE identifiability re-audit

- Scientific question: do **new** decision-time logs establish valid propensity,
  effective support, state sufficiency, overlap, non-interference, censoring and
  missingness assumptions for a specified causal estimand?
- Current evidence: R3-354 was non-identifiable. R4-438 now provides exact
  logging and executable overlap diagnostics, but no new lineage-qualified
  exploratory log corpus has been collected.
- Engineering support/data: R4-438 logging/support audit and existing
  identifiability engine; the 640-row deterministic fixture cannot prove
  stochastic support.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_r4_decision_logging.py services/compute-api/tests/test_ope_identifiability.py --no-cov -q`.
- Expected output: an assumption-by-assumption audit with support/ESS/overlap
  evidence or `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS`.
- Unresolved decision: causal estimand and scientific validity of every
  identification assumption; volume alone is insufficient.
- Dependencies/acceptance: R4-438 passed; retain positive or negative result and
  activate no estimator without positive evidence.

## R4-440 — conditional IPS/DR estimation

- Scientific question: if R4-439 is positive, which IPS, SNIPS and doubly robust
  estimands, nuisance models and sensitivity analyses are valid?
- Current evidence: condition is presently unevaluated because R4-439 has no new
  log audit; Round 3 was non-identifiable.
- Engineering support/data: decision-time propensities, overlap diagnostics,
  statistical artifact infrastructure and negative-result ledger.
- Runnable readiness command: `services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_r4_decision_logging.py services/compute-api/tests/test_ope_identifiability.py --no-cov -q`.
- Expected output: only after activation, estimates with ESS, clipping, weight
  distribution, overlap, uncertainty and sensitivity; otherwise terminal
  `CONDITION_NOT_MET`/`NO-CLAIM` evidence.
- Unresolved decision: activation, estimand/nuisance model, clipping and
  uncertainty interpretation.
- Dependencies/acceptance: positive R4-439 identifiability is mandatory;
  unsupported or unstable estimators close without a claim.

## R4-461 — prior art and final claim statuses

- Scientific question: after all evidence, which candidate contributions remain
  supported, non-subsumed and novel, and which must be no-claim/negative?
- Current evidence: frozen Round 3 claim matrix, negative-result ledger,
  reproduction attempt and figures; Round 4 OPE and reproduction inputs remain
  open.
- Engineering support/data: executable claim-matrix and negative-result gates,
  manifest-linked evidence, final-figure generator and reproduction package.
- Runnable readiness command: `python -m unittest scripts.claim_matrix_gate_test scripts.negative_results_gate_test && services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_independent_reproduction.py --no-cov -q`.
- Expected output: one append-only status per claim mapping hypothesis, prior
  art, data, manifest, metric, test, effect, uncertainty, verification and
  reproduction.
- Unresolved decision: prior-art synthesis, novelty/subsumption and final claim
  boundaries across production, empirical and mathematical statements.
- Dependencies/acceptance: terminal R4-439 and R4-460 evidence; only supported,
  independently bounded, non-subsumed claims may pass.

## R4-462 — thesis evidence synthesis

- Scientific question: what coherent thesis is justified when methods,
  engineering evidence, experiments, statistics, prior art, external validity,
  reproduction, negative results and limitations are considered together?
- Current evidence: frozen Round 3 scientific closure, manifests, claim matrix,
  negative results, generated figures and this Round 4 readiness packet.
- Engineering support/data: deterministic figure generation, claim and
  negative-result gates, evidence audits, manifests and reproducibility records.
- Runnable readiness command: `python -m unittest scripts.final_scientific_figures_test scripts.claim_matrix_gate_test scripts.negative_results_gate_test`.
- Expected output: a manifest-linked thesis package whose figures/tables are
  generated from results and whose negative/no-claim outcomes are first-class.
- Unresolved decision: scientific narrative, contribution hierarchy, limitations
  and conclusion synthesis.
- Dependencies/acceptance: final R4-461 claim statuses; keep evidence classes
  separated and retain every negative/no-claim outcome append-only.
