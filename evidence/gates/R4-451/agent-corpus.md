# R4-451 Adversarial Analytical-Agent Corpus Evidence

Date: 2026-09-02 (Asia/Shanghai)

Validation base revision: `d3b0a32`

Status: `PASSED / LOCAL_ENGINEERING_CLOSURE`

`r4_agent_evaluation.py` freezes a content-addressed nine-case corpus covering
diagnosis, SQL/data analysis, reports, experiment interpretation, what-if,
refusal, injection, ambiguity, and unavailable evidence. Each case includes
role, tool, arguments, expected acceptance/refusal, evidence and citation
expectations, with no production tenant data.

Observed local corpus digest:
`fcb55ba525921bae0440fb011d7b8651fd77ececeae442ffc22168329f1ef02c`.

Validation command:

```text
services/compute-api/.venv/Scripts/python.exe -m pytest services/compute-api/tests/test_r4_agent_evaluation.py --no-cov -q
```

Result: PASS as part of the 17-test focused closure suite. The R4-405
dependency is scoped to its passed local preparation; no live telemetry or
production-agent claim is made.
