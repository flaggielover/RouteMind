# RouteMind Non-Claude-Science Closure Sweep Implementation Plan

## 1. Extend the executable state vocabulary

- Add `condition_not_met` to `TASK_GRAPH.yaml` status values.
- Extend `scripts/validate_control_plane.py` and `scripts/round4_graph_gate.py`
  so the state is valid only as a terminal disposition for an explicitly
  conditional or optional task.
- Record the R4-453 activation evaluation, timestamp, checkpoint, and
  reactivation rule in the task record and closure evidence.
- Add directed mutation tests for missing evaluation evidence and accidental
  activation.

## 2. Close R4-430 experiment scheduling

- Add a typed, deterministic scheduler contract under the Python compute
  application boundary.
- Validate frozen manifest digests, resource/concurrency/timeout limits,
  cancellation, lineage, write-once evidence, and Python-only orchestration.
- Add unit and negative-path tests and `evidence/gates/R4-430/experiment-scheduler.md`.

## 3. Close R4-434 RADS instrumentation

- Add a versioned tick-level observation contract that requires state, action,
  switch, constraint, fallback, latency, outcome, and lineage fields.
- Reject missing/invalid fields without substituting synthetic values.
- Add deterministic replay digest and metrics tests and the R4-434 evidence file.

## 4. Close R4-438 decision logging

- Add decision-time logging for policy identity, deterministic action or exact
  propensity, action set, state digest, shared-resource context, outcome
  lineage, tenant pseudonym, retention, and overlap diagnostics.
- Forbid retroactive propensity fabrication and raw identity fields.
- Add support/overlap tests and the R4-438 evidence file.

## 5. Close R4-451 and R4-452 agent evaluation

- Add a privacy-bounded adversarial corpus with all nine required case classes,
  versioned expected evidence, tool scope, scoring, and corpus digest.
- Add a deterministic read-only evaluator using the existing agent substrate;
  measure tool correctness, grounding/citation, refusal, hallucination boundary,
  latency, cost, reproducibility, and failures.
- Add corpus/evaluator tests and compact evidence for both tasks.

## 6. Prepare science and external work packages

- Add `evidence/closure-sweep/2026-09-02/claude-science-work-packets.md` for
  the ten research tasks, including exact unresolved questions, existing
  engineering support, data, commands, outputs, dependencies, and criteria.
- Add external/downstream readiness notes for blocked production/provider lanes;
  preserve all historical attempts and do not claim target qualification.

## 7. Reconcile the graph and validate

- Transition the five engineering tasks to `passed` only after executable gates.
- Transition genuinely blocked downstream lanes to `blocked` or
  `deferred_external` with exact blockers and local evidence paths.
- Leave Claude Science tasks open, mark R4-453 `condition_not_met`, and leave
  R4-499 blocked on its real dependency set.
- Update `PROGRESS.md`, `HANDOFF.md`, and the closure-sweep evidence record.
- Run fast/full Python, Java, web, graph, contract, determinism, and evidence
  gates; review diff/checks, commit, and push when origin is healthy.
