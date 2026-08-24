# R3-300 Scientific Control Plane Evidence

Date: 2026-08-24 (Asia/Shanghai)
Baseline: `ed947eb`
Status: local validation complete; remote CI pending

## Scope

R3-300 audits the prepared Round 3 graph and establishes the authoritative
scientific control plane. It does not execute a benchmark, statistical campaign,
Digital Twin validation, RADS experiment, or prior-art claim review.

## Delivered controls

- `TASK_GRAPH.yaml` contains 45 dependency-ordered Round 3 tasks across five
  workstreams, including non-blocking deferred tasks.
- Every `R3-*` task records classification, workstream, and independent
  engineering, experiment, statistical, and claim status.
- `scripts/validate_control_plane.py` rejects incomplete research state and
  rejects a generic `passed` state while any required scientific dimension is
  still open.
- `scripts/resume.ps1` exposes the active task's E/X/S/C status.
- The Research Contract freezes initial hypotheses, exclusions, resource rules,
  manifest requirements, and non-claims before material experiments.
- The Claim Matrix and Negative Results ledger start with no supported claim.
- Production-heavy work remains preserved for Round 4 or parallel engineering
  and no longer blocks the Round 3 scientific critical path.

## Executable evidence

The following commands passed locally before the validation checkpoint:

```text
python scripts/validate_control_plane.py
PASS: task graph schema, dependencies, states, and evidence rules

python scripts/validate_control_plane_test.py
Ran 3 tests ... OK

./scripts/resume.ps1
R3-300 ... [validating]
Research gates: R3-300 E-IN-PROGRESS / X-NOT-REQUIRED /
S-NOT-APPLICABLE / C-NOT-APPLICABLE
PASS: RouteMind fast repository gate
```

`git diff --check` passes after mechanical trailing-whitespace cleanup. The full
repository verification command and the real GitHub Actions run are recorded in
the validating and closure checkpoints respectively.

## Scientific disposition

- Engineering: `E-IN-PROGRESS` until the pushed checkpoint passes GitHub Actions.
- Experiment: `X-NOT-REQUIRED`; no material experiment belongs to this task.
- Statistics: `S-NOT-APPLICABLE`; no inferential result belongs to this task.
- Claim: `C-NOT-APPLICABLE`; this control-plane task supports no scientific claim.

