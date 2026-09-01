# R4-439 OPE Identifiability Re-audit Readiness

Date: 2026-09-02 (Asia/Shanghai)

Validation base revision: `375eb7b`

Status: `PENDING / CLAUDE_SCIENCE_REQUIRED`

The local fail-closed audit path is executable and ready for a new,
lineage-qualified decision-log corpus. The current repository has no such
corpus: the decision-log store reports `INSUFFICIENT_DATA`, and the support
audit reports `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS` with all five required
support fields missing (`logged_propensity`, `exploration_indicator`,
`action_overlap`, `state_richness`, and `shared_resource_context`). The
existing 640-row fixture remains simulated and deterministic; it is not
retroactively promoted to causal evidence.

Validation command:

```text
services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_r4_decision_logging.py services/compute-api/tests/test_ope_identifiability.py --no-cov -q
```

Result: `21 passed`.

Readiness output:

```json
{"decision_log_support":{"action_counts":[],"claim_boundary":"support_diagnostic_only","deterministic_count":0,"overlap_ratio":0.0,"reason":"no decision-time logs","record_count":0,"schema_version":"routemind-decision-log-v1","shared_resource_count":0,"status":"INSUFFICIENT_DATA","stochastic_count":0},"ope_audit":{"available_fields":[],"claim_boundary":"OPE_AUDIT_DOES_NOT_ESTABLISH_OFF_POLICY_EFFECT","missing_fields":["logged_propensity","exploration_indicator","action_overlap","state_richness","shared_resource_context"],"reason":"Decision Corpus has selected actions and outcomes but no logged propensities or verified action support","status":"OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS"}}
```

Claude Science must still specify the causal estimand and judge state
sufficiency, overlap, interference, censoring, missingness, effective sample
size, and any assumptions required before R4-439 can pass. No IPS, SNIPS, or
doubly robust estimator is activated by this readiness record.
