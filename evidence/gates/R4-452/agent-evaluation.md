# R4-452 Read-Only Analytical-Agent Evaluation Evidence

Date: 2026-09-02 (Asia/Shanghai)

Validation base revision: `d3b0a32`

Status: `PASSED / DETERMINISTIC_LOCAL_EVALUATION`

The evaluator invokes the existing privacy-bounded analytical-agent substrate
without state-changing tools. It retains grounding, citations, tool
correctness, hallucination, refusal, latency, cost, reproducibility, failure,
and output digests. It cannot promote a scientific or production claim.

Deterministic local result: 9/9 tool-correct, 9/9 grounded, 9/9 cited, four
safe refusals, zero hallucinations, zero failures, USD 0.00. Reproducibility
digest:
`13fbb6ff4a14675868946fd940c8a6a272cfee6cb00f9e1cba83663540c977fc`.

Validation command:

```text
services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_r4_agent_evaluation.py --no-cov -q
```

Result: PASS as part of the 17-test focused closure suite.
