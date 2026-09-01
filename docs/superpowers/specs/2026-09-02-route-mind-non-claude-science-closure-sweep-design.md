# RouteMind Non-Claude-Science Closure Sweep Design

Date: 2026-09-02

## Objective

Audit every non-passed RouteMind task, close all locally executable engineering
work, prepare research work packages, preserve genuine external blockers, and
leave only Claude Science work or unavoidable external/downstream gates open.
Frozen Round 3 manifests, results, negative outcomes, claim statuses, and
historical provider evidence are read-only inputs.

## State model

The executable graph currently has no dedicated conditional terminal state. Add
`condition_not_met` to the root status vocabulary and to the Round 4 validator.
It is terminal only for an explicitly unactivated optional/conditional task and
must carry an evaluation record, timestamp/checkpoint, activation condition, and
reactivation rule. `R4-453` will use this state because no owner-approved
command-side activation exists despite the prerequisite read-only agent
evaluation being complete; no state-changing command test will be fabricated.

Externally blocked tasks retain `blocked` or `deferred_external` when an
external credential, target, provider, observed dataset, human approval, or
downstream gate is genuinely required. Their local preparation, tests, and
readiness evidence are closed and linked, but local evidence is never promoted
to live or production verification.

## Work packages

The five Codex-closable tasks are implemented as deterministic, bounded local
components:

- `R4-430`: a manifest-bound experiment scheduler with resource/concurrency/
  timeout/cancellation limits, immutable evidence protection, audit records, and
  explicit Python ownership.
- `R4-434`: a versioned RADS instrumentation contract that records tick-level
  state, action, switch, constraint, fallback, latency, outcome, and lineage;
  missing fields remain explicit failures.
- `R4-438`: decision-time propensity/exploration/action-support logging with
  privacy allowlists, tenant-safe retention, and executable overlap diagnostics;
  retroactive propensity fabrication is rejected.
- `R4-451`: a privacy-bounded adversarial analytical-agent corpus covering
  diagnosis, SQL/data analysis, reporting, experiment interpretation, what-if,
  refusal, injection, ambiguity, and unavailable evidence, with versioned
  expected evidence and scoring.
- `R4-452`: a deterministic read-only agent evaluator measuring grounding,
  citation, tool correctness, refusal/hallucination boundaries, latency/cost,
  reproducibility, and failures without promoting scientific or production
  claims.

Each component gets focused unit tests, mutation/negative-path tests where the
existing repository pattern supports them, compact evidence under its task
directory, and a task-graph transition only after executable evidence passes.

The ten Claude Science tasks receive work packets containing the scientific
question, current evidence, engineering support, available data, commands,
expected outputs, unresolved decision, dependencies, and acceptance criteria.
The packets distinguish research judgment from already-complete plumbing.

## Graph and evidence changes

Add a dedicated closure-sweep evidence record containing the initial inventory,
classification table, task transitions, test commands/results, external blockers,
research work-package index, final counts, and checkpoint revision. Update
`TASK_GRAPH.yaml`, `PROGRESS.md`, and `HANDOFF.md` together. Extend the Round 4
graph mirror and gate tests for the new terminal status while preserving the
audited task identities, dependencies, closure classifications, external and
human gate inventories, conditional activation rule, and frozen Round 3 lineage.

`R4-499` remains open until all required dependency lanes genuinely reach their
terminal evidence states. No status is changed solely because a report exists.

## Validation and handoff

Run the repository fast gate, graph/evidence validators, Python focused/full
tests, Java tests, web static/unit/build/browser gates where applicable, and
determinism/reproducibility checks. Review `git diff --check` and ensure only
intentional tracked changes are committed; preserve untracked `.codex-tmp/`,
`.superpowers/`, and any concurrent user work. Push a coherent checkpoint to
`origin/main` if the authorized remote is healthy.

The final report must list every non-passed task grouped as Claude Science,
genuine external/downstream blocker, or final closure dependency, and state that
zero ordinary Codex-closable engineering tasks remain.
