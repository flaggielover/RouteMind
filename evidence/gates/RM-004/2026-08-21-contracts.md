# RM-004 Versioned Contract Gate Evidence

Date: 2026-08-21 Asia/Shanghai

Revision: Worktree based on `99604f9`; the exact RM-004 checkpoint is the commit
containing this evidence file.

## Contract baseline

Four JSON Schema Draft 2020-12 contracts now define the first independent v1
integration surface:

- health response;
- dispatch request with bounded coordinates and UUID identities;
- dispatch decision with strategy version, score, and unassigned invariant;
- event envelope with stable event, aggregate, correlation, causation, and W3C
  trace identifiers.

`contracts/README.md` defines a conservative major-version policy. Published v1
fields cannot be removed, renamed, retyped, made required, or narrowed. Permanent
baseline fixtures turn that promise into an executable regression check.

## Executable gate

The validator uses `jsonschema==4.26.0` with format checking and is included in
the frozen Python environment, Ruff, formatting, and strict mypy gates.

```text
scripts/compute-api.ps1 check
PASS: 4 schemas and 12 contract fixtures
PASS: 4 positive examples accepted
PASS: 4 deliberately invalid examples rejected
PASS: 4 v1 compatibility baselines accepted
PASS: Ruff and formatting
PASS: strict mypy, 13 source files
PASS: 16 compute tests, 100% statement and branch coverage
```

The schemas are integration DTOs rather than internal database or domain models.
No durable ownership moved into Python, and no broker behavior is claimed by this
schema-only gate.
