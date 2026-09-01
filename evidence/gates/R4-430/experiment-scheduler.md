# R4-430 Bounded Experiment Scheduler Evidence

Date: 2026-09-02 (Asia/Shanghai)

Validation base revision: `d3b0a32`

Status: `PASSED / LOCAL_ENGINEERING_CLOSURE`

`r4_experiment_scheduler.py` implements a content-addressed frozen manifest,
resource and concurrency admission, cancellation, timeout, output digesting,
and immutable schedule audits. It has no path to mutate frozen evidence or Java
durable business state. The R4-405 dependency is scoped to its passed local
preparation only; no production telemetry or target qualification is claimed.

Validation command:

```text
services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_r4_experiment_scheduler.py --no-cov -q
```

Result: PASS as part of the 17-test focused closure suite. Tests cover manifest
identity, admission, concurrency rejection, cancellation, timeout, successful
output lineage, and fail-closed non-digestible output.
