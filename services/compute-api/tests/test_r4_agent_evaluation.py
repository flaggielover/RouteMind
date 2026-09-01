from __future__ import annotations

import pytest

from routemind_compute.application.r4_agent_evaluation import (
    AgentEvaluationCase,
    AgentEvaluationCorpus,
    ReadOnlyAgentEvaluator,
    default_corpus,
)


def test_default_corpus_covers_required_categories_and_evaluates_safely() -> None:
    corpus = default_corpus()
    results, summary = ReadOnlyAgentEvaluator().evaluate(corpus)
    assert len(corpus.cases) == 9
    assert {case.category for case in corpus.cases} == {
        "diagnosis",
        "sql_data_analysis",
        "reports",
        "experiment_interpretation",
        "what_if",
        "refusal",
        "injection",
        "ambiguity",
        "unavailable_evidence",
    }
    assert summary.result_count == 9
    assert summary.correct_count == 9
    assert summary.refusal_count == 4
    assert summary.hallucination_count == 0
    assert summary.failure_count == 0
    assert all(item.citation_present for item in results)
    assert summary.claim_boundary == "evaluation_only_no_claim_promotion"


def test_corpus_digest_is_content_addressed_and_invalid_cases_fail_closed() -> None:
    corpus = default_corpus()
    assert corpus.corpus_digest == default_corpus().corpus_digest
    with pytest.raises(ValueError, match="unavailable evidence"):
        AgentEvaluationCase(
            "bad", "unavailable_evidence", "operator", "metrics.read", (), True, False
        )
    with pytest.raises(ValueError, match="privacy"):
        AgentEvaluationCase(
            "bad", "reports", "operator", "lineage.read", (("artifact_id", "email"),), True, True
        )
    with pytest.raises(ValueError, match="categories"):
        AgentEvaluationCorpus.create(corpus.cases[:-1])


def test_evaluator_rejects_unknown_tool_and_preserves_reason() -> None:
    case = AgentEvaluationCase(
        "case-unknown", "refusal", "analyst", "missing.tool", (), False, True, "unknown_tool"
    )
    cases = list(default_corpus().cases)
    cases[-4] = case
    corpus = AgentEvaluationCorpus.create(tuple(cases))
    results, _ = ReadOnlyAgentEvaluator().evaluate(corpus)
    result = next(item for item in results if item.case_id == "case-unknown")
    assert not result.accepted
    assert result.refusal_correct
    assert result.reason == "unknown_tool"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("case id", "reports", "operator", "metrics.read", (), True, True), "case_id"),
        (("case", "not-a-category", "operator", "metrics.read", (), True, True), "category"),
        (
            ("case", "reports", "operator", "metrics.read", (("x", "y"), ("x", "z")), True, True),
            "arguments",
        ),
        (
            ("case", "reports", "operator", "metrics.read", (("bad key", "y"),), True, True),
            "arguments",
        ),
        (("case", "reports", "operator", "metrics.read", (("x", ""),), True, True), "bounded"),
        (("case", "reports", "operator", "metrics.read", (), True, True, " "), "expected_reason"),
    ],
)
def test_corpus_case_boundaries_fail_closed(args: tuple[object, ...], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        AgentEvaluationCase(*args)  # type: ignore[arg-type]


def test_corpus_constructor_and_evaluator_failures_are_recorded() -> None:
    corpus = default_corpus()
    with pytest.raises(ValueError, match="version"):
        AgentEvaluationCorpus("wrong", corpus.cases, corpus.corpus_digest)
    with pytest.raises(ValueError, match="digest"):
        AgentEvaluationCorpus(corpus.version, corpus.cases, "a" * 64)
    assert corpus.payload()["schema_version"] == "routemind-agent-evaluation-v1"
    summary = ReadOnlyAgentEvaluator().evaluate(corpus)[1]
    assert summary.as_dict()["result_count"] == 9

    class RaisingSubstrate:
        def invoke(self, request: object) -> object:
            raise RuntimeError("fixture failure")

    results, failed_summary = ReadOnlyAgentEvaluator(RaisingSubstrate()).evaluate(corpus)  # type: ignore[arg-type]
    assert all(item.failure for item in results)
    assert failed_summary.failure_count == len(corpus.cases)
