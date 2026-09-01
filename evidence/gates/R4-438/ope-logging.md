# R4-438 Decision-Time OPE Logging Evidence

Date: 2026-09-02 (Asia/Shanghai)

Validation base revision: `d3b0a32`

Status: `PASSED / LOCAL_ENGINEERING_CLOSURE`

`r4_decision_logging.py` records the exact decision-time behavior policy,
action, context, deterministic seed or propensity, pseudonymized tenant key,
outcome lineage, and retention policy. It rejects retroactive propensity,
duplicate identities, invalid deterministic/propensity combinations, and
retention-policy violations. Support and overlap diagnostics fail closed with
`OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS`.

Validation command:

```text
services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_r4_decision_logging.py --no-cov -q
```

Result: PASS as part of the 17-test focused closure suite. The existing 640-row
external observation fixture is simulated and deterministic; it is not
retrospectively upgraded into identifiable OPE evidence.
