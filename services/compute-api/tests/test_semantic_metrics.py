from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from routemind_compute.api.app import create_app
from routemind_compute.application.analytics_archive import AnalyticalArchive, AnalyticalRecord
from routemind_compute.application.analytics_marts import AnalyticalMartBuilder
from routemind_compute.application.semantic_metrics import (
    MetricError,
    MetricStoreUnavailableError,
    SemanticMetricEngine,
    UnknownMetricError,
    metric_catalog,
    metric_definition,
)


def _append(
    root: Path,
    record_id: str,
    dataset: str,
    event_time: datetime,
    payload: dict[str, object],
) -> None:
    AnalyticalArchive(root).append(
        AnalyticalRecord(
            record_id=record_id,
            dataset=dataset,
            schema_version="v1",
            event_time=event_time,
            ingestion_time=event_time,
            clock_domain="WALL",
            source_revision="semantic-metric-test",
            decision_id=record_id if dataset == "dispatch_decisions" else None,
            payload=payload,
        )
    )


def _engine(root: Path) -> SemanticMetricEngine:
    return SemanticMetricEngine(AnalyticalMartBuilder(root).build("full").database_path)


def test_catalog_is_identical_for_web_reports_and_agents() -> None:
    digests = {
        consumer: tuple(item.definition_digest for item in metric_catalog(consumer))
        for consumer in ("web", "report", "agent")
    }
    assert digests["web"] == digests["report"] == digests["agent"]
    assert len(digests["web"]) == len(set(digests["web"])) == 7
    assert all(len(item.definition_digest) == 64 for item in metric_catalog())


def test_count_and_ratio_metrics_use_utc_half_open_windows(tmp_path: Path) -> None:
    start = datetime(2026, 8, 23, 12, tzinfo=UTC)
    _append(
        tmp_path,
        "decision-1",
        "dispatch_decisions",
        start,
        {"selected_courier": "courier-1", "fallback_used": False},
    )
    _append(
        tmp_path,
        "decision-2",
        "dispatch_decisions",
        start + timedelta(minutes=30),
        {"selected_courier": "", "fallback_used": True},
    )
    _append(
        tmp_path,
        "decision-end",
        "dispatch_decisions",
        start + timedelta(hours=1),
        {"selected_courier": "courier-2", "fallback_used": False},
    )

    results = _engine(tmp_path).evaluate(
        ("dispatch_decision_count", "dispatch_assignment_rate", "dispatch_fallback_rate"),
        start.astimezone(timezone(timedelta(hours=8))),
        (start + timedelta(hours=1)).astimezone(timezone(timedelta(hours=-4))),
    )

    assert [result.value for result in results] == [2.0, 0.5, 0.5]
    assert all(result.status == "available" for result in results)
    assert all(result.window_start == start for result in results)


def test_ratio_is_unavailable_when_denominator_has_no_eligible_records(tmp_path: Path) -> None:
    instant = datetime(2026, 8, 23, 12, tzinfo=UTC)
    _append(tmp_path, "decision-1", "dispatch_decisions", instant, {"strategy": "nearest"})
    result = _engine(tmp_path).evaluate(
        ("dispatch_fallback_rate",), instant, instant + timedelta(hours=1)
    )[0]

    assert result.value is None
    assert result.numerator == 0
    assert result.denominator == 0
    assert result.status == "unavailable"
    assert result.unavailable_reason == "no_eligible_records"


def test_solver_metric_excludes_unknown_status_from_denominator(tmp_path: Path) -> None:
    instant = datetime(2026, 8, 23, 12, tzinfo=UTC)
    _append(tmp_path, "solver-1", "solver_runs", instant, {"status": "success"})
    _append(tmp_path, "solver-2", "solver_runs", instant, {"status": "failed"})
    _append(tmp_path, "solver-3", "solver_runs", instant, {"status": "running"})

    result = _engine(tmp_path).evaluate(
        ("solver_success_rate",), instant, instant + timedelta(hours=1)
    )[0]
    assert result.value == 0.5
    assert result.numerator == 1
    assert result.denominator == 2


def test_unknown_names_windows_and_missing_store_fail_explicitly(tmp_path: Path) -> None:
    instant = datetime(2026, 8, 23, 12, tzinfo=UTC)
    with pytest.raises(UnknownMetricError, match="unknown semantic metric"):
        metric_definition("made_up_sql")
    with pytest.raises(MetricError, match="timezone-aware"):
        SemanticMetricEngine(tmp_path / "missing.duckdb").evaluate(
            ("order_count",), instant.replace(tzinfo=None), instant
        )
    with pytest.raises(MetricError, match="before end"):
        SemanticMetricEngine(tmp_path / "missing.duckdb").evaluate(
            ("order_count",), instant, instant
        )
    with pytest.raises(MetricStoreUnavailableError, match="mart missing"):
        SemanticMetricEngine(tmp_path / "missing.duckdb").evaluate(
            ("order_count",), instant, instant + timedelta(hours=1)
        )


def test_api_catalog_exposes_definition_without_executable_sql() -> None:
    from fastapi.testclient import TestClient

    response = TestClient(create_app()).get(
        "/api/v1/analytics/metrics/catalog", params={"consumer": "agent"}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    assert all(
        "numerator_sql" not in item and item["consumers"] == ["web", "report", "agent"]
        for item in body
    )
    assert response.headers["X-Trace-Id"]


def test_invalid_api_consumer_is_rejected() -> None:
    from fastapi.testclient import TestClient

    response = TestClient(create_app()).get(
        "/api/v1/analytics/metrics/catalog", params={"consumer": "arbitrary-sql"}
    )
    assert response.status_code == 422
